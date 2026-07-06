import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessageChunk

from k_commerce_agent.agent import (
    ModelNotConfiguredError,
    build_agent,
    is_model_configured,
)
from k_commerce_agent.api_models import (
    CartBulkDeleteBody,
    CartDeleteBody,
    CartItemResponse,
    CartListResponse,
    CartMutationResponse,
    CartQuantityUpdateBody,
    DeliveryTrackingEventResponse,
    DeliveryTrackingResponse,
    EditableReviewItemResponse,
    EditableReviewListResponse,
    MemorySummaryResponse,
    OrderGroupResponse,
    OrderProductResponse,
    OrdersResponse,
    ProviderLoginResponse,
    ProviderLoginStatusResponse,
    ReviewDeleteRequestBody,
    ReviewEditRequestBody,
    ReviewListResponse,
    ReviewMutationResponse,
    ReviewUploadRequestBody,
    ReviewableItemResponse,
    ReviewableListResponse,
)
from k_commerce_agent.config import settings
from k_commerce_agent.memory import SessionMemoryStore
from k_commerce_agent.mcp_client import load_tools
from k_commerce_agent.recommendations import run_recommendation_graph
from k_commerce_agent.schemas import ChatRequest, ToolInfo, ToolsResponse

router = APIRouter()
memory_store = SessionMemoryStore(settings.memory_path)
QUANTITY_PATTERNS = (
    re.compile(r"장바구니\s*(?P<index>\d+)번.*?수량\s*(?P<quantity>\d+)개"),
    re.compile(r"(?P<name>.+?)\s+수량\s*(?P<quantity>\d+)개"),
)
DIRECT_LOGIN_COMMANDS = {
    "로그인진행해줘",
    "로그인해줘",
    "자동로그인",
    "쿠팡로그인",
    "coupang.login()",
    "mcp:login",
}


def _looks_like_recommendation_request(message: str) -> bool:
    return any(
        token in message
        for token in ("추천", "비교", "최저가", "뭐 살", "뭐 사", "재구매", "가성비", "비슷한")
    )


def _looks_like_login_request(message: str) -> bool:
    normalized = re.sub(r"\s+", "", message).lower()
    return normalized in DIRECT_LOGIN_COMMANDS


def _format_login_chat_message(message: str, success: bool) -> str:
    if not success:
        return message or "쿠팡 로그인에 실패했습니다."
    if "이미" in message:
        return "이미 쿠팡 로그인 상태예요.\n\n주문 내역이나 장바구니를 바로 확인할 수 있어요."
    return "쿠팡 로그인이 완료됐어요.\n\n주문 내역이나 장바구니를 바로 확인할 수 있어요."


def _parse_direct_cart_quantity_update(
    message: str,
) -> dict[str, int | str] | None:
    if "수량" not in message or ("장바구니" not in message and "개로" not in message):
        return None

    for pattern in QUANTITY_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue
        quantity = int(match.group("quantity"))
        index = match.groupdict().get("index")
        name = (match.groupdict().get("name") or "").strip()
        if index:
            return {"quantity": quantity, "item_index": int(index)}
        if name:
            cleaned_name = re.sub(r"^(장바구니|현재|그)\s*", "", name).strip()
            if cleaned_name:
                return {"quantity": quantity, "product_name": cleaned_name}
    return None


def _extract_text_payload(result: object) -> str:
    if isinstance(result, list):
        texts = [item.get("text", "") for item in result if isinstance(item, dict)]
        return "\n".join(text for text in texts if text)
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False)


def _parse_tool_result(result: object) -> dict[str, object]:
    text = _extract_text_payload(result).strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"message": text}


def _format_order_date(value: object) -> str:
    try:
        timestamp = int(value)
        if timestamp > 10_000_000_000:
            timestamp //= 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y.%m.%d")
    except Exception:
        return "-"


def _map_order_status(invoice_status: str) -> str:
    normalized = (invoice_status or "").strip().lower()
    if normalized in {"final_delivery", "delivered", "delivery_completed", "delivered_to_destination"}:
        return "배송완료"
    if normalized in {"instruct"}:
        return "상품준비중"
    if normalized in {"accept"}:
        return "주문접수"
    if normalized in {"non_tracking"}:
        return "배송조회불가"
    if any(token in normalized for token in ("delivery", "shipping", "in_transit", "배송중")):
        return "배송중"
    if any(token in normalized for token in ("cancel", "취소")):
        return "취소"
    return "주문확인"


