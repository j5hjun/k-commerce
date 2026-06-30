# Order Smoke Tests File Map

This directory contains opt-in smoke tests for real/local Coupang order-list flows.

- `test_coupang_order_list_without_snapshot.py` - default order list smoke test when `orders.json` is absent.
- `test_coupang_order_list_with_clean_snapshot.py` - default order list smoke test when `orders.json` has no failed pages.
- `test_coupang_order_list_with_failed_snapshot.py` - default order list smoke test when `orders.json` has failed pages.
- `test_coupang_order_list_with_missing_order.py` - default order list smoke test when the previous `orders.json` is missing one order.
- `test_coupang_order_list_with_changed_status.py` - default order list smoke test when the previous `orders.json` has a changed delivery status.
- `test_coupang_order_refresh.py` - refresh-mode order list smoke test.
- `test_coupang_order_failed_only.py` - failed-page retry smoke test using a copied and edited `orders.json`.
- `_helpers.py` - order-specific smoke helpers for invoking `order list` and reading/writing `orders.json`.
- `__init__.py` - order smoke test package marker.
