import json
from typing import Literal, NotRequired, TypedDict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessageChunk, ToolMessage

from k_commerce_agent.agent import (
    ModelNotConfiguredError,
    build_agent,
    build_model,
    is_model_configured,
)
from k_commerce_agent.history import (
    extract_requested_limit,
    prepare_chat_messages,
    turn_list_limit,
)
from k_commerce_agent.mcp_client import load_tools
from k_commerce_agent.schemas import ChatRequest, ToolInfo, ToolsResponse

router = APIRouter()

ToolResultStatus = Literal["completed", "failed"]


class ToolResultPayload(TypedDict):
    type: Literal["tool_result"]
    name: str
    status: ToolResultStatus
    content: str
    id: NotRequired[str]


@router.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@router.get("/api/tools", response_model=ToolsResponse)
async def list_tools() -> ToolsResponse:
    """List MCP tools exposed to the agent. Works without an LLM configured."""

    tools = await load_tools()
    return ToolsResponse(
        model_configured=is_model_configured(),
        tools=[ToolInfo(name=t.name, description=t.description or "") for t in tools],
    )


@router.websocket("/ws/chat")
async def chat(websocket: WebSocket) -> None:
    """Stream an agent chat turn to the frontend.

    Message protocol (JSON):
      - client -> server: {"message": "..."} or {"messages": [...]}
      - server -> client: {"type": "token"|"tool"|"tool_result"|"done"|"error", ...}
    """

    await websocket.accept()

    try:
        build_model()
    except ModelNotConfiguredError as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()
        return

    try:
        while True:
            payload = await websocket.receive_json()
            request = ChatRequest.model_validate(payload)
            lc_messages = prepare_chat_messages(request.to_lc_messages())
            if not lc_messages:
                await websocket.send_json({"type": "error", "message": "빈 메시지입니다."})
                continue

            turn_list_limit.set(None)
            for message in reversed(lc_messages):
                if message.get("role") == "user":
                    turn_list_limit.set(extract_requested_limit(message.get("content", "")))
                    break

            pending_tools: list[tuple[str, str]] = []
            seen_tool_ids: set[str] = set()

            try:
                agent = await build_agent()
                async for chunk in agent.astream(
                    {"messages": lc_messages},
                    stream_mode=["messages", "updates"],
                    version="v2",
                ):
                    await _forward_chunk(websocket, chunk, pending_tools, seen_tool_ids)
                await websocket.send_json({"type": "done"})
            except WebSocketDisconnect:
                raise
            except Exception as exc:
                await _fail_pending_tools(websocket, pending_tools, exc)
                await websocket.send_json(
                    {"type": "error", "message": f"실행 중 오류가 발생했습니다: {exc}"}
                )
    except WebSocketDisconnect:
        return


async def _forward_chunk(
    websocket: WebSocket,
    chunk: dict,
    pending_tools: list[tuple[str, str]],
    seen_tool_ids: set[str],
) -> None:
    kind = chunk.get("type")

    if kind == "messages":
        message_chunk, _metadata = chunk["data"]
        if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
            await websocket.send_json({"type": "token", "content": message_chunk.content})
        return

    if kind == "updates":
        for node_name, update in chunk["data"].items():
            messages = (update or {}).get("messages", [])
            for message in messages:
                if node_name == "model":
                    for call in getattr(message, "tool_calls", None) or []:
                        await _emit_tool_call(websocket, call, pending_tools, seen_tool_ids)
                if isinstance(message, ToolMessage):
                    call_id = getattr(message, "tool_call_id", None)
                    name = message.name
                    if call_id:
                        pending_tools[:] = [(pid, pname) for pid, pname in pending_tools if pid != call_id]
                    else:
                        pending_tools[:] = [(pid, pname) for pid, pname in pending_tools if pname != name]
                    await websocket.send_json(
                        _tool_result_payload(
                            name,
                            _content_to_text(message.content),
                            call_id,
                        )
                    )


async def _emit_tool_call(
    websocket: WebSocket,
    call: dict,
    pending_tools: list[tuple[str, str]],
    seen_tool_ids: set[str],
) -> None:
    name = call.get("name")
    if not name:
        return
    call_id = call.get("id")
    if not call_id:
        return
    if call_id in seen_tool_ids:
        return
    seen_tool_ids.add(call_id)
    pending_tools.append((call_id, name))
    await websocket.send_json(
        {"type": "tool", "id": call_id, "name": name, "args": call.get("args") or {}}
    )


async def _fail_pending_tools(
    websocket: WebSocket,
    pending_tools: list[tuple[str, str]],
    exc: Exception,
) -> None:
    while pending_tools:
        call_id, name = pending_tools.pop(0)
        content = json.dumps(
            {
                "error": {
                    "type": "tool_error",
                    "message": str(exc),
                    "tool_name": name,
                }
            },
            ensure_ascii=False,
        )
        await websocket.send_json(_tool_result_payload(name, content, call_id))


def _tool_result_payload(
    tool_name: str,
    content: str,
    call_id: str | None,
) -> ToolResultPayload:
    payload: ToolResultPayload = {
        "type": "tool_result",
        "name": tool_name,
        "status": _tool_result_status(content),
        "content": content,
    }
    if call_id:
        payload["id"] = call_id
    return payload


def _tool_result_status(content: str) -> ToolResultStatus:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return "completed"
    if isinstance(value, dict) and "error" in value:
        return "failed"
    return "completed"


def _content_to_text(content: str | list) -> str:
    """Flatten a LangChain message's content into plain text.

    ``BaseMessage.content`` is either a plain string or a list of content
    blocks (e.g. ``[{"type": "text", "text": "..."}]``, as MCP tool results
    arrive via ``langchain_mcp_adapters``). The frontend only needs the text.
    """

    if isinstance(content, str):
        return content

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)
