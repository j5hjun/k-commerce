# Agent Package Knowledge Base

## OVERVIEW

`packages/agent` owns web-facing orchestration and LLM integration. It consumes MCP tools and leaves provider execution to MCP/CLI.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Package metadata | `pyproject.toml` | `k-commerce-agent` console script and MCP dependency. |
| Public docs | `README.md` | LLM setup, endpoints, WebSocket protocol. |
| Agent source | `src/k_commerce_agent/` | FastAPI, MCP client, model/agent build; see local map. |
| Tests | `tests/` | Settings defaults, no-model failure path, and `/api/tools`; see local map. |

## CONVENTIONS

- The server must boot without an LLM configured; `/health` and `/api/tools` still work.
- Chat over `/ws/chat` requires configured model settings.
- Model config is `AGENT_*` plus provider-specific keys such as `HF_TOKEN` or `WATSONX_*`.
- Manual login tools need a real GUI/display because provider login can launch Chrome.

## ANTI-PATTERNS

- Do not call CLI provider logic directly from the agent; use MCP tools.
