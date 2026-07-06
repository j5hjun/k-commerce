# Agent Routes Knowledge Base

## OVERVIEW

FastAPI routers for health, tool metadata, and streaming chat.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Chat routes | `chat.py` | `/health`, `/api/tools`, `/ws/chat`. |
| Package marker | `__init__.py` | Routes package marker. |

## CONVENTIONS

- `/health` and `/api/tools` must not require an LLM.
- `/ws/chat` streams JSON message types: `token`, `tool`, `done`, `error`.
- Surface model-configuration errors as chat errors rather than import-time failures.

## ANTI-PATTERNS

- Do not perform provider automation directly in route handlers.
