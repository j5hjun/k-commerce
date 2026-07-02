# k_commerce_cli File Map

This package contains the command-line application and service layer.

## Entry points

- `cli.py` - Typer/asyncclick app definition, command registration, and `main()` entry point.
- `base.py` - `Terminal` protocol/base abstraction used by command handlers.
- `__init__.py` - package marker/exports.

## Subpackages

- `commands/` - user-facing CLI commands (`login`, `logout`, `status`, `order`, `review`, `cart`). See `commands/AGENTS.md`.
- `services/` - provider interfaces, stores, browser automation, provider registry, and provider implementations. See `services/AGENTS.md`.
- `terminal/` - concrete terminal output adapter. See `terminal/AGENTS.md`.
