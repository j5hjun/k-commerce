# K-Commerce CLI

CLI for K-Commerce workflows.

## Requirements

- Python `3.11` to `3.13`
- `uv`

## Setup

From the repository root, install the workspace first:

```bash
uv sync
```

## Usage

The CLI currently supports the `coupang` provider.

## Canonical Tool Runner

The MCP tool contract is the source of truth for tool names, request payloads, validation, and
service invocation. The generic CLI runner executes the same canonical contract and prints JSON:

```bash
uv run k-commerce <tool-name> '<json-request>'
uv run k-commerce <tool-name> --request-file ./request.json
```

Canonical tool names:

- `get_providers`
- `login`
- `status`
- `logout`
- `order_sync`
- `order_list`
- `order_search`
- `order_detail`
- `order_failures`
- `product_detail`
- `cart_list`
- `cart_update_quantity`
- `cart_delete_item`
- `cart_delete_items`
- `cart_clear`
- `search_products`
- `review_list_reviewable`
- `review_list_editable`
- `review_upload`
- `review_edit`
- `review_delete`

Example inline requests:

```bash
uv run k-commerce status '{"provider":"coupang"}'
uv run k-commerce search_products '{"provider":"coupang","keyword":"keyboard","sort":"relevance","max_results":10}'
```

Common request examples:

```bash
uv run k-commerce login '{"provider":"coupang"}'
uv run k-commerce order_sync '{"provider":"coupang","refresh":false,"failed_only":false}'
uv run k-commerce order_list '{"provider":"coupang","start_date":"2026-01-01","end_date":"2026-06-30","limit":50}'
uv run k-commerce order_search '{"provider":"coupang","keyword":"세제","start_date":"2026-01-01","end_date":"2026-06-30","limit":50}'
uv run k-commerce cart_list '{"provider":"coupang"}'
uv run k-commerce review_list_reviewable '{"provider":"coupang"}'
```

## Compatibility Alias Commands

The named CLI commands are human/debug compatibility aliases. They keep terminal-oriented prompts
and output while routing commerce work through the shared contract.

| Alias command | Canonical tool |
| --- | --- |
| `uv run k-commerce login coupang` | `login` |
| `uv run k-commerce status coupang` | `status` |
| `uv run k-commerce logout coupang` | `logout` |
| `uv run k-commerce order sync coupang` | `order_sync` |
| `uv run k-commerce order list coupang` | `order_list` |
| `uv run k-commerce order search coupang KEYWORD` | `order_search` |
| `uv run k-commerce order detail coupang ORDER_ID` | `order_detail` |
| `uv run k-commerce order failures coupang` | `order_failures` |
| `uv run k-commerce search coupang KEYWORD` | `search_products` |
| `uv run k-commerce cart coupang --list` | `cart_list` |
| `uv run k-commerce cart coupang --quantity` | `cart_update_quantity` |
| `uv run k-commerce cart coupang --delete` | `cart_delete_item`, `cart_delete_items`, `cart_clear` |
| `uv run k-commerce review upload coupang` | `review_upload` |
| `uv run k-commerce review edit coupang` | `review_edit` |
| `uv run k-commerce review delete coupang` | `review_delete` |

`root_dir` is not part of canonical MCP or JSON request payloads. Use `--root-dir` only on CLI
aliases when local verification needs isolated credentials and session files:

```bash
uv run k-commerce login coupang --root-dir /tmp/test-k-commerce
```

This option is intended for local verification and automated tests where credentials and session
files must be isolated from the default `~/.k-commerce` directory.

If you pass an unsupported provider, the CLI reports the supported provider names from the shared
provider registry.

## Coupang Login Flow

The `login` tool tries the following in order:

1. Restore a previously saved browser session.
2. If no valid session exists, try automatic login with saved credentials.
3. If automatic login is unavailable or fails, wait for manual login in the browser.

When login succeeds, the CLI saves the session so later browser-backed tools can reuse it.
`search_products`, cart tools, review tools, `order_sync`, and `order_search` require a valid saved session.
`order_list`, `order_detail`, and `order_failures` read the saved order snapshot.

Review image or video attachments are not supported.

## Login Status

The `status` tool first checks whether saved session artifacts exist under the selected state
directory. If no local session state is present, it does not proceed with browser-based session
validation.

When saved session artifacts do exist, `status` uses that saved local session state to launch
browser validation and confirm whether it still reaches the real Coupang home session instead of
trusting the presence of local files alone.

## Credential File

To enable automatic login, create this file:

`~/.k-commerce/coupang/credentials.json`

When `--root-dir` is provided, the credential file is resolved under:

`<root-dir>/coupang/credentials.json`

Example:

```json
{
  "email": "you@example.com",
  "password": "your-password"
}
```

Both `email` and `password` must be non-empty strings.

If the file is missing, the CLI skips automatic login and opens the browser for manual login.

## Session Storage

The Coupang provider stores local state under:

`~/.k-commerce/coupang/`

When `--root-dir` is provided, the provider instead uses:

`<root-dir>/coupang/`

Files created there:

- `chrome-profile/`: persistent browser profile used to restore login state
- `cookies.dat`: saved browser cookies
- `session-meta.json`: metadata about the last successful login method
- `credentials.json`: optional credentials for automatic login
- `orders.json`: local order snapshot with collection metadata and nested Coupang orders

The `logout` tool removes saved session artifacts such as `chrome-profile/`, `cookies.dat`, and
`session-meta.json`, but preserves `credentials.json`.

These files are local machine state and should be treated as sensitive.

## Order Snapshot

The `order_sync` tool opens the saved Coupang session, discovers the year tabs visible in the
current account, skips `최근 6개월`, and walks each visible year page-by-page.

Default mode compares the newly collected data against the previous `orders.json` and prints an
order-count summary such as total orders plus added, changed, and deleted orders. The `refresh`
request field skips that comparison and prints only the total order count for the rebuilt snapshot.

When the previous snapshot has no failed pages, default mode also uses it as a page-tail cache:
after a fetched page exactly matches the same year/position in `orders.json`, the tool reuses
the remaining older orders for that year and stops requesting more pages. `refresh` always
requests every visible page and rebuilds the snapshot.

If one or more pages still fail after three retries, the CLI saves the successfully collected
orders and includes the failed year/page pairs in both the terminal summary and `orders.json`
metadata.

The `failed_only` request field reads those saved failure pairs, requests only those pages, merges
successful results into the previous snapshot by order ID, and keeps only pages that still fail in
the new `failedPages` metadata.

The `order_list`, `order_detail`, and `order_failures` tools read only the saved `orders.json`
snapshot. They do not open a browser. If the snapshot is missing, they return `sync_required` with
`next_tools: ["order_sync"]`.

The `order_search` tool opens the saved Coupang order page, searches the order-search field, and
collects matching order pages within the requested date scope. It returns a bounded summary list and
does not overwrite the saved `orders.json` snapshot.
