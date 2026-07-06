# CLI E2E Tests Knowledge Base

## OVERVIEW

End-to-end login scenarios through the CLI entrypoint, separate from live smoke tests.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Shared helpers | `_helpers.py` | Session/root/profile helpers. |
| Credentials login | `test_coupang_login_with_credentials.py` | Successful credentials path. |
| Existing session | `test_coupang_login_with_existing_session.py` | Saved session reuse. |
| Invalid credentials | `test_coupang_login_with_invalid_credentials.py` | Failure path. |
| Manual fallback | `test_coupang_manual_login_without_credentials.py` | Missing credentials/manual login. |

## CONVENTIONS

- E2E here is login/session focused; broader browser flows belong in smoke tests.
- Isolate artifacts with `--root-dir` or temp roots.

## ANTI-PATTERNS

- Do not mix real local `~/.k-commerce` state into e2e tests.