def _fallback_display_status(invoice_status: str) -> str | None:
    normalized = (invoice_status or "").strip().lower()
    if normalized in {"final_delivery", "delivered", "delivery_completed", "delivered_to_destination"}:
        return "배송완료"
    if any(token in normalized for token in ("cancel", "취소")):
        return "주문 취소"
    return None


def _format_price_text(value: object) -> str:
    try:
        return f"{int(value):,}원"
    except Exception:
        return "-"


def _group_orders(payload: dict[str, object]) -> OrdersResponse:
    inner = (payload.get("payload") or {}) if isinstance(payload, dict) else {}
    orders = inner.get("orders") or []
    meta = inner.get("meta") or {}
    groups: list[OrderGroupResponse] = []
    years: set[str] = set()

    for order in orders if isinstance(orders, list) else []:
        if not isinstance(order, dict):
            continue
        ordered_at = int(order.get("orderedAt") or 0)
        date = _format_order_date(ordered_at)
        year = date[:4]
        years.add(year)
        delivery_groups = order.get("deliveryGroupList") or []

        for group_index, raw_group in enumerate(delivery_groups if isinstance(delivery_groups, list) else []):
            if not isinstance(raw_group, dict):
                continue
            status = _map_order_status(str(raw_group.get("invoiceStatus") or ""))
            raw_status = str(raw_group.get("invoiceStatus") or "")
            display_status = (
                str(raw_group.get("displayStatus") or "").strip()
                or _fallback_display_status(raw_status)
            )
            invoice_number = str(raw_group.get("invoiceNumber") or "") or None
            delivery_message = None
            pdd_message = raw_group.get("pddMessage")
            if isinstance(pdd_message, dict):
                raw_message = pdd_message.get("message")
                delivery_message = str(raw_message) if raw_message else None

            items: list[OrderProductResponse] = []
            for raw_product in raw_group.get("productList", []) if isinstance(raw_group.get("productList"), list) else []:
                if not isinstance(raw_product, dict):
                    continue
                items.append(
                    OrderProductResponse(
                        product=str(
                            raw_product.get("productName")
                            or raw_product.get("vendorItemName")
                            or "-"
                        ),
                        price=_format_price_text(
                            raw_product.get("combinedUnitPrice")
                            or raw_product.get("discountedUnitPrice")
                            or raw_product.get("unitPrice")
                        ),
                        quantity=int(raw_product.get("quantity") or 0),
                        link=str(raw_product.get("productUrl") or "") or None,
                        image=str(raw_product.get("imagePath") or "") or None,
                    )
                )

            groups.append(
                OrderGroupResponse(
                    id=f"{order.get('orderId')}-{group_index}",
                    order_id=str(order.get("orderId") or "-"),
                    shipment_box_id=str(raw_group.get("shipmentBoxId") or "") or None,
                    status=status,
                    raw_status=raw_status,
                    display_status=display_status,
                    invoice_number=invoice_number,
                    delivery_message=delivery_message,
                    has_track_action=bool(raw_group.get("hasTrackAction", False)),
                    has_exchange_return_action=bool(raw_group.get("hasExchangeReturnAction", False)),
                    has_write_review_action=bool(raw_group.get("hasWriteReviewAction", False)),
                    date=date,
                    ordered_at=ordered_at,
                    year=year,
                    items=items,
                )
            )

    collected_at = None
    if isinstance(meta, dict):
        raw = meta.get("collectedAt")
        collected_at = str(raw) if raw else None

    return OrdersResponse(
        total=len(groups),
        collected_at=collected_at,
        years=sorted(years, reverse=True),
        groups=groups,
    )


async def _try_direct_cart_quantity_update(
    websocket: WebSocket,
    tools: dict[str, object],
    message: str,
) -> bool:
    parsed = _parse_direct_cart_quantity_update(message)
    if not parsed:
        return False

    tool = tools.get("cart_update_quantity_smart")
    if tool is None:
        return False

    args = {"provider": "coupang", **parsed}
    await websocket.send_json({"type": "tool", "name": "cart_update_quantity_smart", "args": args})
    result = _parse_tool_result(await tool.ainvoke(args))
    await websocket.send_json(
        {
            "type": "token",
            "content": str(result.get("message") or "장바구니 수량 변경을 처리했습니다."),
        }
    )
    await websocket.send_json({"type": "done"})
    return True


