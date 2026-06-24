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

- a Coupang login flow in the CLI
- an MCP package that will expose commerce-oriented tools on top of the workspace packages

Provider-specific usage, credential formats, and session storage details are documented in the package READMEs to avoid duplication here.
