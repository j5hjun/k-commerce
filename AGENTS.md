# Repository Map

This workspace is a Python monorepo for K-commerce automation. Use this map first when you need to find code without opening files one by one.

## Top-level files

- `README.md` - project overview and quickstart for the K-commerce MCP tools.
- `CONTRIBUTING.md` - contributor workflow and local development expectations.
- `pyproject.toml` - root workspace/tooling configuration.
- `uv.lock` - locked dependency graph for the workspace.
- `.gitignore` - ignored local caches, build outputs, and runtime artifacts.

## Directories

- `.agents/` - repository-shared assets for AI agents, including portable skills. See `.agents/AGENTS.md`.
- `.github/` - repository collaboration templates. See `.github/AGENTS.md`.
- `packages/` - installable Python packages. See `packages/AGENTS.md`.
- `packages/mcp/` - MCP server package for Korean commerce workflows. See `packages/mcp/AGENTS.md`.

## Generated or local-only directories

- `.venv/`, `.uv-cache/`, `.pytest_cache/`, `.ruff_cache/`, `.serena/`, `dist/`, and `__pycache__/` are local/generated artifacts. Do not use them as source-of-truth maps.
