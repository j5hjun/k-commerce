from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessageChunk

from k_commerce_agent.agent import (
    ModelNotConfiguredError,
    build_agent,
    is_model_configured,
)
from k_commerce_agent.mcp_client import load_tools
from k_commerce_agent.schemas import ChatRequest, ToolInfo, ToolsResponse

router = APIRouter()


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
      - server -> client: {"type": "token"|"tool"|"done"|"error", ...}
    """

    await websocket.accept()

    try:
        agent = await build_agent()
    except ModelNotConfiguredError as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()
        return

    try:
        while True:
            payload = await websocket.receive_json()
            request = ChatRequest.model_validate(payload)
            lc_messages = request.to_lc_messages()
            if not lc_messages:
                await websocket.send_json({"type": "error", "message": "빈 메시지입니다."})
                continue

            try:
                async for chunk in agent.astream(
                    {"messages": lc_messages},
                    stream_mode=["messages", "updates"],
                    version="v2",
                ):
                    await _forward_chunk(websocket, chunk)
                await websocket.send_json({"type": "done"})
            except WebSocketDisconnect:
                raise
            except Exception as exc:
                await websocket.send_json(
                    {"type": "error", "message": f"실행 중 오류가 발생했습니다: {exc}"}
                )
    except WebSocketDisconnect:
        return


async def _forward_chunk(websocket: WebSocket, chunk: dict) -> None:
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
                tool_calls = getattr(message, "tool_calls", None)
                for call in tool_calls or []:
                    await websocket.send_json(
                        {"type": "tool", "name": call.get("name"), "args": call.get("args")}
                    )
