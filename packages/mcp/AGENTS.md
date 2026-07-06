# MCP Package File Map

This package exposes K-commerce provider actions through an MCP server.

The MCP tool contract is the source of truth for canonical tool names and request payloads. MCP
wrappers delegate through `k_commerce_cli.services.tools.invoke.invoke_tool`.

## Package files

- `pyproject.toml` - MCP package metadata, dependencies, and console script entry point.
- `README.md` - MCP-specific usage documentation.

## Source and tests

- `src/` - importable MCP source tree. See `src/AGENTS.md`.
- `tests/` - MCP server/tool tests. See `tests/AGENTS.md`.

## Tool surface

Canonical tool names: `get_providers`, `login`, `status`, `logout`, `order_sync`, `order_list`, `order_detail`, `order_failures`, `cart_list`,
`cart_update_quantity`, `cart_delete_item`, `cart_delete_items`, `cart_clear`, `search_products`,
`review_list_reviewable`, `review_list_editable`, `review_upload`, `review_edit`, `review_delete`.

Use `k-commerce <tool-name> '<json-request>'` or `k-commerce <tool-name> --request-file <path>` for
local JSON execution through the same shared contract.

Use `npx @modelcontextprotocol/inspector uv run k-commerce-mcp` for manual MCP Inspector testing
against the local stdio server.
