# K-Commerce CLI

K-Commerce CLI runs Coupang workflows from a local terminal. It uses the same tool contract as the
`k-commerce-mcp` MCP server.

Korean documentation is available in [README.ko.md](README.ko.md).

## Installation

```bash
pipx install k-commerce
```

Or:

```bash
uv tool install k-commerce
```

K-Commerce supports Python `3.11` through `3.13`.

## Usage

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

## MCP Server

To use K-Commerce from an MCP client, register the `k-commerce-mcp` command installed by the same
`k-commerce` package.

```json
{
  "mcpServers": {
    "k-commerce": {
      "command": "k-commerce-mcp"
    }
  }
}
```
