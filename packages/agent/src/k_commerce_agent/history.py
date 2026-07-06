import json
import re
from contextvars import ContextVar
from typing import Any

LIST_TOOLS = frozenset(
    {
        "review_list_reviewable",
        "review_list_editable",
        "search_products",
        "order_list",
        "cart_list",
    }
)

_TOOL_RESULT_RE = re.compile(r"^\[(?P<name>[^\]]+) 결과\] (?P<body>.+)$", re.DOTALL)

DEFAULT_SHOWN_ORDERS = 10
MAX_SHOWN_ORDERS = 50

turn_list_limit: ContextVar[int | None] = ContextVar("turn_list_limit", default=None)


def extract_requested_limit(text: str) -> int | None:
    patterns = (
        re.compile(r"(?:상위|최근|처음)\s*(\d+)\s*(?:개|건)?", re.IGNORECASE),
        re.compile(r"(\d+)\s*(?:개|건)\s*(?:만)?"),
        re.compile(r"(\d+)\s*(?:개|건)"),
    )
    for pattern in patterns:
        match = pattern.search(text)
        if not match:
            continue
        value = int(match.group(1))
        if 0 < value <= MAX_SHOWN_ORDERS:
            return value
    return None


def _order_list_limit(max_orders: int | None = None) -> int:
    if max_orders is not None and max_orders > 0:
        return max_orders
    limit = turn_list_limit.get()
    if limit is not None and limit > 0:
        return limit
    return DEFAULT_SHOWN_ORDERS


def _is_order_list_item(item: dict[str, Any]) -> bool:
    if "review_id" in item or "delivery_date" in item or "review_text" in item:
        return False
    if "product_name" in item and "rating" in item and "title" not in item:
        return False
    return (
        "products" in item
        or "title" in item
        or "ordered_at" in item
        or "total_price" in item
    )


def _product_name(product: dict[str, Any]) -> str:
    for key in ("vendorItemName", "productName", "product_name"):
        value = product.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _summarize_order(order: dict[str, Any], index: int) -> dict[str, Any]:
    products: list[dict[str, Any]] = []
    groups = order.get("deliveryGroupList")
    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, dict):
                continue
            product_list = group.get("productList")
            if not isinstance(product_list, list):
                continue
            for product in product_list:
                if not isinstance(product, dict):
                    continue
                name = _product_name(product)
                if not name:
                    continue
                price = product.get("discountedUnitPrice")
                if not isinstance(price, int):
                    price = product.get("unitPrice")
                products.append(
                    {
                        "name": name,
                        "quantity": product.get("quantity"),
                        "price": price if isinstance(price, int) else None,
                    }
                )

    return {
        "index": index,
        "order_id": order.get("orderId", order.get("order_id", index)),
        "title": order.get("title") or f"주문 {index}",
        "ordered_at": order.get("orderedAt"),
        "total_price": order.get("totalProductPrice"),
        "products": products[:3],
    }


def _compact_order_list(parsed: dict[str, Any], *, max_orders: int | None = None) -> str | None:
    items = parsed.get("items")
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict) and _is_order_list_item(first):
            compact_items = [
                {
                    "index": item.get("index", idx + 1),
                    "order_id": item.get("order_id", item.get("orderId")),
                    "title": item.get("title"),
                    "ordered_at": item.get("ordered_at", item.get("orderedAt")),
                    "total_price": item.get("total_price", item.get("totalProductPrice")),
                    "products": (item.get("products") or [])[:3],
                }
                for idx, item in enumerate(items)
                if isinstance(item, dict)
            ]
            return json.dumps(
                {
                    "message": parsed.get("message"),
                    "total_count": parsed.get("total_count", len(compact_items)),
                    "shown_count": parsed.get("shown_count", len(compact_items)),
                    "items": compact_items,
                },
                ensure_ascii=False,
            )

    payload = parsed.get("payload")
    if not isinstance(payload, dict):
        return None
    orders = payload.get("orders")
    if not isinstance(orders, list):
        return None

    meta = payload.get("meta")
    summary = meta.get("summary") if isinstance(meta, dict) else None
    total_orders = summary.get("totalOrders") if isinstance(summary, dict) else None
    total_count = int(total_orders) if isinstance(total_orders, int) else len(orders)

    shown = min(len(orders), _order_list_limit(max_orders))
    compact_items = [
        _summarize_order(order, idx + 1)
        for idx, order in enumerate(orders[:shown])
        if isinstance(order, dict)
    ]
    return json.dumps(
        {
            "message": parsed.get("message"),
            "total_count": total_count,
            "shown_count": len(compact_items),
            "items": compact_items,
        },
        ensure_ascii=False,
    )


