import sys

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from k_commerce_agent.profiles.kcommerce import SYSTEM_PROMPT

# pydantic-settings only pulls .env values into fields declared below, so a
# provider-native var like OPENAI_API_KEY (used by the generic "provider:model"
# path's underlying client, which reads os.environ directly) would otherwise
# never reach the process environment. Load .env into os.environ too so any
# provider's own env var convention works without a bespoke Settings field.
load_dotenv()


class Settings(BaseSettings):
    """Runtime configuration for the K-commerce agent backend.

    Values are read from environment variables (prefix ``AGENT_``) or a local
    ``.env`` file so the server can boot without an LLM configured yet.
    """

    model_config = SettingsConfigDict(env_prefix="AGENT_", env_file=".env", extra="ignore")

    # LLM provider:
    #  - "huggingface": HF OpenAI-compatible router (uses HF_TOKEN)
    #  - "ollama": local Ollama server (OpenAI-compatible, no API key)
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

    # Local Ollama server (OpenAI-compatible endpoint). No API key needed.
    # Set llm_provider="ollama" and llm_model to a tool-calling model tag
    # (e.g. "qwen2.5:7b-instruct").
    ollama_base_url: str = "http://localhost:11434/v1"

    # IBM watsonx.ai credentials. Read from the standard WATSONX_* env vars
    # (no AGENT_ prefix) so an existing .env keeps working.
    watsonx_url: str = Field(default="", validation_alias="WATSONX_URL")
    watsonx_project_id: str = Field(default="", validation_alias="WATSONX_PROJECT_ID")
    watsonx_api_key: str = Field(default="", validation_alias="WATSONX_API_KEY")

    # Pre-call rules only, owned by the k-commerce profile. Post-result
    # guidance (what to do after a tool returns) is attached per-result as a
    # ``next_step`` field by ``k_commerce_agent.profiles.kcommerce``.
    system_prompt: str = SYSTEM_PROMPT

    # Command used to launch the MCP server as a stdio subprocess.
    # Defaults to running the installed k-commerce-mcp package as a module.
    mcp_command: str = sys.executable
    mcp_args: list[str] = ["-m", "k_commerce_mcp.server"]
    mcp_server_name: str = "k-commerce"

    # Comma-separated CORS origins allowed to call this backend.
    cors_origins: list[str] = ["http://localhost:3000"]

    host: str = "127.0.0.1"
    port: int = 8000


settings = Settings()
