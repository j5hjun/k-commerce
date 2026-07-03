# Agent Routes File Map

This directory contains FastAPI routers for the agent backend.

- `chat.py` - `/health`, `/api/tools` (MCP tool listing, no LLM required), and `/ws/chat` (WebSocket streaming chat via the agent).
- `__init__.py` - routes package marker.
