# Agent Package File Map

This package is a LangChain agent backend that bridges a web frontend to the
K-commerce MCP server. The frontend talks HTTP/WebSocket to this backend, and
this backend talks MCP (stdio) to `k-commerce-mcp`.

## Package files

- `pyproject.toml` - agent package metadata, dependencies, and `k-commerce-agent` console script.
- `README.md` - agent-specific setup, LLM configuration, and endpoint documentation.

## Source and tests

- `src/` - importable agent source tree. See `src/AGENTS.md`.
- `tests/` - agent backend tests.
