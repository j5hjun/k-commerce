from unittest.mock import AsyncMock, Mock

import pytest

from k_commerce_cli.commands.cart.interactive import (
    CART_LIST_HEADER,
    _cart_list_choice_label,
    prompt_cart_items,
    prompt_cart_items_empty_action,
    prompt_clear_cart_action,
)
from k_commerce_cli.services.types import CartItem


def test_cart_list_choice_label_matches_table_columns() -> None:
    item = CartItem(
        index=3,
        product_name="하니모아 초경량 UV 자외선 차단 99.9% 고리형 5단 접이식 양산",
        option_text="블랙+하드케이스",
        quantity=2,
        unit_price="30,000원",
        total_price="60,000원",
        product_id="1",
        vendor_item_id="2",
        item_id="3",
    )

    label = _cart_list_choice_label(item)

    assert label.startswith("  3  ")
    assert "블랙+하드케이스" in label
    assert "60,000원" in label.rstrip()


@pytest.mark.anyio
async def test_prompt_cart_items_uses_table_choices_with_navigation() -> None:
    item = CartItem(
        index=1,
        product_name="테스트 상품",
        option_text="옵션",
        quantity=1,
        unit_price="1,000원",
        total_price="1,000원",
        product_id="1",
        vendor_item_id="2",
        item_id="3",
    )
    prompts = Mock()
    prompts.checkbox = AsyncMock(return_value=[item])

    result = await prompt_cart_items(prompts, (item,))

    assert result == (item,)
    message = prompts.checkbox.call_args.args[0]
    assert CART_LIST_HEADER in message
    assert "a 전체" in message
    assert "i 반전" in message
    choices = prompts.checkbox.call_args.kwargs.get("choices") or prompts.checkbox.call_args.args[1]
    assert choices[0].title == _cart_list_choice_label(item)
    assert [choice.title for choice in choices[-2:]] == ["뒤로가기", "나가기"]
    assert prompts.checkbox.call_args.kwargs["focus_submit_values"] is not None


@pytest.mark.anyio
async def test_prompt_cart_items_focus_submit_returns_back_without_secondary_menu() -> None:
    from k_commerce_cli.commands.cart.interactive import _BACK_TO_DELETE_MODE

    item = CartItem(
        index=1,
        product_name="테스트 상품",
        option_text="옵션",
        quantity=1,
        unit_price="1,000원",
        total_price="1,000원",
        product_id="1",
        vendor_item_id="2",
        item_id="3",
    )
    prompts = Mock()
    prompts.checkbox = AsyncMock(return_value=[_BACK_TO_DELETE_MODE])

    result = await prompt_cart_items(prompts, (item,))

    assert result == "back"
    prompts.select.assert_not_called()


@pytest.mark.anyio
async def test_prompt_cart_items_prefers_items_over_navigation() -> None:
    from k_commerce_cli.commands.cart.interactive import _BACK_TO_DELETE_MODE, _EXIT_CART_SELECTION

    item = CartItem(
        index=1,
        product_name="테스트 상품",
        option_text="옵션",
        quantity=1,
        unit_price="1,000원",
        total_price="1,000원",
        product_id="1",
        vendor_item_id="2",
        item_id="3",
    )
    prompts = Mock()
    prompts.checkbox = AsyncMock(
        return_value=[item, _BACK_TO_DELETE_MODE, _EXIT_CART_SELECTION]
    )

    result = await prompt_cart_items(prompts, (item,))

    assert result == (item,)


@pytest.mark.anyio
async def test_prompt_cart_items_empty_selection_offers_navigation() -> None:
    from k_commerce_cli.commands.cart.interactive import _BACK_TO_DELETE_MODE

    item = CartItem(
        index=1,
        product_name="테스트 상품",
        option_text="옵션",
        quantity=1,
        unit_price="1,000원",
        total_price="1,000원",
        product_id="1",
        vendor_item_id="2",
        item_id="3",
    )
    prompts = Mock()
    prompts.checkbox = AsyncMock(return_value=[])
    prompts.select = AsyncMock(return_value=_BACK_TO_DELETE_MODE)

    result = await prompt_cart_items(prompts, (item,))

    assert result == "back"
    prompts.select.assert_awaited_once()


@pytest.mark.anyio
async def test_prompt_cart_items_empty_action_includes_retry() -> None:
    from k_commerce_cli.commands.cart.interactive import _EMPTY_SELECTION_RETRY

    prompts = Mock()
    prompts.select = AsyncMock(return_value=_EMPTY_SELECTION_RETRY)

    result = await prompt_cart_items_empty_action(prompts)

    assert result == "retry"
    choices = prompts.select.call_args.kwargs.get("choices") or prompts.select.call_args.args[1]
    assert [choice.title for choice in choices] == ["다시 선택", "뒤로가기", "나가기"]


@pytest.mark.anyio
async def test_prompt_clear_cart_action_returns_selected_action() -> None:
    from k_commerce_cli.commands.cart.interactive import _CLEAR_CART_BACK

    prompts = Mock()
    prompts.select = AsyncMock(return_value=_CLEAR_CART_BACK)

    result = await prompt_clear_cart_action(prompts)

    assert result == "back"
    message = prompts.select.call_args.args[0]
    assert "다음 작업을 선택하세요" in message
    choices = prompts.select.call_args.kwargs.get("choices") or prompts.select.call_args.args[1]
    assert [choice.title for choice in choices] == [
        "목록보기",
        "전체 비우기",
        "뒤로가기",
        "나가기",
    ]


@pytest.mark.anyio
async def test_prompt_bulk_delete_confirmation_returns_confirm() -> None:
    from k_commerce_cli.commands.cart.interactive import (
        _BULK_DELETE_CONFIRM,
        prompt_bulk_delete_confirmation,
    )

    prompts = Mock()
    prompts.select = AsyncMock(return_value=_BULK_DELETE_CONFIRM)

    result = await prompt_bulk_delete_confirmation(prompts)

    assert result == "confirm"
    assert "정말 삭제하시겠습니까?" in prompts.select.call_args.args[0]


def test_format_selected_cart_delete_list_uses_delete_heading() -> None:
    from k_commerce_cli.commands.cart.interactive import format_selected_cart_delete_list

    item = CartItem(
        index=1,
        product_name="테스트 상품",
        option_text="옵션",
        quantity=1,
        unit_price="1,000원",
        total_price="1,000원",
        product_id="1",
        vendor_item_id="2",
        item_id="3",
    )

    formatted = format_selected_cart_delete_list((item,))

    assert formatted.startswith("삭제할 상품 (1건):")
    assert "테스트 상품" in formatted
