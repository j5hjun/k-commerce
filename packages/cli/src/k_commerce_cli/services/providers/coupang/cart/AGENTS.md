# Coupang Cart Knowledge Base

## OVERVIEW

Browser-backed cart subdomain for listing items, updating quantities, deleting selected items, and clearing the cart.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Service/session orchestration | `service.py` | `CoupangCartService`, cart session lifecycle. |
| Delete operations | `delete.py` | Single, batch, and clear-cart browser deletion. |
| Runtime state | `state.py` | Cart state holder and messages. |
| Request/result types | `type.py` | Cart item, update, delete dataclasses. |
| Selectors/helpers | `utils.py` | Cart URL, selectors, parsing helpers. |

## CONVENTIONS

- The stable cart identity tuple is `product_id`, `vendor_item_id`, `item_id`.
- Return typed cart result objects instead of raw browser dictionaries.
- Preserve graceful `not_logged_in` and browser-closed messages.

## ANTI-PATTERNS

- Do not add cart prompting here; command interaction belongs in `commands/cart/`.
- Do not persist cart data through `ProviderStore`; read it from the live browser session.
