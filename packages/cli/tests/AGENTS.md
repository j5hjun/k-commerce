# CLI Tests File Map

This directory contains tests for the CLI package.

## Unit and service tests

- `test_cli.py` - command registration, help output, parser validation, terminal printing, and command-to-service plumbing.
- `test_auth_service.py` - provider registry behavior and default provider creation.
- `test_provider_store.py` - credential/session/order persistence behavior in `ProviderStore`.
- `test_coupang_login.py` - Coupang auth/browser/session behavior with test doubles.
- `test_coupang_logout.py` - Coupang logout/session cleanup behavior.
- `test_coupang_orders.py` - Coupang order collection, retry, diff-count, cache, and failure-message behavior.
- `__init__.py` - test package marker.

## Scenario directories

- `e2e/` - end-to-end CLI login scenarios against browser/session helpers. See `e2e/AGENTS.md`.
- `smoke/` - opt-in smoke tests for local/manual Coupang login scenarios. See `smoke/AGENTS.md`.
