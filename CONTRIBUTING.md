# Contributing

## Development Setup

This repository uses `uv` workspace management.

- workspace root: `pyproject.toml`
- workspace packages:
  - `packages/cli`
  - `packages/mcp`

## Common Commands

Use these commands from the repository root unless noted otherwise.

```bash
uv sync
uv build
uv run pytest
uv run k-commerce --help
uv run k-commerce-mcp
```

## Test Layout

Tests are organized by package.

- `packages/cli/tests`
  - CLI unit/integration tests
  - provider/browser/store tests
- `packages/cli/tests/e2e`
  - file-backed login flow scenarios that run through the CLI entrypoint
  - uses `--root-dir` to isolate credentials and session data under a temporary directory
- `packages/cli/tests/smoke`
  - opt-in smoke tests that launch the real browser or depend on local credentials/session state
  - skipped by default unless explicit smoke env vars are provided
- `packages/mcp/tests`
  - MCP server and tool wiring tests

Run the full suite from the repository root:

```bash
uv run pytest
```

Run only the CLI e2e-style scenarios:

```bash
uv run pytest packages/cli/tests/e2e
```

Run the CLI smoke tests explicitly:

```bash
RUN_COUPANG_SMOKE=1 uv run pytest packages/cli/tests/smoke -m smoke
```

Smoke inputs by case:

- existing session
  - source: `~/.k-commerce/coupang`
  - copied artifacts: `chrome-profile/`, `cookies.dat`
- credentials
  - source: `~/.k-commerce/coupang`
  - copied artifacts: `credentials.json`
- invalid credentials
  - source: none
  - generated artifacts: invalid `credentials.json`
- manual login without credentials
  - source: none
  - starts from an empty temporary root directory
  - requires you to complete the browser login flow during the smoke run

## Branch Strategy

Use short-lived branches and treat `dev` as the main integration branch.

- `main`
  - stable branch for reviewed and validated changes
  - merge into `main` from `dev` when a release-ready set of changes is prepared
- `dev`
  - shared integration branch for ongoing team development
  - open feature, fix, docs, chore, and refactor pull requests against `dev`
- `feat/<topic>`
  - new feature work
  - example: `feat/mcp-server-bootstrap`
- `fix/<topic>`
  - bug fixes
  - example: `fix/package-entrypoint`
- `chore/<topic>`
  - maintenance, tooling, or repository setup
  - example: `chore/add-pr-template`
- `docs/<topic>`
  - documentation-only changes
  - example: `docs/add-contributing-guide`
- `refactor/<topic>`
  - internal code improvements without intended behavior changes
  - example: `refactor/server-layout`

Recommended flow:

1. Branch from `dev`
2. Open pull requests into `dev`
3. Merge `dev` into `main` after the changes are reviewed and considered stable

Documentation-only changes:

- use `docs/<topic>` when the documentation update is its own task
- include documentation changes in the same branch when they belong to a feature or fix
- for repository setup or process documentation on `dev`, updating `dev` directly can be acceptable during the initial setup phase

## Commit Message Convention

Use a simple Conventional Commits style:

```text
<type>: <summary>
```

Recommended types:

- `feat`: new functionality
- `fix`: bug fix
- `chore`: tooling, config, or maintenance
- `docs`: documentation changes
- `refactor`: internal restructuring without intended behavior change
- `test`: test additions or updates

Examples:

```text
feat: add MCP server entrypoint
fix: correct package script target
docs: add pull request template
chore: configure uv workspace
```

## Pull Requests

Before opening a pull request:

- branch from `dev` unless you are preparing a `dev` to `main` promotion
- make sure the branch name matches the change type
- target `dev` for normal development work
- target `main` only for reviewed changes that are ready to be promoted from `dev`
- fill out the PR template with created files, modified files, and test steps
- include only the scope needed for one planned feature or one clearly scoped fix

If a recommended check does not apply, explain why in the PR.
