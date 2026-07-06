# k_commerce_agent Knowledge Base

## OVERVIEW

FastAPI backend, MCP client bootstrap, LangChain model/agent wiring, schemas, and chat routes.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| App factory | `main.py` | `create_app()`, CORS, `app`, uvicorn `main()`. |
| Settings | `config.py` | `AGENT_*`, HuggingFace, watsonx, MCP command, host/port. |
| MCP tools | `mcp_client.py` | `build_mcp_client()` and `load_tools()` over stdio. |
| Agent/model | `agent.py` | `is_model_configured()`, `build_model()`, `build_agent()`. |
| Schemas | `schemas.py` | Chat and tool-list request/response models. |
| Routes | `routes/` | HTTP/WebSocket API; see local map. |

## CONVENTIONS

- Resolve LLM lazily so non-chat endpoints work before API keys/models are set.
- MCP calls are stateless; persistent commerce state remains in the CLI layer.
- Default provider mode is HuggingFace; watsonx and generic `provider:model` are supported.

## ANTI-PATTERNS

- Do not require model credentials for app import or health/tool-list endpoints.
