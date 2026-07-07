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
| `product_detail` | Collect product details, detail images, and OCR text. |
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
