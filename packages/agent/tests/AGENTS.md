# Agent Tests Knowledge Base

## OVERVIEW

Backend tests for FastAPI boot, lazy model setup, and MCP tool exposure.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Backend contract | `test_agent_backend.py` | Settings defaults, no-model failure path, `/api/tools` contract. |

## CONVENTIONS

- Keep app import and `create_app()` usable without model credentials.
- `/health` and `/api/tools` tests should not require an LLM configuration.
- When isolating route behavior, monkeypatch MCP tool loading instead of calling CLI provider internals.
- `/api/tools` should expose only the canonical MCP tool names.
- Add WebSocket tests beside `test_agent_backend.py` when changing `/ws/chat`; assert message types `token`, `tool`, `done`, and `error`.

## ANTI-PATTERNS

- Do not require `HF_TOKEN`, `WATSONX_*`, or other model secrets for default backend tests.
- Do not drive real browser/provider automation from agent tests.
