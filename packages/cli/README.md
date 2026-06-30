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

List reviewable products only:

```bash
uv run k-commerce review upload coupang --list
```

Write a review interactively:

```bash
uv run k-commerce review upload coupang
```

List editable reviews only:

```bash
uv run k-commerce review edit coupang --list
```

Edit a review interactively:

```bash
uv run k-commerce review edit coupang
```

To isolate credentials and session data under a custom directory:

```bash
uv run k-commerce login coupang --root-dir /tmp/test-k-commerce
```

The same `--root-dir` option also applies to status, logout, and review commands:

```bash
uv run k-commerce status coupang --root-dir /tmp/test-k-commerce
uv run k-commerce logout coupang --root-dir /tmp/test-k-commerce
uv run k-commerce review upload coupang --list --root-dir /tmp/test-k-commerce
uv run k-commerce review upload coupang --root-dir /tmp/test-k-commerce
uv run k-commerce review edit coupang --list --root-dir /tmp/test-k-commerce
uv run k-commerce review edit coupang --root-dir /tmp/test-k-commerce
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

## Coupang Review Commands

The `review` command group reuses a saved Coupang session.

### Interactive upload

```bash
uv run k-commerce review upload coupang
```

This loads the reviewable product list, lets you pick an item with arrow keys, then prompts
for rating and review text before submitting.

### Upload list only

```bash
uv run k-commerce review upload coupang --list
```

### Interactive edit

```bash
uv run k-commerce review edit coupang
```

This loads the editable review list, lets you pick an existing review with arrow keys, then prompts
for rating and review text before submitting the update.

### Edit list only

```bash
uv run k-commerce review edit coupang --list
```

If no saved session exists, or the session is no longer logged in, the command fails with a clear
message instead of opening a login flow automatically.

Image or video attachments are not supported in this command.

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

The `logout` command removes saved session artifacts such as `chrome-profile/`, `cookies.dat`, and
`session-meta.json`, but preserves `credentials.json`.

These files are local machine state and should be treated as sensitive.
