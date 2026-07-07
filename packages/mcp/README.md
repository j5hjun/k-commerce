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

Open the local stdio server in MCP Inspector:

```bash
npx @modelcontextprotocol/inspector uv run k-commerce-mcp
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
- `order_sync`: Collects provider orders into the local order snapshot.
- `order_list`: Lists saved provider orders without opening a browser.
- `order_search`: Searches the browser-backed provider order page and returns matched orders.
- `order_detail`: Shows one saved provider order in detail.
- `order_failures`: Lists saved provider orders that need attention.
- `product_detail`: Collects product details, detail images, and OCR text from a provider product page.
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

## Compatibility CLI Aliases

The human-oriented CLI aliases are available for local debugging and interactive browser checks.
Automation should prefer the canonical MCP tool names and request payloads.

| Alias command | Canonical MCP tool |
| --- | --- |
| `k-commerce login coupang` | `login` |
| `k-commerce status coupang` | `status` |
| `k-commerce logout coupang` | `logout` |
| `k-commerce order sync coupang` | `order_sync` |
| `k-commerce order list coupang` | `order_list` |
| `k-commerce order search coupang KEYWORD` | `order_search` |
| `k-commerce order detail coupang ORDER_ID` | `order_detail` |
| `k-commerce order failures coupang` | `order_failures` |
| `k-commerce product detail coupang URL` | `product_detail` |
| `k-commerce search coupang KEYWORD` | `search_products` |
| `k-commerce cart coupang` / `--list` | `cart_list` |
| `k-commerce cart coupang --quantity` | `cart_update_quantity` |
| `k-commerce cart coupang --delete` (단일 삭제) | `cart_delete_item` |
| `k-commerce cart coupang --delete` (선택 삭제) | `cart_delete_items` |
| `k-commerce cart coupang --delete` (전체 삭제) | `cart_clear` |
| `k-commerce review upload coupang` | `review_upload` |
| `k-commerce review edit coupang` | `review_edit` |
| `k-commerce review delete coupang` | `review_delete` |

프론트에서는 `cart_list`로 받은 `items`를 화면에 표시한 뒤, 사용자가 고른 항목의
`product_id`, `vendor_item_id`, `item_id`로 삭제/수량 변경 도구를 호출하면 됩니다.

## Supported Providers

The MCP tools currently support:

- `coupang`
