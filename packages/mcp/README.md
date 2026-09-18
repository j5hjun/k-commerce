# K-Commerce MCP

K-Commerce MCP is a local stdio MCP server for running Coupang workflows from MCP clients.

Korean documentation is available in [README.ko.md](README.ko.md).

## Installation

Install with `pipx`:

```bash
pipx install k-commerce
```

Or install with `uv`:

```bash
uv tool install k-commerce
```

The installed `k-commerce-mcp` command starts the local stdio MCP server.

## MCP Registration

Register the server in your MCP client configuration:

```json
{
  "mcpServers": {
    "k-commerce": {
      "command": "k-commerce-mcp"
    }
  }
}
```

For local development from the repository root, you can also register:

```json
{
  "mcpServers": {
    "k-commerce": {
      "command": "uv",
      "args": ["run", "k-commerce-mcp"]
    }
  }
}
```

You can verify the local server with MCP Inspector:

```bash
npx @modelcontextprotocol/inspector k-commerce-mcp
```

## Tools

The current provider is `coupang`.

| Tool | Description |
| --- | --- |
| `get_providers` | Return the supported provider list. |
| `login` | Run the provider login flow. |
| `status` | Check saved provider session status. |
| `logout` | Remove saved session artifacts. |
| `order_sync` | Collect provider orders into the local order snapshot. |
| `order_list` | Return saved orders. |
| `order_search` | Search orders on the provider order page. |
| `order_detail` | Return details for one saved order. |
| `order_failures` | Return order failure items that need attention. |
| `product_detail` | Get product details and detail images. |
| `cart_list` | Return cart items. |
| `cart_update_quantity` | Update the quantity of one cart item. |
| `cart_delete_item` | Delete one cart item. |
| `cart_delete_items` | Delete multiple cart items. |
| `cart_clear` | Clear the cart. |
| `search_products` | Search provider products. |
| `review_list_reviewable` | Return products eligible for review. |
| `review_list_editable` | Return editable reviews. |
| `review_upload` | Upload a product review. |
| `review_edit` | Edit a product review. |
| `review_delete` | Delete a product review. |

### Product detail images

`product_detail` returns product JSON in both `structuredContent` and a text block,
followed by base64 MCP image blocks containing the original detail images. The calling
client and model must support image input. No OCR model, Watsonx credentials, or `.env`
is needed by this tool; normal Coupang login/session requirements still apply.
The CLI returns metadata and image URLs only. The former `ocr` and `ocr_status` fields
have been removed. `image_delivery` lists every URL as `attached`, `failed`, or `skipped`
in source order; image blocks follow the order of the `attached` entries.

Attachments support HTTPS Coupang CDN JPEG, PNG, WebP, and GIF responses without redirects.
Limits are 20 images, 5 MiB per image, 10 MiB total original bytes, and 30 seconds of download time.
Failed or omitted images retain their URLs and warnings; product metadata remains available.
The server does not resize or crop images, so model-specific size limits still apply.
