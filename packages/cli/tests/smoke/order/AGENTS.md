# Order Smoke Tests Knowledge Base

## OVERVIEW

Opt-in real/local Coupang order-list smoke scenarios.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Order helpers | `_helpers.py` | Invoke `order list`, read/write copied `orders.json`. |
| No snapshot | `test_coupang_order_list_without_snapshot.py` | Starts without prior `orders.json`. |
| Clean snapshot | `test_coupang_order_list_with_clean_snapshot.py` | Previous snapshot has no failed pages. |
| Failed snapshot | `test_coupang_order_list_with_failed_snapshot.py` | Previous snapshot has failed pages. |
| Missing/changed order | `test_coupang_order_list_with_missing_order.py`, `test_coupang_order_list_with_changed_status.py` | Snapshot diff scenarios. |
| Refresh/failed only | `test_coupang_order_refresh.py`, `test_coupang_order_failed_only.py` | Refresh and failed-page retry. |

## CONVENTIONS

- Mutate only copied `orders.json` in temp roots.
- Scenario helpers may rewrite `meta.failedPages`, `meta.refresh`, remove one order, or change delivery status.
- Successful smoke output may end in `[ok]` or `[warn]` depending on live site state.

## ANTI-PATTERNS

- Do not point order smoke tests at the original `~/.k-commerce/coupang/orders.json`.
