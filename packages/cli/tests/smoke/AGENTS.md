# CLI Smoke Tests File Map

This directory contains opt-in smoke tests for real/local CLI flows.

- `_helpers.py` - smoke-test gating, generic CLI invocation, provider path helpers, and artifact copy utilities.
- `auth/` - Coupang authentication smoke tests: credentials login, existing session reuse, malformed credentials, and manual login.
- `__init__.py` - smoke test package marker.

Smoke tests may require local credentials, browser state, or explicit environment opt-in; do not assume they are safe to run by default.
