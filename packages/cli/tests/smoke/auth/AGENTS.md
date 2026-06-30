# Auth Smoke Tests File Map

This directory contains opt-in smoke tests for Coupang authentication flows.

- `test_coupang_login_with_credentials.py` - credentials-based Coupang login using copied local credentials.
- `test_coupang_login_with_existing_session.py` - existing Coupang session reuse using copied browser/session artifacts.
- `test_coupang_login_with_malformed_credentials.py` - malformed credentials handling.
- `test_coupang_manual_login_without_credentials.py` - manual login when credentials are absent.
- `_helpers.py` - auth-specific smoke helpers for login invocation and credentials writing.
- `__init__.py` - auth smoke test package marker.
