# CLI Commands Knowledge Base

## OVERVIEW

Command handlers registered by `k_commerce_cli/cli.py`. This layer owns CLI parsing and output, not provider behavior.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Login/status/logout | `login.py`, `status.py`, `logout.py` | Root-dir handling and provider dispatch. |
| Generic tool runner | `tool_runner.py` | JSON runner for canonical tool names with inline JSON and `--request-file`. |
| Orders | `order.py` | `order list`, `order sync`, detail, and failures aliases. |
| Search | `search.py` | Sort validation, table/JSON output, optional JSON save. |
| Cart workflows | `cart/` | List-browse, quantity, delete; see local map. |
| Review workflows | `review/` | Upload/edit/delete; see local map. |

## CONVENTIONS

- The MCP tool contract is the source of truth; command handlers call shared tool invocation for commerce work.
- Existing command groups are human/debug compatibility aliases over the canonical tools.
- `root_dir` is accepted only as a CLI debug/runtime option, not as a canonical request payload field.
- Keep command modules thin: parse, prompt, delegate, print.
- Preserve exact user-facing strings that tests assert.

## ANTI-PATTERNS

- Do not duplicate Coupang scraping or state logic here.
