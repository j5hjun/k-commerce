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

Run the CLI from the workspace root:

```bash
uv run k-commerce login coupang
```

Check whether any saved local Coupang session artifacts still produce a live Coupang home session:

```bash
uv run k-commerce status coupang
```

Remove saved local Coupang session artifacts while preserving `credentials.json` for future automatic login:

```bash
uv run k-commerce logout coupang
```

Collect visible-year Coupang orders except the `최근 6개월` tab and update `orders.json` with a
diff summary:

```bash
uv run k-commerce order list coupang
```

Ignore the previous snapshot comparison and recreate `orders.json` from the latest collection:

```bash
uv run k-commerce order list coupang --refresh
```

To isolate credentials and session data under a custom directory:

```bash
uv run k-commerce login coupang --root-dir /tmp/test-k-commerce
```

The same `--root-dir` option also applies to status, logout, and order list commands:

```bash
uv run k-commerce status coupang --root-dir /tmp/test-k-commerce
uv run k-commerce logout coupang --root-dir /tmp/test-k-commerce
uv run k-commerce order list coupang --root-dir /tmp/test-k-commerce
```

This option is intended for local verification and automated tests where credentials and session files
must be isolated from the default `~/.k-commerce` directory.

If you pass an unsupported provider, the CLI reports the supported provider names from the shared
provider registry.

## Coupang Login Flow

The `coupang` login command tries the following in order:

1. Restore a previously saved browser session.
2. If no valid session exists, try automatic login with saved credentials.
3. If automatic login is unavailable or fails, wait for manual login in the browser.

When login succeeds, the CLI saves the session so the next run can reuse it.

## Login Status

The `status` command first checks whether saved session artifacts exist under the selected root
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

The `logout` command removes saved session artifacts such as `chrome-profile/`, `cookies.dat`, and
`session-meta.json`, but preserves `credentials.json`.

These files are local machine state and should be treated as sensitive.

## Order Snapshot

The `order list` command opens the saved Coupang session, discovers the year tabs visible in the
current account, skips `최근 6개월`, and walks each visible year page-by-page.

Default mode compares the newly collected data against the previous `orders.json` and prints an
order-count summary such as total orders plus added, changed, and deleted orders. `--refresh`
skips that comparison and prints only the total order count for the rebuilt snapshot.

If one or more pages still fail after three retries, the CLI saves the successfully collected
orders and includes the failed year/page pairs in both the terminal summary and `orders.json`
metadata.
