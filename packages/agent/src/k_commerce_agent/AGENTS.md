# k_commerce_agent File Map

This package contains the FastAPI agent backend and its MCP/LLM wiring.

- `main.py` - `create_app()` FastAPI factory, CORS setup, and `main()` uvicorn runner (`k-commerce-agent` entry point).
- `config.py` - `Settings` (env prefix `AGENT_`): LLM provider/model, watsonx credentials (WATSONX_* aliases), MCP launch command, CORS, host/port.
- `mcp_client.py` - `build_mcp_client()`/`load_tools()`; connects to `k-commerce-mcp` over stdio and loads MCP tools as LangChain tools (stateless).
- `agent.py` - `build_model()` (watsonx via `ChatWatsonx`, else `init_chat_model`), `is_model_configured()`, and `build_agent()` using `create_agent`; raises `ModelNotConfiguredError` when the LLM is not fully configured.
- `schemas.py` - request/response models for chat and the tools listing.
- `routes/` - FastAPI routers. See `routes/AGENTS.md`.
- `__init__.py` - package marker.

LLM is resolved lazily so `/health` and `/api/tools` work before a model is configured.
Tool behavior is delegated through MCP to `packages/mcp`, which delegates to `packages/cli` services.
