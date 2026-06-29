# Providers File Map

This directory contains concrete commerce provider packages.

- `coupang/` - Coupang auth, order collection, provider assembly, and provider-specific data types. See `coupang/AGENTS.md`.
- `__init__.py` - provider package exports.

Provider lookup and registration lives in `../registry.py`; shared provider protocols live in `../base.py`.