def _compact_list_item(tool_name: str, item: dict[str, Any], index: int) -> dict[str, Any]:
    row_index = item.get("index", index + 1)

    if tool_name == "review_list_editable":
        review_text = item.get("review_text")
        compact_review_text = ""
        if isinstance(review_text, str) and review_text:
            compact_review_text = review_text if len(review_text) <= 120 else f"{review_text[:117]}..."
        return {
            "index": row_index,
            "review_id": item.get("review_id"),
            "product_id": item.get("product_id") or "",
            "order_id": item.get("order_id") or "",
            "product_name": item.get("product_name"),
            "rating": item.get("rating"),
            "review_text": compact_review_text,
            "written_at": item.get("written_at") or "",
        }

    if tool_name == "review_list_reviewable":
        return {
            "index": row_index,
            "product_id": item.get("product_id"),
            "product_name": item.get("product_name"),
            "delivery_date": item.get("delivery_date"),
            "completed_order_vendor_item_id": item.get("completed_order_vendor_item_id"),
            "vendor_item_id": item.get("vendor_item_id"),
            "review_url": item.get("review_url"),
        }

    if tool_name == "search_products":
        return {
            "index": row_index,
            "product_id": item.get("product_id"),
            "product_name": item.get("product_name"),
            "price": item.get("price"),
            "rating": item.get("rating"),
            "image_url": item.get("image_url"),
            "product_link": item.get("product_link"),
        }

    if tool_name == "cart_list":
        return {
            "index": row_index,
            "product_name": item.get("product_name"),
            "option_text": item.get("option_text"),
            "quantity": item.get("quantity"),
            "unit_price": item.get("unit_price"),
            "total_price": item.get("total_price"),
            "product_id": item.get("product_id"),
            "vendor_item_id": item.get("vendor_item_id"),
            "item_id": item.get("item_id"),
            "image_url": item.get("image_url"),
            "product_link": item.get("product_link"),
        }

    return {
        "index": row_index,
        "product_id": item.get("product_id"),
        "product_name": item.get("product_name"),
        "vendor_item_id": item.get("vendor_item_id"),
        "item_id": item.get("item_id"),
    }


def compact_tool_result_for_history(tool_name: str, raw: str) -> str:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    if tool_name not in LIST_TOOLS or not isinstance(parsed, dict):
        return raw

    if tool_name == "order_list":
        compact = _compact_order_list(parsed)
        if compact is not None:
            return compact

    items = parsed.get("items")
    if not isinstance(items, list):
        return raw

    compact_items = [
        _compact_list_item(tool_name, item, index)
        for index, item in enumerate(items)
        if isinstance(item, dict)
    ]
    compact = {
        "provider": parsed.get("provider"),
        "success": parsed.get("success"),
        "item_count": len(compact_items),
        "items": compact_items,
    }
    return json.dumps(compact, ensure_ascii=False)


def compact_tool_content(tool_name: str, content: Any) -> Any:
    """Shrink list-tool payloads before they reach the LLM or websocket."""

    if tool_name not in LIST_TOOLS:
        return content
    if isinstance(content, str):
        return compact_tool_result_for_history(tool_name, content)
    if isinstance(content, list):
        blocks: list[Any] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if isinstance(text, str):
                    blocks.append({**block, "text": compact_tool_result_for_history(tool_name, text)})
                    continue
            blocks.append(block)
        return blocks
    return content


def _compact_message_content(content: str) -> str:
    match = _TOOL_RESULT_RE.match(content.strip())
    if not match:
        return content

    tool_name = match.group("name")
    body = match.group("body")
    if tool_name not in LIST_TOOLS:
        return content

    return f"[{tool_name} 결과] {compact_tool_result_for_history(tool_name, body)}"


def prepare_chat_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Compress list-tool payloads and keep only the latest result per list tool."""

    prepared: list[dict[str, str]] = []
    latest_list_tool_idx: dict[str, int] = {}

    for message in messages:
        role = message.get("role", "")
        content = message.get("content", "")
        if role != "assistant" or not content:
            prepared.append(message)
            continue

        compacted = _compact_message_content(content)
        tool_match = _TOOL_RESULT_RE.match(compacted.strip())
        if not tool_match:
            prepared.append({"role": role, "content": compacted})
            continue

        tool_name = tool_match.group("name")
        if tool_name not in LIST_TOOLS:
            prepared.append({"role": role, "content": compacted})
            continue

        entry = {"role": role, "content": compacted}
        if tool_name in latest_list_tool_idx:
            prepared[latest_list_tool_idx[tool_name]] = entry
        else:
            latest_list_tool_idx[tool_name] = len(prepared)
            prepared.append(entry)

    return prepared
