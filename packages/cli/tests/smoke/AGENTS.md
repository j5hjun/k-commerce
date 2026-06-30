# CLI Smoke Tests File Map

This directory contains opt-in smoke tests for real/local CLI flows.

- `_helpers.py` - smoke-test gating, generic CLI invocation, provider path helpers, and artifact copy utilities.
- `auth/` - Coupang authentication smoke tests: credentials login, existing session reuse, malformed credentials, and manual login.
- `__init__.py` - smoke test package marker.

Smoke tests may require local credentials, browser state, or explicit environment opt-in; do not assume they are safe to run by default.

## Smoke Test Organization

- Smoke tests must copy only the required local provider artifacts from `~/.k-commerce/coupang` into the test `tmp_path`. Tests must not modify the original local provider state directly.
- Keep smoke tests organized by domain:
  - `tests/smoke/auth/` for authentication smoke tests.
  - `tests/smoke/order/` for order-list smoke tests.
  - `tests/smoke/_helpers.py` for shared smoke utilities.
  - `tests/smoke/<domain>/_helpers.py` for domain-specific helpers.
- Split smoke tests by scenario. Do not combine multiple smoke scenarios in one test file. Prefer explicit filenames such as `test_coupang_order_list_without_snapshot.py`, `test_coupang_order_list_with_clean_snapshot.py`, and `test_coupang_order_failed_only.py`.
