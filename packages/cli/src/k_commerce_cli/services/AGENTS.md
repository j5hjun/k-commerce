# Services File Map

This directory contains the CLI service layer and provider abstraction.

## Core service contracts

- `base.py` - protocols/base classes for browser sessions, stores, providers, auth services, order services, review services, and provider implementations.
- `models.py` - shared service data models such as `Credentials`.
- `paths.py` - `ProviderPaths`, the filesystem layout helper for provider artifacts.
- `registry.py` - provider factory registry plus `get_provider()` and `list_providers()`.
- `store.py` - `ProviderStore`, which reads/writes credentials, sessions, metadata, orders, and provider artifacts.
- `__init__.py` - service package exports.

## Subdirectories

- `browser/` - browser automation runtime abstraction. See `browser/AGENTS.md`.
- `providers/` - concrete commerce provider implementations. See `providers/AGENTS.md`.
- `types/` - shared result and provider-name types. See `types/AGENTS.md`.

## Provider Service Rules

- Add provider capabilities through `BaseProvider` service protocols and `*_service_cls` wiring instead of growing concrete provider classes with direct implementation methods.
