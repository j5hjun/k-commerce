# Coupang Provider Knowledge Base

## OVERVIEW

Concrete Coupang provider implementation and the main complexity hub for browser-backed workflows.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Provider wiring | `provider.py` | `CoupangProvider`; wires auth/order/review/search/cart services. |
| Login/session | `auth.py` | Restore session, credentials login, manual browser fallback. |
| Orders | `orders.py` | `orders.json` snapshot merge, refresh, failed-page retry. |
| Order types | `types.py` | Coupang order dataclasses. |
| Cart | `cart/` | Cart list, quantity, delete, clear; see local map. |
| Review | `review/` | List/upload/edit/delete reviews; see local map. |
| Search | `search/` | Product search and detail-price enrichment; see local map. |

## CONVENTIONS

- Service constructors stay aligned as `provider` or `provider_name`, `store`, `browser`, optional `terminal`.
- Convert browser/login failures into typed result objects with state messages.
- `not_logged_in` is the shared login gate; browser-closed is the main browser/evaluation fallback.
- Preserve `login_method` session metadata.
- Pair browser-flow edits with broad fake-browser tests before live smoke coverage.

## ANTI-PATTERNS

- Do not leak raw browser exceptions to CLI/MCP boundaries.
- Do not add a separate `orders/AGENTS.md` unless `orders.py` becomes a package.