async def _try_direct_login(
    websocket: WebSocket,
    tools: dict[str, object],
    message: str,
) -> bool:
    if not _looks_like_login_request(message):
        return False

    tool = tools.get("login")
    if tool is None:
        return False

    args = {"provider": "coupang"}
    await websocket.send_json({"type": "tool", "name": "login", "args": args})
    result = _parse_tool_result(await tool.ainvoke(args))
    await websocket.send_json(
        {
            "type": "token",
            "content": _format_login_chat_message(
                str(result.get("message") or ""),
                bool(result.get("success", False)),
            ),
        }
    )
    await websocket.send_json({"type": "done"})
    return True


@router.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@router.get("/api/tools", response_model=ToolsResponse)
async def list_tools() -> ToolsResponse:
    """List MCP tools exposed to the agent. Works without an LLM configured."""

    tools = await load_tools()
    return ToolsResponse(
        model_configured=is_model_configured(),
        tools=[ToolInfo(name=t.name, description=t.description or "") for t in tools],
    )


@router.get("/api/memory/{session_id}", response_model=MemorySummaryResponse)
async def get_memory(session_id: str) -> MemorySummaryResponse:
    memory = memory_store.get(session_id)
    return MemorySummaryResponse(
        session_id=memory.session_id,
        preferred_categories=memory.preferred_categories,
        avoided_keywords=memory.avoided_keywords,
        recent_queries=memory.recent_queries[-8:],
        recent_recommendations=memory.recent_recommendations[:5],
        price_preference=memory.price_preference,
        delivery_preference=memory.delivery_preference,
        last_intent=memory.last_intent,
    )


@router.get("/api/orders", response_model=OrdersResponse)
async def get_orders(refresh: bool = False) -> OrdersResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("order_list")
    if tool is None:
        return OrdersResponse(total=0, years=[], groups=[])
    payload = _parse_tool_result(
        await tool.ainvoke(
            {"provider": "coupang", "refresh": refresh, "failed_only": False}
        )
    )
    return _group_orders(payload)


@router.get(
    "/api/providers/{provider}/login-status",
    response_model=ProviderLoginStatusResponse,
)
async def get_provider_login_status(provider: str) -> ProviderLoginStatusResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("login_status")
    if tool is None:
        return ProviderLoginStatusResponse(
            provider=provider,
            logged_in=False,
            message="login_status 도구를 찾을 수 없습니다.",
        )

    payload = _parse_tool_result(await tool.ainvoke({"provider": provider}))
    return ProviderLoginStatusResponse(
        provider=str(payload.get("provider") or provider),
        logged_in=bool(payload.get("logged_in", False)),
        message=str(payload.get("message") or ""),
    )


@router.post("/api/providers/{provider}/login", response_model=ProviderLoginResponse)
async def login_provider(provider: str) -> ProviderLoginResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("login")
    if tool is None:
        return ProviderLoginResponse(
            provider=provider,
            success=False,
            message="login 도구를 찾을 수 없습니다.",
        )

    payload = _parse_tool_result(await tool.ainvoke({"provider": provider}))
    return ProviderLoginResponse(
        provider=str(payload.get("provider") or provider),
        success=bool(payload.get("success", False)),
        message=str(payload.get("message") or ""),
    )


@router.get("/api/cart", response_model=CartListResponse)
async def get_cart(provider: str = "coupang", refresh: bool = False) -> CartListResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("cart_list")
    if tool is None:
        return CartListResponse(
            provider=provider,
            success=False,
            message="cart_list 도구를 찾을 수 없습니다.",
        )

    payload = _parse_tool_result(
        await tool.ainvoke({"provider": provider, "refresh": refresh})
    )
    items = payload.get("items") if isinstance(payload, dict) else []
    return CartListResponse(
        provider=str(payload.get("provider") or provider),
        success=bool(payload.get("success", False)),
        message=str(payload.get("message") or ""),
        items=[
            CartItemResponse(
                index=int(item.get("index") or 0),
                product_name=str(item.get("product_name") or ""),
                option_text=str(item.get("option_text") or ""),
                quantity=int(item.get("quantity") or 0),
                unit_price=str(item.get("unit_price") or ""),
                total_price=str(item.get("total_price") or ""),
                product_id=str(item.get("product_id") or ""),
                vendor_item_id=str(item.get("vendor_item_id") or ""),
                item_id=str(item.get("item_id") or ""),
                delivery_text=str(item.get("delivery_text") or ""),
            )
            for item in items
            if isinstance(item, dict)
        ],
    )


