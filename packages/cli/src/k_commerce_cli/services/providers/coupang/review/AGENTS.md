# Coupang Review Service File Map

This directory contains Coupang review listing, upload, edit, and delete automation.

- `service.py` - `CoupangReviewService`, session handling, review list orchestration, result conversion, and public review methods.
- `upload.py` - browser automation mixin for opening review forms, detecting upload state, and submitting new reviews.
- `edit.py` - browser automation mixin for opening existing reviews, validating identifiers, and submitting edits.
- `delete.py` - browser automation mixin for locating reviews and confirming review deletion.
- `browser.py` - helpers for deserializing browser/CDP evaluation results.
- `state.py` - review workflow state constants and user-facing state messages.
- `type.py` - review request/result dataclasses plus browser-scrape helper dataclasses.
- `utils.py` - Coupang review URLs, URL builders, formatting helpers, and text normalization utilities.
- `__init__.py` - review package marker.

Keep provider-facing service construction aligned with `BaseProvider`: accept `provider`, `store`, `browser`, and optional `terminal`.
