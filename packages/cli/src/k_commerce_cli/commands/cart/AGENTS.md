# Cart Commands File Map

This directory contains the `cart` command and interactive cart workflows.

- `__init__.py` - thin `cart` command definition: exclusive `--list`/`--quantity`/`--delete` flag handling that dispatches to the per-flow runners.
- `list.py` - `run_cart_list` flow for the default list-browse mode.
- `quantity.py` - `run_quantity_update` flow for the `--quantity` mode.
- `delete.py` - `run_delete` flow plus single/selected/clear delete sub-flows for the `--delete` mode.
- `common.py` - shared cart message constants and helpers (`get_provider` re-export, `resolve_root_dir`, `report_unless_list_success`, `cart_delete_request`, `fetch_cart_list`).
- `interactive.py` - shared prompt helpers and formatters for selecting cart items, choosing delete modes, confirming deletions, entering quantities, and rendering cart list/detail views.

Command files should stay thin: parse CLI options, collect user input, call provider services, and print terminal messages.
