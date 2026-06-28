# K-Commerce

AI agent and MCP infrastructure for Korean commerce workflows.

## Workspace

This repository is a `uv` workspace with Python `3.11` to `3.13` support.

Install the workspace from the repository root:

```bash
uv sync
```

## Packages

- `packages/cli`: end-user CLI for commerce workflows. See [packages/cli/README.md](packages/cli/README.md).
- `packages/mcp`: MCP server exposing commerce tools. See [packages/mcp/README.md](packages/mcp/README.md).

## Current Scope

The workspace currently includes:

- a Coupang CLI flow with `login`, `login status`, `logout`, and `order list` commands
- an MCP package that exposes `login` and `login_status` tools on top of the shared provider registry

The `order list` flow is currently CLI-only and writes a local `orders.json` snapshot under the
selected provider directory.

## Supported Providers

The provider registry currently supports:

- `coupang`

Provider-specific usage, credential formats, and session storage details are documented in the package READMEs to avoid duplication here.
