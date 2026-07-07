# K-Commerce

K-Commerce는 쿠팡 작업을 로컬에서 실행하기 위한 Python CLI와 stdio MCP 서버를 함께 제공합니다.

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

설치하면 두 명령을 사용할 수 있습니다.

- `k-commerce`: 터미널에서 도구를 직접 실행하는 CLI
- `k-commerce-mcp`: MCP 클라이언트가 실행하는 로컬 stdio 서버

지원 Python 버전은 `3.11`부터 `3.13`까지입니다.

## CLI 사용

현재 지원 provider는 `coupang`입니다.

상태 확인:

```bash
k-commerce status '{"provider":"coupang"}'
```

로그인:

```bash
k-commerce login '{"provider":"coupang"}'
```

상품 검색:

```bash
k-commerce search_products '{"provider":"coupang","keyword":"keyboard","sort":"relevance","max_results":10}'
```

요청 JSON이 길면 파일로 전달할 수 있습니다.

```bash
k-commerce <tool-name> --request-file ./request.json
```

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

등록 확인은 MCP Inspector로 할 수 있습니다.

```bash
npx @modelcontextprotocol/inspector k-commerce-mcp
```

## 제공 도구

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

## 로그인과 로컬 상태

`login` 도구는 저장된 브라우저 세션을 먼저 복원하고, 유효한 세션이 없으면 저장된
credentials로 자동 로그인을 시도합니다. 자동 로그인이 불가능하면 브라우저에서 수동 로그인을
기다립니다.

자동 로그인을 사용하려면 다음 파일을 만듭니다.

```text
~/.k-commerce/coupang/credentials.json
```

```json
{
  "email": "you@example.com",
  "password": "your-password"
}
```

세션, 쿠키, 주문 스냅샷은 기본적으로 다음 경로에 저장됩니다.

```text
~/.k-commerce/coupang/
```

이 디렉터리의 파일은 로컬 계정 상태를 포함할 수 있으므로 민감하게 취급해야 합니다.
