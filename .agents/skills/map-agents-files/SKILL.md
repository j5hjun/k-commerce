---
name: map-agents-files
description: Create or update AGENTS.md files with concise file maps that explain what content lives where, so future agents can navigate a repository without opening files one by one. Use when the user asks to make a map, file guide, repository guide, directory guide, AGENTS.md navigation notes, or to document what files/directories contain across one or more AGENTS.md files.
---

# Map AGENTS Files

## Overview

Build directory-aware file maps inside `AGENTS.md` files. Treat each `AGENTS.md` as a local navigation guide for its directory and descendants, with enough detail to find relevant files quickly without reading source files first.

## Workflow

1. Find every relevant `AGENTS.md`.
   - Use `find . -name AGENTS.md -print | sort` so hidden directories such as `.github/` are included.
   - Also inspect tracked/untracked status if this is a Git repo; many `AGENTS.md` files may be newly created.

2. Build a source-of-truth file list.
   - Prefer `rg --files` for normal repository files.
   - Use `find` when hidden directories must be included.
   - Exclude generated/local-only directories unless the user explicitly asks for them: `.git/`, `.venv/`, `.uv-cache/`, `.pytest_cache/`, `.ruff_cache/`, `.serena/`, `dist/`, `build/`, `node_modules/`, `__pycache__/`, and cache/artifact folders.

3. Infer file roles efficiently.
   - Use paths, filenames, package metadata, tests, and top-level symbols to summarize intent.
   - For Python, an AST pass that lists top-level classes/functions is usually enough.
   - Read whole files only when names and symbols are not enough to write an accurate map.

4. Decide each `AGENTS.md` scope.
   - Root `AGENTS.md`: summarize repository-wide layout, top-level files, major packages, and generated directories to ignore.
   - Intermediate `AGENTS.md`: summarize direct child directories and route readers to deeper `AGENTS.md` files.
   - Leaf `AGENTS.md`: list files in that directory and explain each file's role.
   - Test directories: group tests by scenario or behavior and name helper files.

5. Edit maps.
   - Preserve existing non-map instructions unless the user asked to replace them.
   - If a file already has a stale map section, replace that section rather than duplicating it.
   - Use short headings such as `# Repository Map`, `# Services File Map`, or `# CLI Tests File Map`.
   - Prefer bullets of the form ``- `file.py` - concise role.``.
   - Mention sibling/deeper `AGENTS.md` files where they provide more detail.

6. Validate coverage.
   - Confirm every discovered `AGENTS.md` is non-empty.
   - Spot-check representative high-level and leaf maps.
   - Report any intentionally ignored generated directories and any existing unrelated changes you did not touch.

## Map Style

- Keep maps concise and navigational, not exhaustive API documentation.
- Use relative paths from the current `AGENTS.md` when referring to local files; use repository-relative paths when pointing outside the current scope.
- Include the purpose of important config files (`pyproject.toml`, package manifests, CI templates, issue forms).
- In source directories, describe ownership and runtime role: entry points, command handlers, service abstractions, concrete providers, adapters, storage, and type definitions.
- In test directories, describe what behavior each test file covers rather than restating every test name.
- Call out generated/local-only directories in the root map so future agents do not mistake them for source.

## Good Output Pattern

```markdown
# Example File Map

This directory contains the provider service layer.

- `base.py` - shared provider, browser, store, and service protocols.
- `registry.py` - provider lookup and list helpers.
- `store.py` - persistent credentials/session/order artifact storage.
- `providers/` - concrete provider implementations. See `providers/AGENTS.md`.
```
