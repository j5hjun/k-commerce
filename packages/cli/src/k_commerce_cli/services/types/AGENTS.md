# Service Types File Map

This directory contains shared type definitions returned by provider services.

- `auth.py` - `LoginResult`, `LogoutResult`, and `StatusResult` dataclasses.
- `provider.py` - `ProviderName` enum/literal-style provider identifier definitions.
- `order.py` - shared order-related type surface; currently a package placeholder for cross-provider order types.
- `review.py` - shared review-related type surface re-exported from the Coupang review dataclasses.
- `__init__.py` - type package exports.

## Type Export Rules

- Expose shared service result types through scoped files such as `auth.py`, `order.py`, or `review.py`, then re-export them from `types/__init__.py`.
