# CLI Package Knowledge Base

## OVERVIEW

`packages/cli` owns the `k-commerce` command UX, provider contracts, persistent state, browser automation, and Coupang workflow logic.

## STRUCTURE

```text
cli/
├── pyproject.toml   # package metadata and `k-commerce` console script
├── README.md        # current CLI command surface
├── src/k_commerce_cli/
└── tests/
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| App entry | `src/k_commerce_cli/cli.py` | `app` and `main`; command registration. |
| Generic tool runner | `src/k_commerce_cli/commands/tool_runner.py` | `k-commerce <tool-name> '<json-request>'` and `--request-file` JSON execution. |
| Commands | `src/k_commerce_cli/commands/` | Human/debug compatibility aliases for login/status/logout/order/search/review/cart. |
| Service layer | `src/k_commerce_cli/services/` | Provider protocols, registry, store, browser adapter, types, and canonical MCP tool contract. |
| Coupang workflows | `src/k_commerce_cli/services/providers/coupang/` | Auth/order/review/search/cart automation. |
| Tests | `tests/` | Unit/service/e2e/smoke coverage. |

## CONVENTIONS

- The MCP tool contract is the source of truth for canonical tool names and request payloads.
- Commands parse options, resolve provider/root-dir/input, call shared invocation, and print terminal output.
- Provider behavior belongs in `services/`; everything else should call into this package instead of duplicating provider behavior.
- `--root-dir`/`--root_dir` isolation is a CLI-only debug/runtime option and should work consistently across login, status, logout, review, cart, order list, and search.
- Login order is restore saved session, try saved credentials, then manual browser login.

## ANTI-PATTERNS

- Do not put scraping, browser session handling, or provider state changes in command modules.
