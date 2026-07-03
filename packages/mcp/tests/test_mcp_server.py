from unittest.mock import AsyncMock, patch

import pytest
from k_commerce_cli.services.types import (
    CartDeleteRequest,
    CartDeleteResult,
    CartItem,
    CartQuantityUpdateResult,
    ListCartResult,
    LoginResult,
    LogoutResult,
    StatusResult,
)
from k_commerce_mcp import server


@pytest.mark.anyio
async def test_create_mcp_server_registers_login_and_login_status_tools() -> None:
    mcp_server = server.create_mcp_server()

    tools = await mcp_server.list_tools()
    tool_names = {tool.name for tool in tools}

    assert "get_providers" in tool_names
    assert "login" in tool_names
    assert "login_status" in tool_names
    assert "logout" in tool_names
    assert "order_list" in tool_names
    assert "cart_list" in tool_names
    assert "cart_update_quantity" in tool_names
    assert "cart_delete_item" in tool_names
    assert "cart_delete_items" in tool_names
    assert "cart_clear" in tool_names


@pytest.mark.anyio
async def test_login_tool_has_clear_description() -> None:
    mcp_server = server.create_mcp_server()

    tools = await mcp_server.list_tools()
    login_tool = next(tool for tool in tools if tool.name == "login")

    assert "Coupang" in login_tool.description


@pytest.mark.anyio
async def test_login_status_tool_has_clear_description() -> None:
    mcp_server = server.create_mcp_server()

    tools = await mcp_server.list_tools()
    login_status_tool = next(tool for tool in tools if tool.name == "login_status")

    assert "status" in login_status_tool.description.lower()
    assert "logged in" in login_status_tool.description.lower()


@pytest.mark.anyio
async def test_login_tool_returns_provider_login_result_for_coupang_provider() -> None:
    expected = LoginResult(
        provider="coupang",
        success=True,
        message="쿠팡 로그인 성공",
    )
    mocked_provider = type(
        "MockProvider",
        (),
        {"login": AsyncMock(return_value=expected)},
    )()

    with patch("k_commerce_mcp.tools.login.get_provider", return_value=mocked_provider) as get_provider:
        result = await server.login(provider="coupang")

    assert result == expected
    get_provider.assert_called_once_with("coupang")
    mocked_provider.login.assert_awaited_once_with()


@pytest.mark.anyio
async def test_login_status_tool_returns_provider_status_result_for_coupang_provider() -> None:
    expected = StatusResult(
        provider="coupang",
        logged_in=True,
        message="쿠팡 로그인 상태입니다",
    )
    mocked_provider = type(
        "MockProvider",
        (),
        {"status": AsyncMock(return_value=expected)},
    )()

    with patch(
        "k_commerce_mcp.tools.login_status.get_provider",
        return_value=mocked_provider,
    ) as get_provider:
        result = await server.login_status(provider="coupang")

    assert result == expected
    get_provider.assert_called_once_with("coupang")
    mocked_provider.status.assert_awaited_once_with()


@pytest.mark.anyio
async def test_logout_tool_returns_provider_logout_result_for_coupang_provider() -> None:
    expected = LogoutResult(
        provider="coupang",
        success=True,
        message="쿠팡 로그아웃 완료",
    )
    mocked_provider = type(
        "MockProvider",
        (),
        {"logout": AsyncMock(return_value=expected)},
    )()

    with patch("k_commerce_mcp.tools.logout.get_provider", return_value=mocked_provider) as get_provider:
        result = await server.logout(provider="coupang")

    assert result == expected
    get_provider.assert_called_once_with("coupang")
    mocked_provider.logout.assert_awaited_once_with()


@pytest.mark.anyio
async def test_order_list_tool_delegates_to_provider() -> None:
    expected = object()
    mocked_provider = type(
        "MockProvider",
        (),
        {"list_orders": AsyncMock(return_value=expected)},
    )()

    with patch(
        "k_commerce_mcp.tools.order.get_provider",
        return_value=mocked_provider,
    ) as get_provider:
        result = await server.order_list(
            provider="coupang",
            refresh=True,
            failed_only=False,
        )

    assert result is expected
    get_provider.assert_called_once_with("coupang")
    mocked_provider.list_orders.assert_awaited_once_with(
        refresh=True,
        failed_only=False,
    )


