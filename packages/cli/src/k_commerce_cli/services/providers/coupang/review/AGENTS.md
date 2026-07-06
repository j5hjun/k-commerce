# Coupang Review Knowledge Base

## OVERVIEW

Review listing, upload, edit, and delete automation for Coupang.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Public service | `service.py` | `CoupangReviewService` and result conversion. |
| Upload flow | `upload.py` | Opens forms, detects state, submits new reviews. |
| Edit flow | `edit.py` | Opens existing reviews, validates identifiers, submits edits. |
| Delete flow | `delete.py` | Locates reviews and confirms deletion. |
| Browser decoding | `browser.py` | Browser/CDP evaluation result helpers. |
| State/messages | `state.py` | Review workflow state constants. |
| Types/helpers | `type.py`, `utils.py` | Request/result dataclasses, URLs, formatting. |

## CONVENTIONS

- Use state checks for login, editability, already-reviewed, and identifier mismatch.
- Keep provider-facing constructor shape compatible with `BaseProvider`.
- Preserve repeated scroll/stability loops and JSON-encoded identifiers unless replacing the whole browser strategy.

## ANTI-PATTERNS

- Do not move review prompt logic here; command prompts live in `commands/review/`.
