# K-Commerce

K-Commerce provides a local Python CLI and stdio MCP server for Coupang workflows.

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

The package installs two commands:

- `k-commerce`: CLI for running tools directly from a terminal
- `k-commerce-mcp`: local stdio MCP server for MCP clients

K-Commerce supports Python `3.11` through `3.13`.

## CLI Usage

The current provider is `coupang`.

Check session status:

```bash
k-commerce status '{"provider":"coupang"}'
```

Log in:

```bash
k-commerce login '{"provider":"coupang"}'
```

Search products:

```bash
k-commerce search_products '{"provider":"coupang","keyword":"keyboard","sort":"relevance","max_results":10}'
```

For longer JSON requests, pass a request file:

```bash
k-commerce <tool-name> --request-file ./request.json
```

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

You can verify the local server with MCP Inspector:

```bash
npx @modelcontextprotocol/inspector k-commerce-mcp
```

## Tools

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

## Login And Local State

The `login` tool first tries to restore a saved browser session. If no valid session is available,
it tries automatic login with saved credentials. If automatic login is unavailable, it waits for
manual login in the browser.

To enable automatic login, create:

```text
~/.k-commerce/coupang/credentials.json
```

```json
{
  "email": "you@example.com",
  "password": "your-password"
}
```

Sessions, cookies, and order snapshots are stored under:

```text
~/.k-commerce/coupang/
```

Treat files in this directory as sensitive local account state.
