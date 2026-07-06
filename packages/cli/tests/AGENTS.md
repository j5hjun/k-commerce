# CLI Tests Knowledge Base

## OVERVIEW

CLI package tests: fast unit/service coverage, login e2e coverage, and opt-in real-browser smoke coverage.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Command contract | `test_cli.py` | Help, parser validation, terminal printing, command-service plumbing. |
| Alias routing | `test_cli_alias_invocation.py` | Human/debug aliases delegate through shared tool invocation and keep `root_dir` runtime-only. |
| Generic runner | `test_tool_runner.py`, `test_tool_runner_errors.py` | `k-commerce <tool-name> <json>` / `--request-file`, JSON errors, timeout and sanitized provider failures. |
| Tool dispatch | `test_tool_registry.py`, `test_tool_invoke.py`, `tool_runner_support.py` | Canonical tool registry, typed fake providers, runtime options. |
| Provider/store | `test_auth_service.py`, `test_provider_store.py` | Registry/default provider and state persistence. |
| Coupang services | `test_coupang_*.py` | Login/logout/orders/review/search/cart service behavior. |
| Interactive flows | `test_cart_interactive.py`, `test_cart_list_browse.py`, `test_review_list_browse.py` | Prompt loops and browse behavior. |
| Login e2e | `e2e/` | File-backed login/session scenarios. |
| Smoke | `smoke/` | Opt-in browser/local-state tests; see local maps. |

## CONVENTIONS

- Default tests should be fake-driven and isolated.
- Use `tmp_path`/`--root-dir` for provider state isolation.
- Keep command/provider tests separate from live browser coverage.
- Most async tests use `@pytest.mark.anyio`.
- Use typed fake providers and dataclass call records for shared-tool and alias-routing tests.
- Keep new focused test files small; split new coverage instead of adding to already large behavior suites.

## ANTI-PATTERNS

- Do not add local credential/session dependency to default unit tests.
- Do not make command alias tests call providers directly; they should prove delegation through shared invocation.
