# k_commerce_mcp Knowledge Base

## OVERVIEW

MCP server package containing the FastMCP registration hub and thin tool wrappers.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Server factory | `server.py` | `create_mcp_server()` and stdio `main()`. |
| Tool wrappers | `tools/` | One module per MCP action; see local map. |
| Package marker | `__init__.py` | Import package marker. |

## CONVENTIONS

- Register tools centrally in `server.py`.
- The MCP tool contract is the source of truth for canonical names and payloads.
- Tool modules delegate through the shared `k_commerce_cli.services.tools.invoke.invoke_tool` contract.
- Current tool surface: `get_providers`, `login`, `status`, `logout`, `order_list`, `cart_list`, `cart_update_quantity`, `cart_delete_item`, `cart_delete_items`, `cart_clear`, `search_products`, `review_list_reviewable`, `review_list_editable`, `review_upload`, `review_edit`, `review_delete`.
- MCP payloads do not include `root_dir`; that option belongs to CLI debug/runtime execution.

## ANTI-PATTERNS

- Do not make `server.py` own provider behavior.