def _cart_mutation_response(
    payload: dict[str, object],
    provider: str,
) -> CartMutationResponse:
    quantity = payload.get("quantity")
    return CartMutationResponse(
        provider=str(payload.get("provider") or provider),
        success=bool(payload.get("success", False)),
        message=str(payload.get("message") or ""),
        deleted_count=int(payload.get("deleted_count") or 0),
        quantity=int(quantity) if quantity is not None else None,
        product_id=str(payload.get("product_id") or ""),
        vendor_item_id=str(payload.get("vendor_item_id") or ""),
        item_id=str(payload.get("item_id") or ""),
        notice=str(payload.get("notice") or ""),
    )


@router.patch("/api/cart/items/quantity", response_model=CartMutationResponse)
async def update_cart_quantity(body: CartQuantityUpdateBody) -> CartMutationResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("cart_update_quantity")
    if tool is None:
        return CartMutationResponse(
            provider=body.provider,
            success=False,
            message="cart_update_quantity 도구를 찾을 수 없습니다.",
            quantity=body.quantity,
        )

    payload = _parse_tool_result(
        await tool.ainvoke(
            {
                "provider": body.provider,
                "quantity": body.quantity,
                "product_id": body.product_id,
                "vendor_item_id": body.vendor_item_id,
                "item_id": body.item_id,
            }
        )
    )
    return _cart_mutation_response(payload, body.provider)


@router.delete("/api/cart/items", response_model=CartMutationResponse)
async def delete_cart_item(body: CartDeleteBody) -> CartMutationResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("cart_delete_item")
    if tool is None:
        return CartMutationResponse(
            provider=body.provider,
            success=False,
            message="cart_delete_item 도구를 찾을 수 없습니다.",
        )

    payload = _parse_tool_result(
        await tool.ainvoke(
            {
                "provider": body.provider,
                "product_id": body.product_id,
                "vendor_item_id": body.vendor_item_id,
                "item_id": body.item_id,
            }
        )
    )
    return _cart_mutation_response(payload, body.provider)


@router.delete("/api/cart/items/bulk", response_model=CartMutationResponse)
async def delete_cart_items(body: CartBulkDeleteBody) -> CartMutationResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("cart_delete_items")
    if tool is None:
        return CartMutationResponse(
            provider=body.provider,
            success=False,
            message="cart_delete_items 도구를 찾을 수 없습니다.",
        )

    payload = _parse_tool_result(
        await tool.ainvoke(
            {
                "provider": body.provider,
                "items": [
                    {
                        "product_id": item.product_id,
                        "vendor_item_id": item.vendor_item_id,
                        "item_id": item.item_id,
                    }
                    for item in body.items
                ],
            }
        )
    )
    return _cart_mutation_response(payload, body.provider)


@router.delete("/api/cart", response_model=CartMutationResponse)
async def clear_cart(provider: str = "coupang") -> CartMutationResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("cart_clear")
    if tool is None:
        return CartMutationResponse(
            provider=provider,
            success=False,
            message="cart_clear 도구를 찾을 수 없습니다.",
        )

    payload = _parse_tool_result(await tool.ainvoke({"provider": provider}))
    return _cart_mutation_response(payload, provider)


