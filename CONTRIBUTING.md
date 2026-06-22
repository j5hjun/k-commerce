# Contributing

## Development Setup

This repository uses `uv` workspace management.

- workspace root: `pyproject.toml`
- current package: `packages/mcp`

## Common Commands

Use these commands from the repository root unless noted otherwise.

```bash
uv sync --all-packages
uv build
uv run k-commerce-mcp
```

## Branch Strategy

Use short-lived branches and keep `main` in a releasable state.

- `main`
  - default branch
  - keep stable and review-approved
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

- make sure the branch name matches the change type
- fill out the PR template with created files, modified files, and test steps
- include only the scope needed for one planned feature or one clearly scoped fix

If a recommended check does not apply, explain why in the PR.
