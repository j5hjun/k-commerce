# k_commerce_cli Knowledge Base

## OVERVIEW

Import package for CLI composition, terminal/prompt adapters, command handlers, and service/provider code.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| CLI composition | `cli.py` | Registers all commands and initializes terminal/prompts in context. |
| Terminal contract | `base.py` | Abstract terminal output protocol. |
| Prompt helpers | `prompts.py` | Questionary-backed async prompts. |
| Commands | `commands/` | User-facing command handlers; see local map. |
| Services | `services/` | Provider contracts, canonical tool contract, and implementations; see local map. |
| Terminal adapter | `terminal/asyncclick.py` | Concrete terminal adapter. |

## CONVENTIONS

- Keep the app entry point thin; command registration belongs here, behavior belongs below.
- `cli.py` dispatches unknown canonical names such as `search_products` and `review_upload` to the generic `k-commerce <tool-name> '<json-request>'` runner.
- Preserve asyncclick patterns; do not describe this package as Typer-based.

## ANTI-PATTERNS

- Do not make `cli.py` a workflow implementation file.
