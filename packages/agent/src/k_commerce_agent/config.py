import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the K-commerce agent backend.

    Values are read from environment variables (prefix ``AGENT_``) or a local
    ``.env`` file so the server can boot without an LLM configured yet.
    """

    model_config = SettingsConfigDict(env_prefix="AGENT_", env_file=".env", extra="ignore")

    # LLM provider:
    #  - "huggingface": HF OpenAI-compatible router (uses HF_TOKEN)
    #  - "watsonx": IBM watsonx.ai
    #  - "" (empty): generic "provider:model" form in ``llm_model``
    llm_provider: str = "huggingface"

    # For huggingface/watsonx this is the model_id
    # (e.g. "Qwen/Qwen2.5-72B-Instruct"). For the generic path it is a
    # "provider:model" string.
    llm_model: str = "Qwen/Qwen2.5-72B-Instruct"

    # HuggingFace Inference Providers (OpenAI-compatible router).
    hf_token: str = Field(default="", validation_alias="HF_TOKEN")
    hf_base_url: str = "https://router.huggingface.co/v1"

    # IBM watsonx.ai credentials. Read from the standard WATSONX_* env vars
    # (no AGENT_ prefix) so an existing .env keeps working.
    watsonx_url: str = Field(default="", validation_alias="WATSONX_URL")
    watsonx_project_id: str = Field(default="", validation_alias="WATSONX_PROJECT_ID")
    watsonx_api_key: str = Field(default="", validation_alias="WATSONX_API_KEY")

    system_prompt: str = (
        "당신은 한국 커머스 자동화를 돕는 어시스턴트입니다. "
        "제공된 도구를 사용해 로그인 상태 확인, 주문 조회, 장바구니 조회/수정/삭제 등을 수행하세요. "
        "도구의 provider 인자는 항상 소문자 식별자를 사용하세요(예: 'coupang'). "
        "특별한 언급이 없으면 provider는 'coupang'으로 간주하세요. "
        "주문 내역을 조회할 때는 order_list를 사용하세요. "
        "장바구니 항목을 변경하거나 삭제할 때는 cart_list로 얻은 product_id, vendor_item_id, item_id를 사용하세요. "
        "사용자가 장바구니에서 보이는 상품명이나 '1번 상품'처럼 말하면 cart_update_quantity_smart를 우선 사용하세요. "
        "사용자에게는 한국어로 간결하게 답하세요."
    )

    # Command used to launch the MCP server as a stdio subprocess.
    # Defaults to running the installed k-commerce-mcp package as a module.
    mcp_command: str = sys.executable
    mcp_args: list[str] = ["-m", "k_commerce_mcp.server"]
    mcp_server_name: str = "k-commerce"

    # Comma-separated CORS origins allowed to call this backend.
    cors_origins: list[str] = ["http://localhost:3000"]

    host: str = "127.0.0.1"
    port: int = 8000
    memory_path: Path = Field(
        default=Path.home() / ".k-commerce" / "agent-memory.json"
    )


settings = Settings()
