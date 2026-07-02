# Cart Commands File Map

This directory contains the `cart` command and interactive cart workflows.

- `__init__.py` - `cart` command, exclusive `--list`/`--quantity`/`--delete` flag handling, and the list-browse, quantity-update, and delete (single/selected/clear) flows.
- `interactive.py` - shared prompt helpers and formatters for selecting cart items, choosing delete modes, confirming deletions, entering quantities, and rendering cart list/detail views.

Command files should stay thin: parse CLI options, collect user input, call provider services, and print terminal messages.
