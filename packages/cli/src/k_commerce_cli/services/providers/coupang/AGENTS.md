# Coupang Provider File Map

This directory contains the Coupang provider implementation.

- `provider.py` - `CoupangProvider`, which wires store, browser, auth service, order service, and review service together through `BaseProvider`.
- `auth.py` - `CoupangAuthService`, login/logout/status flow, login page state detection, session restore/persist behavior, and manual-login waiting.
- `orders.py` - `CoupangOrderService`, order page scraping/evaluation, cache refresh/merge behavior, and order-list terminal message formatting.
- `types.py` - Coupang order dataclasses for summaries, metadata, products, delivery groups, order results, and list results.
- `review/` - Coupang review listing, upload, edit, delete, browser-evaluation helpers, state handling, and review dataclasses. See `review/AGENTS.md`.
- `__init__.py` - public Coupang provider exports.

Tests for this provider are mainly in `packages/cli/tests/test_coupang_login.py`, `test_coupang_logout.py`, `test_coupang_orders.py`, `test_coupang_review.py`, `test_coupang_review_cli.py`, and the e2e/smoke subdirectories.

## Coupang Service Rules

- Keep Coupang service constructors aligned as `provider`, `store`, `browser`, and optional `terminal` so they can be instantiated through `BaseProvider`.
