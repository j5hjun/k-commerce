# CLI E2E Tests File Map

This directory contains end-to-end CLI login scenarios.

- `_helpers.py` - session/root/profile helpers for e2e tests.
- `test_coupang_login_with_credentials.py` - successful Coupang login using a credentials file.
- `test_coupang_login_with_existing_session.py` - successful login path when a saved session already exists.
- `test_coupang_login_with_invalid_credentials.py` - failure path for invalid credentials.
- `test_coupang_manual_login_without_credentials.py` - manual login flow when credentials are missing.
- `__init__.py` - e2e test package marker.
