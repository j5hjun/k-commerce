# PROJECT KNOWLEDGE BASE

**Generated:** 2026-07-06 09:47:21 KST
**Commit:** 921ffcf
**Branch:** dev

## OVERVIEW

Python `uv` workspace for K-commerce automation. The public surfaces are a browser-backed CLI, a FastMCP stdio server over the CLI provider layer, and a FastAPI/LangChain agent backend that talks to MCP.

## STRUCTURE

```text
k-commerce/
├── packages/
│   ├── cli/      # `k-commerce`; command UX, provider contracts, browser automation, Coupang workflows
│   ├── mcp/      # `k-commerce-mcp`; thin MCP tool facade over CLI services
│   └── agent/    # `k-commerce-agent`; FastAPI/LangChain bridge to MCP
├── .agents/      # repo-shared agent skills
├── .github/      # PR template and issue forms
├── AGENTS.override.md  # git-ignored local-only notes
├── pyproject.toml
└── uv.lock
```

Generated/local-only: `.venv/`, `.uv-cache/`, `.pytest_cache/`, `.ruff_cache/`, `.serena/`, `.omo/`, `dist/`, `k_commerce.egg-info/`, top-level `tests/__pycache__/`, and any `__pycache__/`.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Package split | `packages/AGENTS.md` | Dependency direction is `agent -> mcp -> cli`. |
| CLI command wiring | `packages/cli/src/k_commerce_cli/cli.py` | Registers `login`, `status`, `order`, `logout`, `review`, `search`, `cart`. |
| CLI command handlers | `packages/cli/src/k_commerce_cli/commands/` | Thin asyncclick handlers; see local map. |
| Generic CLI tool runner | `packages/cli/src/k_commerce_cli/commands/tool_runner.py` | Executes `k-commerce <tool-name> '<json-request>'` and `--request-file`. |
| Provider contracts | `packages/cli/src/k_commerce_cli/services/base.py` | Provider, browser, store, auth/order/review/search/cart protocols. |
| MCP tool contract | `packages/cli/src/k_commerce_cli/services/tools/` | The MCP tool contract is the source of truth for canonical tool names, validation, JSON serialization, and `invoke_tool()`. |
| Provider factory | `packages/cli/src/k_commerce_cli/services/registry.py` | `get_provider()` builds paths, store, browser, concrete provider. |
| Persistent state | `packages/cli/src/k_commerce_cli/services/store.py` | Credentials, cookies, metadata, `orders.json`; temp roots in tests. |
| Coupang provider | `packages/cli/src/k_commerce_cli/services/providers/coupang/` | Auth, orders, cart, review, search, provider wiring. |
| CLI tests | `packages/cli/tests/` | Unit/service/e2e/smoke split, generic runner, and alias-routing coverage; see local map. |
| MCP server | `packages/mcp/src/k_commerce_mcp/server.py` | Tool registration and stdio `main()`. |
| Agent backend | `packages/agent/src/k_commerce_agent/` | FastAPI app, MCP client, model/agent build, chat route. |
| GitHub collaboration | `.github/AGENTS.md` | PR template and issue-form rules. |
| Shared agent skills | `.agents/AGENTS.md` | Repo-local reusable skills. |

## CODE MAP

| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|------|
| `app` | click group | `packages/cli/src/k_commerce_cli/cli.py:33` | CLI tests | CLI command registry. |
| `main` | function | `packages/cli/src/k_commerce_cli/cli.py:48` | entry point | Console script target for `k-commerce`. |
| `invoke_tool` | function | `packages/cli/src/k_commerce_cli/services/tools/invoke.py` | CLI/MCP wrappers | Shared canonical tool dispatcher. |
| `list_tool_names` | function | `packages/cli/src/k_commerce_cli/services/tools/registry.py` | CLI/MCP tests | Canonical tool-name list including `search_products` and `review_upload`. |
| `get_provider` | function | `packages/cli/src/k_commerce_cli/services/registry.py:28` | 56 callers | Provider construction choke point used by CLI and MCP. |
| `Provider` | protocol | `packages/cli/src/k_commerce_cli/services/base.py:97` | registry | Shared provider capability contract. |
| `ProviderStore` | class | `packages/cli/src/k_commerce_cli/services/store.py:10` | 31 callers | Filesystem state boundary. |
| `ProviderPaths` | class | `packages/cli/src/k_commerce_cli/services/paths.py:6` | 42 callers | Provider artifact layout. |
| `CoupangProvider` | class | `packages/cli/src/k_commerce_cli/services/providers/coupang/provider.py:14` | registry/tests | Wires Coupang service classes. |
| `CoupangOrderService` | class | `packages/cli/src/k_commerce_cli/services/providers/coupang/orders.py:25` | provider/tests | Snapshot merge/refresh/failed-page retry. |
| `CoupangCartService` | class | `packages/cli/src/k_commerce_cli/services/providers/coupang/cart/service.py:79` | provider/tests | Cart list, quantity, delete sessions. |
| `create_mcp_server` | function | `packages/mcp/src/k_commerce_mcp/server.py:26` | MCP tests | Registers MCP tools and descriptions. |
| `create_app` | function | `packages/agent/src/k_commerce_agent/main.py:9` | app/tests | FastAPI factory with CORS and chat router. |
| `build_agent` | function | `packages/agent/src/k_commerce_agent/agent.py:97` | route/tests | Builds LangChain agent from MCP tools. |

## CONVENTIONS

- Use `uv run python` or `uv run pytest` for project commands; local shell commands should use `python3`.
- Python range is `>=3.11,<3.14`; root Ruff line length is `200`.
- Root pytest paths are `packages/cli/tests`, `packages/mcp/tests`, and `packages/agent/tests`.
- Keep public surfaces separate: CLI owns provider behavior, MCP adapts it, agent consumes MCP tools.
- CLI command modules parse input and print output; provider behavior belongs in `services/`.
- The existing CLI commands are human/debug compatibility aliases; the generic canonical runner is `k-commerce <tool-name> '<json-request>'` or `k-commerce <tool-name> --request-file <path>`.
- `root_dir` is a CLI-only debug/runtime option passed through `ToolRuntimeOptions`; it is not a canonical MCP or JSON request field.
- MCP tools stay stateless and thin; wrappers delegate through `k_commerce_cli.services.tools.invoke.invoke_tool` and do not duplicate scraping/session logic.
- Agent talks to MCP over stdio; it should not call CLI provider internals directly.
- User-visible provider output may be Korean; preserve exact strings when tests assert them.
- PR bodies must preserve `.github/pull_request_template.md` headings, even when written in Korean.

## ANTI-PATTERNS

- Do not treat generated/cache directories as source maps.
- Do not put shared repository rules in `AGENTS.override.md`; it is git-ignored local-only context.
- Do not collapse CLI, MCP, and agent behavior into one package.
- Do not add credential/browser-dependent coverage to default pytest paths; keep it in e2e/smoke with markers.
- Do not bypass `get_provider()` for user-facing provider flows unless a test injects a fake provider.

## COMMANDS

```bash
uv sync
uv build
uv run pytest
uv run pytest packages/cli/tests
uv run pytest packages/cli/tests/e2e
uv run pytest packages/mcp/tests
uv run pytest packages/agent/tests
RUN_COUPANG_SMOKE=1 K_COMMERCE_BROWSER_SANDBOX=0 uv run pytest packages/cli/tests/smoke -m smoke
uv run k-commerce --help
uv run k-commerce-mcp
npx @modelcontextprotocol/inspector uv run k-commerce-mcp
uv run k-commerce-agent
```

## NOTES

- Canonical tool names: `get_providers`, `login`, `status`, `logout`, `order_list`, `cart_list`, `cart_update_quantity`, `cart_delete_item`, `cart_delete_items`, `cart_clear`, `search_products`, `review_list_reviewable`, `review_list_editable`, `review_upload`, `review_edit`, `review_delete`.
- Main CLI regression surfaces: `test_cli.py`, `test_cli_alias_invocation.py`, `test_tool_runner.py`, `test_tool_runner_errors.py`, `test_coupang_login.py`, `test_coupang_orders.py`, `test_coupang_review.py`, `test_coupang_review_cli.py`.
- `packages/cli/src/k_commerce_cli/services/providers/coupang/auth.py` has a TODO for live smoke reproduction despite unit coverage.
