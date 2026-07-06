# Auth Smoke Tests Knowledge Base

## OVERVIEW

Opt-in Coupang authentication smoke scenarios.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Auth helpers | `_helpers.py` | Login invocation and credentials writing. |
| Credentials login | `test_coupang_login_with_credentials.py` | Uses copied local credentials. |
| Existing session | `test_coupang_login_with_existing_session.py` | Uses copied browser/session artifacts. |
| Malformed credentials | `test_coupang_login_with_malformed_credentials.py` | Writes invalid credentials. |
| Manual login | `test_coupang_manual_login_without_credentials.py` | Starts from empty temp root. |

## CONVENTIONS

- Validate login outcomes and session metadata.
- Skip rather than mutate or repair stale local source artifacts.

## ANTI-PATTERNS

- Do not write test credentials into the real provider directory.
