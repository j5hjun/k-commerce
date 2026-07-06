import json
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from k_commerce_agent.config import settings
from k_commerce_agent.history import LIST_TOOLS, compact_tool_content
from k_commerce_agent.mcp_client import load_tools_by_server
from k_commerce_agent.profiles.kcommerce import attach_next_step
from k_commerce_agent.tools.web_search import web_search


class ModelNotConfiguredError(RuntimeError):
    """Raised when an agent is requested but no LLM model is configured."""


def is_model_configured() -> bool:
    """Report whether an LLM is fully configured, without constructing it."""

    provider = settings.llm_provider.strip().lower()
    if provider in ("hf", "huggingface"):
        return bool(settings.llm_model and settings.hf_token)
    if provider == "ollama":
        return bool(settings.llm_model)
    if provider in ("watsonx", "ibm"):
        return all(
            (
                settings.llm_model,
                settings.watsonx_url,
                settings.watsonx_project_id,
                settings.watsonx_api_key,
            )
        )
    return bool(settings.llm_model)


def build_model() -> BaseChatModel:
    """Resolve the chat model from settings.

    Supports IBM watsonx.ai (``llm_provider="watsonx"``) and the generic
    LangChain ``provider:model`` path for everything else.
    """

    provider = settings.llm_provider.strip().lower()

    if provider in ("hf", "huggingface"):
        missing = [
            name
            for name, value in (
                ("AGENT_LLM_MODEL", settings.llm_model),
                ("HF_TOKEN", settings.hf_token),
            )
            if not value
        ]
        if missing:
            raise ModelNotConfiguredError(
                "HuggingFace 설정이 부족합니다. 다음 값이 필요합니다: " + ", ".join(missing)
            )

        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.hf_base_url,
            api_key=settings.hf_token,
        )

    if provider == "ollama":
        if not settings.llm_model:
            raise ModelNotConfiguredError(
                "Ollama 설정이 부족합니다. AGENT_LLM_MODEL에 tool calling을 지원하는 "
                "모델 태그(예: 'qwen2.5:7b-instruct')를 지정하세요."
            )

        from langchain_openai import ChatOpenAI

        # Ollama's OpenAI-compatible endpoint ignores the API key but the
        # client requires a non-empty value.
        return ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            api_key="ollama",
        )

    if provider in ("watsonx", "ibm"):
        missing = [
            name
            for name, value in (
                ("AGENT_LLM_MODEL", settings.llm_model),
                ("WATSONX_URL", settings.watsonx_url),
                ("WATSONX_PROJECT_ID", settings.watsonx_project_id),
                ("WATSONX_API_KEY", settings.watsonx_api_key),
            )
            if not value
        ]
        if missing:
            raise ModelNotConfiguredError(
                "watsonx 설정이 부족합니다. 다음 값이 필요합니다: " + ", ".join(missing)
            )

        from langchain_ibm import ChatWatsonx

        return ChatWatsonx(
            model_id=settings.llm_model,
            url=settings.watsonx_url,
            project_id=settings.watsonx_project_id,
            api_key=settings.watsonx_api_key,
        )

    if not settings.llm_model:
        raise ModelNotConfiguredError(
            "LLM 모델이 설정되지 않았습니다. 환경변수 AGENT_LLM_MODEL을 "
            "'provider:model' 형식(예: 'anthropic:claude-sonnet-4-6')으로 지정하고 "
            "해당 provider 패키지와 API 키를 설정하세요."
        )

    return init_chat_model(settings.llm_model)


def _tool_error_payload(tool_name: str, exc: Exception) -> str:
    return json.dumps(
        {
            "error": {
                "type": "tool_error",
                "message": str(exc),
                "tool_name": tool_name,
            }
        },
        ensure_ascii=False,
    )


def _with_safe_tool_errors(tool: BaseTool) -> BaseTool:
    """Return tool results instead of raising so the chat stream can finish."""

    coroutine = getattr(tool, "coroutine", None)
    if coroutine is None:
        return tool

    use_artifact = getattr(tool, "response_format", "content") == "content_and_artifact"

    async def safe_coroutine(
        *args: Any,
        **kwargs: Any,
    ) -> str | tuple[Any, Any]:
        try:
            return await coroutine(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - surfaced to the frontend as structured JSON
            payload = _tool_error_payload(tool.name, exc)
            if use_artifact:
                return payload, None
            return payload

    return tool.model_copy(update={"coroutine": safe_coroutine})


def _with_compact_tool_results(tool: BaseTool) -> BaseTool:
    """Return compact list-tool payloads so the LLM does not see huge JSON blobs."""

    if tool.name not in LIST_TOOLS:
        return tool

    coroutine = getattr(tool, "coroutine", None)
    if coroutine is None:
        return tool

    use_artifact = getattr(tool, "response_format", "content") == "content_and_artifact"

    async def compact_coroutine(
        *args: Any,
        **kwargs: Any,
    ) -> str | tuple[Any, Any]:
        result = await coroutine(*args, **kwargs)
        if use_artifact and isinstance(result, tuple):
            content, artifact = result
            return compact_tool_content(tool.name, content), artifact
        return compact_tool_content(tool.name, result)

    return tool.model_copy(update={"coroutine": compact_coroutine})


def _with_next_step_hints(tool: BaseTool, *, first_party: bool) -> BaseTool:
    """Attach agent-loop next-step hints to tool results."""

    coroutine = getattr(tool, "coroutine", None)
    if coroutine is None:
        return tool

    use_artifact = getattr(tool, "response_format", "content") == "content_and_artifact"

    async def hinted_coroutine(
        *args: Any,
        **kwargs: Any,
    ) -> str | tuple[Any, Any]:
        result = await coroutine(*args, **kwargs)
        if use_artifact and isinstance(result, tuple):
            content, artifact = result
            return attach_next_step(tool.name, content, first_party=first_party), artifact
        return attach_next_step(tool.name, result, first_party=first_party)

    return tool.model_copy(update={"coroutine": hinted_coroutine})


def _wrap_tool(tool: BaseTool, *, first_party: bool) -> BaseTool:
    """Wrap a tool with host-level and (for first-party tools) profile-level layers.

    Error safety applies to every tool. Name-keyed layers — list compaction
    and next-step hints — only apply to first-party tools, so a third-party
    MCP tool that happens to share a name (e.g. another server's ``status``)
    is never rewritten.
    """

    wrapped = _with_safe_tool_errors(tool)
    if first_party:
        wrapped = _with_compact_tool_results(wrapped)
    return _with_next_step_hints(wrapped, first_party=first_party)


async def build_agent():
    """Build a tool-calling agent backed by the MCP tools.

    The LLM is resolved lazily so the rest of the backend can run before a
    model/API key is chosen. Call this only when you actually need to run a
    chat turn.
    """

    model = build_model()
    tools: list[BaseTool] = []
    for server_name, server_tools in (await load_tools_by_server()).items():
        first_party = server_name == settings.mcp_server_name
        tools.extend(_wrap_tool(tool, first_party=first_party) for tool in server_tools)
    tools.append(_wrap_tool(web_search, first_party=True))
    return create_agent(model=model, tools=tools, system_prompt=settings.system_prompt)
