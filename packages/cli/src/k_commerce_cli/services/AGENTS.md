# Services Knowledge Base

## OVERVIEW

Provider abstraction and service layer for CLI business behavior.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Protocols/base classes | `base.py` | Browser, store, provider, service contracts. |
| Provider registry | `registry.py` | `get_provider()` and `list_providers()`. |
| Tool contract | `tools/` | Canonical MCP tool registry, request validation, invocation, and JSON serialization. |
| Persistent state | `store.py` | Credentials, session metadata, cookies, orders. |
| Paths | `paths.py` | Provider artifact layout. |
| Browser adapter | `browser/nodriver.py` | Concrete nodriver runtime. |
| Provider implementations | `providers/` | Concrete commerce providers. |
| Shared result types | `types/` | Provider/result re-export surface. |

## CONVENTIONS

- Add capabilities through `BaseProvider` protocols and service class wiring.
- The MCP tool contract is the source of truth for canonical names: `get_providers`, `login`, `status`, `logout`, `order_list`, `cart_list`, `cart_update_quantity`, `cart_delete_item`, `cart_delete_items`, `cart_clear`, `search_products`, `review_list_reviewable`, `review_list_editable`, `review_upload`, `review_edit`, `review_delete`.
- `tools/invoke.py` is the shared dispatcher used by MCP wrappers and the generic CLI runner.
- `ToolRuntimeOptions.root_dir` is for CLI debug/runtime isolation; canonical payload parsing rejects `root_dir`.
- Keep `registry.py`, `store.py`, and `paths.py` small and compositional.
- Browser orchestration complexity belongs under provider subpackages.

## ANTI-PATTERNS

- Do not grow concrete provider classes with direct implementation methods when a service class should own the behavior.