@router.get(
    "/api/orders/{order_id}/shipments/{shipment_box_id}/tracking",
    response_model=DeliveryTrackingResponse,
)
async def get_order_delivery_tracking(
    order_id: str,
    shipment_box_id: str,
    provider: str = "coupang",
) -> DeliveryTrackingResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("order_delivery_tracking")
    if tool is None:
        return DeliveryTrackingResponse(
            provider=provider,
            order_id=order_id,
            shipment_box_id=shipment_box_id,
        )

    payload = _parse_tool_result(
        await tool.ainvoke(
            {
                "provider": provider,
                "order_id": int(order_id),
                "shipment_box_id": shipment_box_id,
            }
        )
    )
    inner = (payload.get("payload") or {}) if isinstance(payload, dict) else {}
    events = inner.get("events") if isinstance(inner, dict) else []
    return DeliveryTrackingResponse(
        provider=str(inner.get("provider") or provider),
        order_id=str(inner.get("orderId") or order_id),
        shipment_box_id=str(inner.get("shipmentBoxId") or shipment_box_id),
        invoice_number=str(inner.get("invoiceNumber") or "") or None,
        display_status=str(inner.get("displayStatus") or "") or None,
        courier_name=str(inner.get("courierName") or "") or None,
        tracking_number=str(inner.get("trackingNumber") or "") or None,
        summary=str(inner.get("summary") or "") or None,
        raw_lines=[
            str(line)
            for line in (inner.get("rawLines") or [])
            if isinstance(line, str) and line.strip()
        ],
        collected_at=str(inner.get("collectedAt") or "") or None,
        events=[
            DeliveryTrackingEventResponse(
                time=str(event.get("time") or "") or None,
                status=str(event.get("status") or "-"),
                description=str(event.get("description") or "") or None,
                location=str(event.get("location") or "") or None,
            )
            for event in events
            if isinstance(event, dict)
        ],
    )


def _reviewable_response(payload: dict[str, object], provider: str) -> ReviewableListResponse:
    raw_items = payload.get("items") if isinstance(payload, dict) else []
    items = raw_items if isinstance(raw_items, list) else []
    return ReviewableListResponse(
        provider=str(payload.get("provider") or provider),
        success=bool(payload.get("success", False)),
        message=str(payload.get("message") or ""),
        items=[
            ReviewableItemResponse(
                index=int(item.get("index") or 0),
                product_id=str(item.get("product_id") or ""),
                product_name=str(item.get("product_name") or ""),
                delivery_date=str(item.get("delivery_date") or ""),
                completed_order_vendor_item_id=str(item.get("completed_order_vendor_item_id") or ""),
                vendor_item_id=str(item.get("vendor_item_id") or ""),
                review_url=str(item.get("review_url") or ""),
            )
            for item in items
            if isinstance(item, dict)
        ],
    )


def _editable_reviews_response(
    payload: dict[str, object],
    provider: str,
) -> EditableReviewListResponse:
    raw_items = payload.get("items") if isinstance(payload, dict) else []
    items = raw_items if isinstance(raw_items, list) else []
    return EditableReviewListResponse(
        provider=str(payload.get("provider") or provider),
        success=bool(payload.get("success", False)),
        message=str(payload.get("message") or ""),
        items=[
            EditableReviewItemResponse(
                index=int(item.get("index") or 0),
                review_id=str(item.get("review_id") or ""),
                product_id=str(item.get("product_id") or ""),
                order_id=str(item.get("order_id") or ""),
                product_name=str(item.get("product_name") or ""),
                rating=int(item.get("rating") or 0),
                review_text=str(item.get("review_text") or ""),
                modify_url=str(item.get("modify_url") or ""),
            )
            for item in items
            if isinstance(item, dict)
        ],
    )


@router.get("/api/reviews", response_model=ReviewListResponse)
async def get_reviews(provider: str = "coupang") -> ReviewListResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("review_list")
    if tool is None:
        empty_reviewable = ReviewableListResponse(
            provider=provider,
            success=False,
            message="review_list 도구를 찾을 수 없습니다.",
        )
        empty_editable = EditableReviewListResponse(
            provider=provider,
            success=False,
            message="review_list 도구를 찾을 수 없습니다.",
        )
        return ReviewListResponse(
            provider=provider,
            success=False,
            message="review_list 도구를 찾을 수 없습니다.",
            reviewable=empty_reviewable,
            editable=empty_editable,
        )

    payload = _parse_tool_result(await tool.ainvoke({"provider": provider}))
    reviewable_payload = payload.get("reviewable") if isinstance(payload, dict) else {}
    editable_payload = payload.get("editable") if isinstance(payload, dict) else {}
    reviewable = _reviewable_response(
        reviewable_payload if isinstance(reviewable_payload, dict) else {},
        provider,
    )
    editable = _editable_reviews_response(
        editable_payload if isinstance(editable_payload, dict) else {},
        provider,
    )
    return ReviewListResponse(
        provider=str(payload.get("provider") or provider),
        success=bool(payload.get("success", reviewable.success and editable.success)),
        message=str(payload.get("message") or ""),
        reviewable=reviewable,
        editable=editable,
    )


