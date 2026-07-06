# MCP Tests Knowledge Base

## OVERVIEW

Tests for MCP server registration, shared-registry parity, and thin wrapper delegation.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Server behavior | `test_mcp_server.py` | Tool registration, descriptions, provider delegation, stdio runner behavior. |
| Registry parity | `test_tool_registry_parity.py` | MCP tool names/descriptions match the shared CLI registry exactly. |

## CONVENTIONS

- The expected tool set comes from `k_commerce_cli.services.tools.registry.list_tool_names()`.
- MCP tests should assert exactly the 16 canonical tools from the shared registry.
- Wrapper tests should prove delegation through `invoke_tool()` or the shared provider contract, not reimplemented provider logic.
- MCP schemas must keep `root_dir` out of request payloads.
- Manual MCP checks can use `npx @modelcontextprotocol/inspector uv run k-commerce-mcp` against the local stdio server.

## ANTI-PATTERNS

- Do not pin an MCP-only tool list that can drift from the shared registry.
- Do not add browser/session-dependent behavior to MCP tests.
