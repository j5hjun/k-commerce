# Packages Knowledge Base

## OVERVIEW

Workspace package boundary. Dependency direction is intentionally one-way: `agent -> mcp -> cli`.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| CLI/business logic | `cli/` | `k-commerce`; commands, provider contracts, browser automation, Coupang workflows. |
| MCP facade | `mcp/` | `k-commerce-mcp`; exposes CLI provider behavior as MCP tools. |
| Agent backend | `agent/` | `k-commerce-agent`; FastAPI/LangChain bridge to MCP. |

## CONVENTIONS

- `cli` is the source of truth for commerce behavior.
- The MCP tool contract is the source of truth for canonical tool names and request payloads.
- `mcp` imports CLI services and adapts them to MCP; it does not own provider logic.
- `agent` consumes MCP tools over stdio; it does not call CLI services directly.
- Canonical tool names are `get_providers`, `login`, `status`, `logout`, `order_sync`, `order_list`, `order_search`, `order_detail`, `order_failures`, `cart_list`, `cart_update_quantity`, `cart_delete_item`, `cart_delete_items`, `cart_clear`, `search_products`, `review_list_reviewable`, `review_list_editable`, `review_upload`, `review_edit`, and `review_delete`.

## ANTI-PATTERNS

- Do not introduce reverse dependencies from `cli` to `mcp` or `agent`.