@router.get("/api/reviews/reviewable", response_model=ReviewableListResponse)
async def get_reviewable_items(provider: str = "coupang") -> ReviewableListResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("review_list_reviewable")
    if tool is None:
        return ReviewableListResponse(
            provider=provider,
            success=False,
            message="review_list_reviewable 도구를 찾을 수 없습니다.",
        )

    payload = _parse_tool_result(await tool.ainvoke({"provider": provider}))
    items = payload.get("items") if isinstance(payload, dict) else []
    return ReviewableListResponse(
        provider=str(payload.get("provider") or provider),
        success=bool(payload.get("success", False)),
        message=str(payload.get("message") or ""),
        items=[
            ReviewableItemResponse(
                index=int(item.get("index") or 0),
                product_id=str(item.get("product_id") or ""),
                product_name=str(item.get("product_name") or ""),
                delivery_date=str(item.get("delivery_date") or ""),
                completed_order_vendor_item_id=str(item.get("completed_order_vendor_item_id") or ""),
                vendor_item_id=str(item.get("vendor_item_id") or ""),
                review_url=str(item.get("review_url") or ""),
            )
            for item in items
            if isinstance(item, dict)
        ],
    )


@router.get("/api/reviews/editable", response_model=EditableReviewListResponse)
async def get_editable_reviews(provider: str = "coupang") -> EditableReviewListResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("review_list_editable")
    if tool is None:
        return EditableReviewListResponse(
            provider=provider,
            success=False,
            message="review_list_editable 도구를 찾을 수 없습니다.",
        )

    payload = _parse_tool_result(await tool.ainvoke({"provider": provider}))
    items = payload.get("items") if isinstance(payload, dict) else []
    return EditableReviewListResponse(
        provider=str(payload.get("provider") or provider),
        success=bool(payload.get("success", False)),
        message=str(payload.get("message") or ""),
        items=[
            EditableReviewItemResponse(
                index=int(item.get("index") or 0),
                review_id=str(item.get("review_id") or ""),
                product_id=str(item.get("product_id") or ""),
                order_id=str(item.get("order_id") or ""),
                product_name=str(item.get("product_name") or ""),
                rating=int(item.get("rating") or 0),
                review_text=str(item.get("review_text") or ""),
                modify_url=str(item.get("modify_url") or ""),
            )
            for item in items
            if isinstance(item, dict)
        ],
    )


@router.post("/api/reviews", response_model=ReviewMutationResponse)
async def create_review(body: ReviewUploadRequestBody) -> ReviewMutationResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("review_upload")
    if tool is None:
        return ReviewMutationResponse(
            provider=body.provider,
            success=False,
            message="review_upload 도구를 찾을 수 없습니다.",
        )

    payload = _parse_tool_result(
        await tool.ainvoke(
            {
                "provider": body.provider,
                "order_id": body.order_id,
                "product_id": body.product_id,
                "rating": body.rating,
                "text": body.text,
                "review_url": body.review_url,
            }
        )
    )
    return ReviewMutationResponse(
        provider=str(payload.get("provider") or body.provider),
        success=bool(payload.get("success", False)),
        message=str(payload.get("message") or ""),
        product_id=str(payload.get("product_id") or body.product_id) or None,
        order_id=str(payload.get("order_id") or body.order_id) or None,
    )


@router.patch("/api/reviews/{review_id}", response_model=ReviewMutationResponse)
async def update_review(review_id: str, body: ReviewEditRequestBody) -> ReviewMutationResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("review_edit")
    if tool is None:
        return ReviewMutationResponse(
            provider=body.provider,
            success=False,
            message="review_edit 도구를 찾을 수 없습니다.",
            review_id=review_id,
        )

    payload = _parse_tool_result(
        await tool.ainvoke(
            {
                "provider": body.provider,
                "order_id": body.order_id,
                "product_id": body.product_id,
                "review_id": review_id,
                "rating": body.rating,
                "text": body.text,
            }
        )
    )
    return ReviewMutationResponse(
        provider=str(payload.get("provider") or body.provider),
        success=bool(payload.get("success", False)),
        message=str(payload.get("message") or ""),
        review_id=str(payload.get("review_id") or review_id) or None,
        product_id=str(payload.get("product_id") or body.product_id) or None,
        order_id=str(payload.get("order_id") or body.order_id) or None,
    )


