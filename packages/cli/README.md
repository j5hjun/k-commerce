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

Run the CLI from the workspace root:

```bash
uv run k-commerce login coupang
```

To isolate credentials and session data under a custom directory:

```bash
uv run k-commerce login coupang --root-dir /tmp/test-k-commerce
```

This option is intended for local verification and automated tests where credentials and session files
must be isolated from the default `~/.k-commerce` directory.

## Coupang Login Flow

The `coupang` login command tries the following in order:

1. Restore a previously saved browser session.
2. If no valid session exists, try automatic login with saved credentials.
3. If automatic login is unavailable or fails, wait for manual login in the browser.

When login succeeds, the CLI saves the session so the next run can reuse it.

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

These files are local machine state and should be treated as sensitive.
