# K-Commerce MCP

K-Commerce MCP는 쿠팡 작업을 로컬 MCP 클라이언트에서 실행하기 위한 stdio MCP 서버입니다.

English documentation is available in [README.md](README.md).

## 설치

`pipx`로 설치:

```bash
pipx install k-commerce
```

또는 `uv`로 설치:

```bash
uv tool install k-commerce
```

설치 후 `k-commerce-mcp` 명령이 로컬 stdio MCP 서버를 실행합니다.

## MCP 등록

MCP 클라이언트 설정에 서버를 등록합니다.

```json
{
  "mcpServers": {
    "k-commerce": {
      "command": "k-commerce-mcp"
    }
  }
}
```

로컬 개발 중에는 저장소 루트에서 다음처럼 실행할 수도 있습니다.

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

등록 확인은 MCP Inspector로 할 수 있습니다.

```bash
npx @modelcontextprotocol/inspector k-commerce-mcp
```

## 제공 도구

현재 지원 provider는 `coupang`입니다.

| 도구 | 설명 |
| --- | --- |
| `get_providers` | 지원하는 provider 목록을 반환합니다. |
| `login` | provider 로그인 플로우를 실행합니다. |
| `status` | 저장된 provider 세션 상태를 확인합니다. |
| `logout` | 저장된 세션 아티팩트를 제거합니다. |
| `order_sync` | provider 주문을 수집해 로컬 주문 스냅샷에 저장합니다. |
| `order_list` | 저장된 주문 목록을 반환합니다. |
| `order_search` | provider 주문 페이지에서 주문을 검색합니다. |
| `order_detail` | 저장된 주문 하나의 상세 정보를 반환합니다. |
| `order_failures` | 확인이 필요한 주문 실패 항목을 반환합니다. |
| `product_detail` | 상품 상세, 상세 이미지, OCR 텍스트를 수집합니다. |
| `cart_list` | 장바구니 항목을 반환합니다. |
| `cart_update_quantity` | 장바구니 항목 수량을 변경합니다. |
| `cart_delete_item` | 장바구니 항목 하나를 삭제합니다. |
| `cart_delete_items` | 장바구니 항목 여러 개를 삭제합니다. |
| `cart_clear` | 장바구니 전체를 비웁니다. |
| `search_products` | provider 상품을 검색합니다. |
| `review_list_reviewable` | 리뷰 작성 가능한 상품을 반환합니다. |
| `review_list_editable` | 수정 가능한 리뷰를 반환합니다. |
| `review_upload` | 상품 리뷰를 작성합니다. |
| `review_edit` | 상품 리뷰를 수정합니다. |
| `review_delete` | 상품 리뷰를 삭제합니다. |