@router.delete("/api/reviews/{review_id}", response_model=ReviewMutationResponse)
async def remove_review(review_id: str, body: ReviewDeleteRequestBody) -> ReviewMutationResponse:
    tools = await load_tools()
    tool_map = {tool.name: tool for tool in tools}
    tool = tool_map.get("review_delete")
    if tool is None:
        return ReviewMutationResponse(
            provider=body.provider,
            success=False,
            message="review_delete 도구를 찾을 수 없습니다.",
            review_id=review_id,
        )

    payload = _parse_tool_result(
        await tool.ainvoke(
            {
                "provider": body.provider,
                "review_id": review_id,
                "product_id": body.product_id,
                "order_id": body.order_id,
            }
        )
    )
    return ReviewMutationResponse(
        provider=str(payload.get("provider") or body.provider),
        success=bool(payload.get("success", False)),
        message=str(payload.get("message") or ""),
        review_id=str(payload.get("review_id") or review_id) or None,
        product_id=str(payload.get("product_id") or body.product_id) or None,
        order_id=str(payload.get("order_id") or body.order_id) or None,
    )


@router.websocket("/ws/chat")
async def chat(websocket: WebSocket) -> None:
    """Stream an agent chat turn to the frontend.

    Message protocol (JSON):
      - client -> server: {"message": "..."} or {"messages": [...]}
      - server -> client: {"type": "token"|"tool"|"done"|"error", ...}
    """

    await websocket.accept()

    try:
        while True:
            payload = await websocket.receive_json()
            request = ChatRequest.model_validate(payload)
            lc_messages = request.to_lc_messages()
            if not lc_messages:
                await websocket.send_json({"type": "error", "message": "빈 메시지입니다."})
                continue

            session_id = request.session_id or "anonymous"
            user_messages = [message.content for message in request.messages or [] if message.role == "user"]
            memory = memory_store.ingest_history(session_id, user_messages)
            latest_user_message = user_messages[-1] if user_messages else request.message or ""

            try:
                tools = await load_tools()
                tool_map = {tool.name: tool for tool in tools}

                if await _try_direct_cart_quantity_update(
                    websocket,
                    tool_map,
                    latest_user_message,
                ):
                    continue

                if await _try_direct_login(
                    websocket,
                    tool_map,
                    latest_user_message,
                ):
                    continue

                if _looks_like_recommendation_request(latest_user_message):
                    response, recommended_names = await run_recommendation_graph(
                        user_message=latest_user_message,
                        memory=memory,
                        tools=tool_map,
                        on_tool=lambda name, args: websocket.send_json(
                            {"type": "tool", "name": name, "args": args}
                        ),
                    )
                    await websocket.send_json({"type": "token", "content": response})
                    memory_store.note_recommendations(session_id, recommended_names)
                    await websocket.send_json({"type": "done"})
                    continue

                try:
                    agent = await build_agent(extra_system_prompt=memory.to_prompt_block())
                except ModelNotConfiguredError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    await websocket.close()
                    return

                async for chunk in agent.astream(
                    {"messages": lc_messages},
                    stream_mode=["messages", "updates"],
                    version="v2",
                ):
                    await _forward_chunk(websocket, chunk)
                await websocket.send_json({"type": "done"})
            except WebSocketDisconnect:
                raise
            except Exception as exc:
                await websocket.send_json(
                    {"type": "error", "message": f"실행 중 오류가 발생했습니다: {exc}"}
                )
    except WebSocketDisconnect:
        return


async def _forward_chunk(websocket: WebSocket, chunk: dict) -> None:
    kind = chunk.get("type")

    if kind == "messages":
        message_chunk, _metadata = chunk["data"]
        if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
            await websocket.send_json({"type": "token", "content": message_chunk.content})
        return

    if kind == "updates":
        for node_name, update in chunk["data"].items():
            messages = (update or {}).get("messages", [])
            for message in messages:
                tool_calls = getattr(message, "tool_calls", None)
                for call in tool_calls or []:
                    await websocket.send_json(
                        {"type": "tool", "name": call.get("name"), "args": call.get("args")}
                    )
        return