@pytest.mark.anyio
async def test_cart_list_tool_returns_provider_cart_list_result() -> None:
    expected = ListCartResult(
        provider="coupang",
        success=True,
        message="장바구니 1건",
        items=(
            CartItem(
                index=1,
                product_name="테스트 상품",
                option_text="옵션",
                quantity=2,
                unit_price="10,000원",
                total_price="20,000원",
                product_id="p1",
                vendor_item_id="v1",
                item_id="i1",
            ),
        ),
    )
    mocked_provider = type(
        "MockProvider",
        (),
        {"list_cart": AsyncMock(return_value=expected)},
    )()

    with patch("k_commerce_mcp.tools.cart.get_provider", return_value=mocked_provider) as get_provider:
        result = await server.cart_list(provider="coupang")

    assert result == expected
    get_provider.assert_called_once_with("coupang")
    mocked_provider.list_cart.assert_awaited_once_with()


@pytest.mark.anyio
async def test_cart_update_quantity_tool_delegates_to_provider() -> None:
    expected = CartQuantityUpdateResult(
        provider="coupang",
        success=True,
        message="수량 변경 완료",
        quantity=3,
        product_id="p1",
        vendor_item_id="v1",
        item_id="i1",
    )
    mocked_provider = type(
        "MockProvider",
        (),
        {"update_cart_quantity": AsyncMock(return_value=expected)},
    )()

    with patch(
        "k_commerce_mcp.tools.cart.get_provider",
        return_value=mocked_provider,
    ) as get_provider:
        result = await server.cart_update_quantity(
            provider="coupang",
            quantity=3,
            product_id="p1",
            vendor_item_id="v1",
            item_id="i1",
        )

    assert result == expected
    get_provider.assert_called_once_with("coupang")
    request = mocked_provider.update_cart_quantity.await_args.args[0]
    assert request.quantity == 3
    assert request.product_id == "p1"
    assert request.vendor_item_id == "v1"
    assert request.item_id == "i1"


@pytest.mark.anyio
async def test_cart_delete_item_tool_delegates_to_provider() -> None:
    expected = CartDeleteResult(
        provider="coupang",
        success=True,
        message="삭제 완료",
        deleted_count=1,
    )
    mocked_provider = type(
        "MockProvider",
        (),
        {"delete_cart_item": AsyncMock(return_value=expected)},
    )()

    with patch(
        "k_commerce_mcp.tools.cart.get_provider",
        return_value=mocked_provider,
    ) as get_provider:
        result = await server.cart_delete_item(
            provider="coupang",
            product_id="p1",
            vendor_item_id="v1",
            item_id="i1",
        )

    assert result == expected
    get_provider.assert_called_once_with("coupang")
    request = mocked_provider.delete_cart_item.await_args.args[0]
    assert request.product_id == "p1"
    assert request.vendor_item_id == "v1"
    assert request.item_id == "i1"


@pytest.mark.anyio
async def test_cart_delete_items_tool_delegates_to_provider() -> None:
    expected = CartDeleteResult(
        provider="coupang",
        success=True,
        message="2건 삭제 완료",
        deleted_count=2,
    )
    mocked_provider = type(
        "MockProvider",
        (),
        {"delete_cart_items": AsyncMock(return_value=expected)},
    )()
    items = (
        CartDeleteRequest(product_id="p1", vendor_item_id="v1", item_id="i1"),
        CartDeleteRequest(product_id="p2", vendor_item_id="v2", item_id="i2"),
    )

    with patch(
        "k_commerce_mcp.tools.cart.get_provider",
        return_value=mocked_provider,
    ) as get_provider:
        result = await server.cart_delete_items(provider="coupang", items=list(items))

    assert result == expected
    get_provider.assert_called_once_with("coupang")
    mocked_provider.delete_cart_items.assert_awaited_once_with(items)


@pytest.mark.anyio
async def test_cart_clear_tool_delegates_to_provider() -> None:
    expected = CartDeleteResult(
        provider="coupang",
        success=True,
        message="장바구니 비우기 완료",
        deleted_count=5,
    )
    mocked_provider = type(
        "MockProvider",
        (),
        {"clear_cart": AsyncMock(return_value=expected)},
    )()

    with patch("k_commerce_mcp.tools.cart.get_provider", return_value=mocked_provider) as get_provider:
        result = await server.cart_clear(provider="coupang")

    assert result == expected
    get_provider.assert_called_once_with("coupang")
    mocked_provider.clear_cart.assert_awaited_once_with()


def test_main_runs_mcp_server_over_stdio() -> None:
    with patch("k_commerce_mcp.server.create_mcp_server") as create_mcp_server:
        mcp_server = create_mcp_server.return_value

        server.main()

    create_mcp_server.assert_called_once_with()
    mcp_server.run.assert_called_once_with(transport="stdio")
