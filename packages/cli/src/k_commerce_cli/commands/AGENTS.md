# CLI Commands File Map

This directory contains command handlers registered by `k_commerce_cli/cli.py`.

- `login.py` - `login` command, root-dir resolution, and provider login dispatch.
- `logout.py` - `logout` command, root-dir resolution, and provider session cleanup dispatch.
- `status.py` - `status` command, root-dir resolution, and provider login-status dispatch.
- `order.py` - `order` command group plus `order list` handler and refresh flag plumbing.
- `__init__.py` - command package marker.

Command files should stay thin: parse CLI options, resolve paths/provider names, call services, and print terminal messages.
