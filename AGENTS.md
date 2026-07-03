# Repository Map

This workspace is a Python monorepo for K-commerce automation. Use this map first when you need to find code without opening files one by one.

## Top-level files

- `README.md` - project overview and quickstart for the K-commerce CLI/MCP tools.
- `CONTRIBUTING.md` - contributor workflow and local development expectations.
- `pyproject.toml` - root workspace/tooling configuration.
- `uv.lock` - locked dependency graph for the workspace.
- `.gitignore` - ignored local caches, build outputs, and runtime artifacts.

## Directories

- `.agents/` - repository-shared assets for AI agents, including portable skills. See `.agents/AGENTS.md`.
- `.github/` - repository collaboration templates. See `.github/AGENTS.md`.
- `packages/` - all installable Python packages. See `packages/AGENTS.md`.
- `packages/cli/` - command-line application, provider services, browser automation, and CLI tests.
- `packages/mcp/` - MCP server wrapper around the CLI provider services and MCP tests.
- `packages/agent/` - LangChain agent backend (FastAPI) that bridges a web frontend to the MCP server over stdio.

## Generated or local-only directories

- `.venv/`, `.uv-cache/`, `.pytest_cache/`, `.ruff_cache/`, `.serena/`, `dist/`, and `__pycache__/` are local/generated artifacts. Do not use them as source-of-truth maps.
