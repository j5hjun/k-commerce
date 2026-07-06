# Cart Commands Knowledge Base

## OVERVIEW

Interactive `cart` command workflows: list-browse, quantity update, and delete modes.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Mode dispatch | `__init__.py` | Exclusive `--list`/`--quantity`/`--delete` handling. |
| List-browse | `list.py` | Default cart browse flow. |
| Quantity update | `quantity.py` | `--quantity` workflow. |
| Delete flows | `delete.py` | Single, selected, and clear delete flows. |
| Shared helpers | `common.py` | Provider/root-dir helpers and message constants. |
| Prompts/rendering | `interactive.py` | Item selection, confirmations, display helpers. |

## CONVENTIONS

- Keep cart identifiers together: `product_id`, `vendor_item_id`, and `item_id`.
- Prompting belongs here; provider mutation belongs in Coupang cart services.

## ANTI-PATTERNS

- Do not persist cart state from command code.
