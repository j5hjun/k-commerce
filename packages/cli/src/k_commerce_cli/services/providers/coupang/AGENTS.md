# Coupang Provider File Map

This directory contains the Coupang provider implementation.

- `provider.py` - `CoupangProvider`, which wires store, browser, auth service, and order service together.
- `auth.py` - `CoupangAuthService`, login/logout/status flow, login page state detection, session restore/persist behavior, and manual-login waiting.
- `orders.py` - `CoupangOrderService`, order page scraping/evaluation, cache refresh/merge behavior, and order-list terminal message formatting.
- `types.py` - Coupang order dataclasses for summaries, metadata, products, delivery groups, order results, and list results.
- `__init__.py` - public Coupang provider exports.

Tests for this provider are mainly in `packages/cli/tests/test_coupang_login.py`, `test_coupang_logout.py`, `test_coupang_orders.py`, and the e2e/smoke subdirectories.
