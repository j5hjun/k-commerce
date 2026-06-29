from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any, Protocol

import questionary


class Prompts(Protocol):
    async def select(self, message: str, choices: Sequence[Any]) -> Any: ...

    async def text(self, message: str) -> str: ...

    async def print_message(self, message: str, *, style: str = "fg:red") -> None: ...


class QuestionaryPrompts:
    async def select(self, message: str, choices: Sequence[Any]) -> Any:
        def _ask() -> Any:
            selection = questionary.select(
                message,
                choices=list(choices),
                use_indicator=True,
            ).ask()

            if selection is None:
                raise KeyboardInterrupt
            return selection

        return await asyncio.to_thread(_ask)

    async def text(self, message: str) -> str:
        def _ask() -> str:
            value = questionary.text(message).ask()

            if value is None:
                raise KeyboardInterrupt
            return value

        return await asyncio.to_thread(_ask)

    async def print_message(self, message: str, *, style: str = "fg:red") -> None:
        await asyncio.to_thread(lambda: questionary.print(message, style=style))
