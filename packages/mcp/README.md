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

- `get_providers`: 현재 지원 중인 provider 이름 목록을 반환합니다.
  - return: `list[str]`

- `login`: provider name을 받아 로그인 플로우를 실행합니다.
  - example: `provider="coupang"`
  - return: `LoginResult`

- `login_status`: 저장된 로컬 세션이 실제로 유효한 로그인 상태인지 확인합니다.
  - example: `provider="coupang"`
  - return: `StatusResult`

- `logout`: 저장된 로컬 세션 아티팩트를 제거합니다.
  - example: `provider="coupang"`
  - return: `LogoutResult`

- `order_list`: 주문 내역 스냅샷을 수집/조회합니다.
  - example: `provider="coupang", refresh=false, failed_only=false`
  - return: `OrderResult`

- `cart_list`: 장바구니 상품 목록을 조회합니다.
  - example: `provider="coupang", refresh=false`
  - return: `ListCartResult`

- `cart_update_quantity`: 장바구니 상품 수량을 변경합니다.
  - example: `provider="coupang", quantity=3, product_id="...", vendor_item_id="...", item_id="..."`
  - return: `CartQuantityUpdateResult`

- `cart_update_quantity_smart`: 장바구니 화면에 보이는 index 또는 상품명으로 수량을 변경합니다.
  - example: `provider="coupang", quantity=5, item_index=1`
  - example: `provider="coupang", quantity=5, product_name="Qiaokao 철제 서랍형 수납박스"`
  - return: `CartQuantityUpdateResult`

- `cart_delete_item`: 장바구니에서 상품 1건을 삭제합니다.
  - example: `provider="coupang", product_id="...", vendor_item_id="...", item_id="..."`
  - return: `CartDeleteResult`

- `cart_delete_items`: 장바구니에서 여러 상품을 한 번에 삭제합니다.
  - example: `provider="coupang", items=[{"product_id": "...", "vendor_item_id": "...", "item_id": "..."}]`
  - return: `CartDeleteResult`

- `cart_clear`: 장바구니의 모든 상품을 삭제합니다.
  - example: `provider="coupang"`
  - return: `CartDeleteResult`

## Cart CLI Mapping

| CLI | MCP |
| --- | --- |
| `k-commerce cart coupang` / `--list` | `cart_list` |
| `k-commerce cart coupang --quantity` | `cart_update_quantity` |
| visible item based quantity update | `cart_update_quantity_smart` |
| `k-commerce cart coupang --delete` (단일 삭제) | `cart_delete_item` |
| `k-commerce cart coupang --delete` (선택 삭제) | `cart_delete_items` |
| `k-commerce cart coupang --delete` (전체 삭제) | `cart_clear` |

프론트에서는 `cart_list`로 받은 `items`를 화면에 표시한 뒤, 사용자가 고른 항목의
`product_id`, `vendor_item_id`, `item_id`로 삭제/수량 변경 도구를 호출하면 됩니다.

Order snapshot collection is also available through the CLI command
`k-commerce order list coupang`.

## Supported Providers

The MCP tools currently support:

- `coupang`
