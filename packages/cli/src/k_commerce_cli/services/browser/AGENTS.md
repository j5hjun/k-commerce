# Browser Services File Map

This directory contains browser automation adapters used by provider services.

- `nodriver.py` - Nodriver-backed browser implementation, cookie handling, runtime launch/stop logic, tab selection, and session wrapper classes.
- `__init__.py` - browser package exports.

Provider code should depend on the browser protocols from `services/base.py` where possible and use this directory for the concrete Nodriver runtime.
