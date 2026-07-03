# MCP Tools File Map

This directory contains MCP tool functions registered by `../server.py`.

- `get_providers.py` - `get_providers` tool returning available provider names.
- `login.py` - `login` tool that delegates provider login.
- `login_status.py` - `login_status` tool that delegates provider status checks.
- `logout.py` - `logout` tool that delegates provider logout/session cleanup.
- `order.py` - `order_list` tool that delegates provider order snapshot collection.
- `cart.py` - cart list, quantity update, delete, and clear tools.
- `__init__.py` - tool package exports.

Keep tool modules thin: validate/describe MCP-facing inputs and delegate business behavior to the CLI service layer.
