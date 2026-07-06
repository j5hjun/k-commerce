# K-Commerce MCP

MCP server for Korean commerce workflows.

## Setup

Install the workspace from the repository root:

```bash
uv sync
```

Run the MCP server from the repository root:

```bash
uv run k-commerce-mcp
```

## Tools

The MCP tool contract is the source of truth for tool names, request payloads, validation, and
service invocation. MCP wrappers keep explicit FastMCP signatures and delegate through
`k_commerce_cli.services.tools.invoke.invoke_tool`.

Canonical tools:

- `get_providers`: Returns supported provider names.
- `login`: Runs the provider login flow.
- `status`: Checks whether saved provider session state is valid.
- `logout`: Removes saved provider session artifacts while preserving credentials.
- `order_list`: Collects or reads the provider order snapshot.
- `cart_list`: Lists cart items.
- `cart_update_quantity`: Updates one cart item quantity.
- `cart_delete_item`: Deletes one cart item.
- `cart_delete_items`: Deletes multiple cart items.
- `cart_clear`: Clears all cart items.
- `search_products`: Searches provider products.
- `review_list_reviewable`: Lists products eligible for review.
- `review_list_editable`: Lists editable reviews.
- `review_upload`: Uploads a product review.
- `review_edit`: Edits a product review.
- `review_delete`: Deletes a product review.

MCP requests do not include `root_dir`. That path override is available only through CLI
human/debug compatibility aliases.

The same canonical tools can be exercised locally through the generic CLI runner:

```bash
uv run k-commerce <tool-name> '<json-request>'
uv run k-commerce <tool-name> --request-file ./request.json
```

## Cart CLI Mapping

| CLI | MCP |
| --- | --- |
| `k-commerce cart coupang` / `--list` | `cart_list` |
| `k-commerce cart coupang --quantity` | `cart_update_quantity` |
| `k-commerce cart coupang --delete` (단일 삭제) | `cart_delete_item` |
| `k-commerce cart coupang --delete` (선택 삭제) | `cart_delete_items` |
| `k-commerce cart coupang --delete` (전체 삭제) | `cart_clear` |

프론트에서는 `cart_list`로 받은 `items`를 화면에 표시한 뒤, 사용자가 고른 항목의
`product_id`, `vendor_item_id`, `item_id`로 삭제/수량 변경 도구를 호출하면 됩니다.

Order snapshot collection is also available through the CLI command `k-commerce order list coupang`.

## Supported Providers

The MCP tools currently support:

- `coupang`
