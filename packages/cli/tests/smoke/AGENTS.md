# CLI Smoke Tests Knowledge Base

## OVERVIEW

Opt-in real/local browser tests for Coupang flows. These are not safe-by-default CI coverage.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Shared smoke helpers | `_helpers.py` | Gating, CLI invocation, provider paths, artifact copy. |
| Auth smoke | `auth/` | Credentials, existing session, malformed credentials, manual login. |
| Order smoke | `order/` | Snapshot, refresh, failed-page retry scenarios. |

## CONVENTIONS

- Gate real smoke execution with `RUN_COUPANG_SMOKE=1`.
- Use `K_COMMERCE_BROWSER_SANDBOX=0` only where Chrome sandboxing is blocked.
- Copy only required artifacts from `~/.k-commerce/coupang` into `tmp_path`.
- Never mutate the original local provider state directly.
- Keep one real-flow scenario per test file.

## ANTI-PATTERNS

- Do not combine multiple smoke scenarios in one test.
