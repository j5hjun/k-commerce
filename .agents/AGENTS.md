# Agent Assets Knowledge Base

## OVERVIEW

Repository-shared assets for AI agents. These are source-controlled project helpers, not user-local `~/.codex` skills.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Shared skills | `skills/` | Portable repo-local skills; see nested map. |

## CONVENTIONS

- Put repository-specific reusable skills under `.agents/skills/`, not in a personal Codex home directory.
- Keep skills portable across agent runtimes when possible.

## ANTI-PATTERNS

- Do not store personal/local-only instructions here; use git-ignored local notes instead.
