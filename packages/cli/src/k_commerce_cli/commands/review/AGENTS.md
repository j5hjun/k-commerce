# Review Commands Knowledge Base

## OVERVIEW

`review` command group for upload, edit, and delete workflows.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Group registration | `__init__.py` | Upload/edit/delete command group. |
| Upload | `upload.py` | List-only, item selection, upload request dispatch. |
| Edit | `edit.py` | Editable review selection and edit dispatch. |
| Delete | `delete.py` | Deletable review selection and delete dispatch. |
| Shared prompts | `interactive.py` | Item/rating/text prompts. |

## CONVENTIONS

- Command code collects user input and passes typed review requests to services.
- Preserve list-only modes; tests cover command-to-service plumbing.

## ANTI-PATTERNS

- Do not put browser form automation in command modules.
