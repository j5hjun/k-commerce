# Review Commands File Map

This directory contains the `review` command group and interactive review workflows.

- `__init__.py` - review command group registration for upload, edit, and delete subcommands.
- `upload.py` - `review upload` command, list-only mode, reviewable item selection, and upload request dispatch.
- `edit.py` - `review edit` command, editable review selection, edit prompt flow, and edit request dispatch.
- `delete.py` - `review delete` command, deletable review selection and delete request dispatch.
- `interactive.py` - shared prompt helpers for selecting review items, ratings, and review text.

Command files should stay thin: parse CLI options, collect user input, call provider services, and print terminal messages.
