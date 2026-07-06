from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from k_commerce_agent.config import settings
from k_commerce_agent.mcp_client import load_tools


class ModelNotConfiguredError(RuntimeError):
    """Raised when an agent is requested but no LLM model is configured."""


def is_model_configured() -> bool:
    """Report whether an LLM is fully configured, without constructing it."""

    provider = settings.llm_provider.strip().lower()
    if provider in ("hf", "huggingface"):
        return bool(settings.llm_model and settings.hf_token)
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


async def build_agent(*, extra_system_prompt: str = ""):
    """Build a tool-calling agent backed by the MCP tools.

    The LLM is resolved lazily so the rest of the backend can run before a
    model/API key is chosen. Call this only when you actually need to run a
    chat turn.
    """

    model = build_model()
    tools = await load_tools()
    system_prompt = settings.system_prompt
    if extra_system_prompt.strip():
        system_prompt = f"{system_prompt}\n\n{extra_system_prompt.strip()}"
    return create_agent(model=model, tools=tools, system_prompt=system_prompt)
