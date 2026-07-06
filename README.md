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
- `packages/agent`: LangChain agent backend bridging a web frontend to the MCP server. See [packages/agent/README.md](packages/agent/README.md).

## Current Scope

The MCP tool contract is the source of truth for commerce tool names, request payloads, validation,
and shared service invocation. Both MCP wrappers and the generic CLI runner delegate through
`k_commerce_cli.services.tools.invoke.invoke_tool`.

The canonical tool names are:

- `get_providers`
- `login`
- `status`
- `logout`
- `order_sync`
- `order_list`
- `order_search`
- `order_detail`
- `order_failures`
- `cart_list`
- `cart_update_quantity`
- `cart_delete_item`
- `cart_delete_items`
- `cart_clear`
- `search_products`
- `review_list_reviewable`
- `review_list_editable`
- `review_upload`
- `review_edit`
- `review_delete`

Run any canonical tool through the generic CLI runner with inline JSON or a request file:

```bash
uv run k-commerce <tool-name> '<json-request>'
uv run k-commerce <tool-name> --request-file ./request.json
```

Run the MCP stdio server directly or open it in MCP Inspector:

```bash
uv run k-commerce-mcp
npx @modelcontextprotocol/inspector uv run k-commerce-mcp
```

Human-oriented CLI aliases such as `k-commerce login coupang`, `k-commerce order list coupang`,
and `k-commerce search coupang KEYWORD` remain available for local debugging and interactive
browser checks. Their `--root-dir` option is a CLI-only debug/runtime option and is not part of the
canonical MCP or JSON request payload.

## Supported Providers

The provider registry currently supports:

- `coupang`

Provider-specific usage, credential formats, and session storage details are documented in the package READMEs to avoid duplication here.
