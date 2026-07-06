# MCP Tools Knowledge Base

## OVERVIEW

Tool functions registered by `../server.py`.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Providers | `get_providers.py` | Returns supported provider names. |
| Session | `login.py`, `status.py`, `logout.py` | Provider session operations. |
| Orders | `order.py` | `order_sync`, `order_list`, `order_detail`, and `order_failures` tools. |
| Cart | `cart.py` | List, quantity update, single/batch delete, clear. |
| Search | `search.py` | Product search wrapper. |
| Review | `review.py` | Reviewable/editable list, upload, edit, and delete wrappers. |

## CONVENTIONS

- Keep tool functions async and thin.
- Validate/shape MCP-facing inputs, then delegate through `k_commerce_cli.services.tools.invoke.invoke_tool`.
- Canonical tool names are owned by `k_commerce_cli.services.tools.registry`; this directory implements wrappers for `get_providers`, `login`, `status`, `logout`, `order_sync`, `order_list`, `order_detail`, `order_failures`, cart tools, `search_products`, and review tools including `review_upload`.
- Keep cart delete/update request identity fields explicit.

## ANTI-PATTERNS

- Do not duplicate CLI command prompting or Coupang scraping here.
