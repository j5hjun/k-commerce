# Tool Contract Knowledge Base

## OVERVIEW

Shared canonical tool layer used by the generic CLI runner and MCP wrappers.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Tool registry | `registry.py` | Canonical tool names, descriptions, and request model bindings. |
| Tool dispatch | `invoke.py` | Payload validation, request dataclass construction, provider routing. |
| Runtime/options/errors | `types.py` | `ToolRuntimeOptions`, provider factory protocols, request errors. |
| JSON boundary | `serialization.py` | Deterministic JSON-compatible result conversion. |
| Package exports | `__init__.py` | Public import surface for CLI/MCP consumers. |

## CONVENTIONS

- This directory is the source of truth for canonical tool names and request payloads.
- `invoke_tool()` is the shared dispatch path for MCP wrappers and `k-commerce <tool-name> <request>`.
- Keep `root_dir` in `ToolRuntimeOptions`; canonical JSON payloads must reject it.
- Keep request parsing typed and explicit. Unknown tools, invalid payloads, and validation errors should return structured tool errors at the boundary.
- Preserve sanitized generic CLI errors for unexpected provider/browser failures; do not leak tracebacks, absolute paths, cookies, tokens, or raw browser exception text.
- `serialization.py` should stay pure and deterministic.

## ANTI-PATTERNS

- Do not duplicate tool validation in command modules or MCP wrappers.
- Do not add provider/session behavior here beyond dispatch and runtime-option plumbing.
- Do not add non-canonical session-state aliases; the current session-state tool name is `status`.
