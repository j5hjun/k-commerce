# CLI Smoke Tests File Map

This directory contains opt-in smoke tests for real/local CLI flows.

- `_helpers.py` - smoke-test gating, CLI invocation, credential writing, provider path helpers, and artifact copy utilities.
- `test_coupang_login_with_credentials.py` - smoke test for credentials-based Coupang login.
- `test_coupang_login_with_existing_session.py` - smoke test for reusing an existing Coupang session.
- `test_coupang_login_with_malformed_credentials.py` - smoke test for malformed credentials handling.
- `test_coupang_manual_login_without_credentials.py` - smoke test for manual login when credentials are absent.
- `__init__.py` - smoke test package marker.

Smoke tests may require local credentials, browser state, or explicit environment opt-in; do not assume they are safe to run by default.
