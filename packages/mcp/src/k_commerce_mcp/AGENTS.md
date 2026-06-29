# k_commerce_mcp File Map

This package contains the MCP server entry point and tool registrations.

- `server.py` - `create_mcp_server()` factory, tool registration, and `main()` stdio runner.
- `tools/` - MCP tool implementations for provider actions. See `tools/AGENTS.md`.
- `__init__.py` - MCP package marker/exports.

The server delegates provider behavior to `packages/cli/src/k_commerce_cli/services`.
