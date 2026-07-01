from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from k_commerce_cli.base import Terminal
from k_commerce_cli.commands.cart.interactive import (
    _cart_selection_prompt,
    format_cart_detail,
    run_cart_list_browse,
)
from k_commerce_cli.prompts import QuestionaryPrompts
from k_commerce_cli.services.types import CartItem


def _cart_item() -> CartItem:
    return CartItem(
        index=1,
        product_name="루미즈 초경량 자외선차단 접이식 3단 양산 우산",
        option_text="베이지",
        quantity=2,
        unit_price="5,900원",
        total_price="11,800원",
        product_id="9459571406",
        vendor_item_id="95103608027",
        item_id="44245695211",
        delivery_text="내일(화) 도착 보장",
    )


def test_cart_selection_prompt_mentions_detail_for_browse_mode() -> None:
    browse_prompt = _cart_selection_prompt("상세 보기할 상품을 고르세요", 3, browse=True)
    action_prompt = _cart_selection_prompt("수량을 수정할 상품을 선택하세요", 3)

    assert "Enter로 상세 보기" in browse_prompt
    assert "Enter 선택" in action_prompt
    assert "Enter로 상세 보기" not in action_prompt


def test_format_cart_detail_shows_full_fields() -> None:
    output = format_cart_detail(_cart_item())

    assert "No: 1" in output
    assert "루미즈 초경량" in output
    assert "베이지" in output
    assert "수량: 2개" in output
    assert "95103608027" in output
    assert "내일(화) 도착 보장" in output


@pytest.mark.anyio
async def test_run_cart_list_browse_shows_detail_then_exits() -> None:
    terminal = Mock(spec=Terminal)
    terminal.echo = Mock()
    prompts = Mock(spec=QuestionaryPrompts)

    with (
        patch(
            "k_commerce_cli.commands.cart.interactive.prompt_cart_item",
            new=AsyncMock(return_value=_cart_item()),
        ),
        patch(
            "k_commerce_cli.commands.cart.interactive.prompt_list_detail_action",
            new=AsyncMock(return_value="exit"),
        ),
    ):
        await run_cart_list_browse(
            terminal,
            prompts,
            (_cart_item(),),
            exit_message="종료",
        )

    terminal.echo.assert_any_call(format_cart_detail(_cart_item()))
    terminal.echo.assert_any_call("종료")


@pytest.mark.anyio
async def test_run_cart_list_browse_returns_to_list_on_back() -> None:
    terminal = Mock(spec=Terminal)
    terminal.echo = Mock()
    prompts = Mock(spec=QuestionaryPrompts)
    item = _cart_item()

    with (
        patch(
            "k_commerce_cli.commands.cart.interactive.prompt_cart_item",
            new=AsyncMock(side_effect=[item, None]),
        ),
        patch(
            "k_commerce_cli.commands.cart.interactive.prompt_list_detail_action",
            new=AsyncMock(return_value="back"),
        ),
    ):
        await run_cart_list_browse(
            terminal,
            prompts,
            (item,),
            exit_message="종료",
        )

    assert terminal.echo.call_args_list[-1] == (("종료",),)
