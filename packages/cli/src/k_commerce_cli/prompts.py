import asyncio
from collections.abc import Sequence
from typing import Any, TypeVar

import questionary
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import Style
from questionary.constants import DEFAULT_QUESTION_PREFIX
from questionary.constants import DEFAULT_SELECTED_POINTER
from questionary.prompts import common
from questionary.prompts.common import Choice
from questionary.prompts.common import InquirerControl
from questionary.prompts.common import Separator
from questionary.question import Question
from questionary.styles import merge_styles_default

T = TypeVar("T")


def _ask_checkbox(
    message: str,
    choices: Sequence[Choice | str],
    *,
    focus_submit_values: frozenset[object] | None = None,
) -> list[Any]:
    ic = InquirerControl(
        list(choices),
        default=None,
        pointer=DEFAULT_SELECTED_POINTER,
        initial_choice=None,
        show_description=True,
    )

    def get_prompt_tokens() -> list[tuple[str, str]]:
        tokens: list[tuple[str, str]] = [
            ("class:qmark", DEFAULT_QUESTION_PREFIX),
            ("class:question", f" {message} "),
        ]
        if ic.is_answered:
            nbr_selected = len(ic.selected_options)
            if nbr_selected == 0:
                tokens.append(("class:answer", "done"))
            elif nbr_selected == 1:
                tokens.append(("class:answer", f"[{ic.get_selected_values()[0].title}]"))
            else:
                tokens.append(("class:answer", f"done ({nbr_selected} selections)"))
        return tokens

    def get_selected_values() -> list[Any]:
        return [choice.value for choice in ic.get_selected_values()]

    merged_style = merge_styles_default([Style([("bottom-toolbar", "noreverse")]), None])
    layout = common.create_inquirer_layout(ic, get_prompt_tokens)
    bindings = KeyBindings()

    @bindings.add(Keys.ControlQ, eager=True)
    @bindings.add(Keys.ControlC, eager=True)
    def abort(event):  # type: ignore[no-untyped-def]
        event.app.exit(exception=KeyboardInterrupt, style="class:aborting")

    @bindings.add(" ", eager=True)
    def toggle(_event):  # type: ignore[no-untyped-def]
        pointed_choice = ic.get_pointed_at().value
        if pointed_choice in ic.selected_options:
            ic.selected_options.remove(pointed_choice)
        else:
            ic.selected_options.append(pointed_choice)

    @bindings.add("i", eager=True)
    def invert(_event):  # type: ignore[no-untyped-def]
        ic.selected_options = [
            choice.value
            for choice in ic.choices
            if not isinstance(choice, Separator)
            and choice.value not in ic.selected_options
            and not choice.disabled
        ]

    @bindings.add("a", eager=True)
    def select_all(_event):  # type: ignore[no-untyped-def]
        all_selected = True
        for choice in ic.choices:
            if (
                not isinstance(choice, Separator)
                and choice.value not in ic.selected_options
                and not choice.disabled
            ):
                ic.selected_options.append(choice.value)
                all_selected = False
        if all_selected:
            ic.selected_options = []

    def move_cursor_down(event):  # type: ignore[no-untyped-def]
        ic.select_next()
        while not ic.is_selection_valid():
            ic.select_next()

    def move_cursor_up(event):  # type: ignore[no-untyped-def]
        ic.select_previous()
        while not ic.is_selection_valid():
            ic.select_previous()

    bindings.add(Keys.Down, eager=True)(move_cursor_down)
    bindings.add(Keys.Up, eager=True)(move_cursor_up)
    bindings.add("j", eager=True)(move_cursor_down)
    bindings.add("k", eager=True)(move_cursor_up)
    bindings.add(Keys.ControlN, eager=True)(move_cursor_down)
    bindings.add(Keys.ControlP, eager=True)(move_cursor_up)

    @bindings.add(Keys.ControlM, eager=True)
    def submit(event):  # type: ignore[no-untyped-def]
        selected_values = get_selected_values()
        ic.submission_attempted = True
        if not selected_values and focus_submit_values:
            pointed_value = ic.get_pointed_at().value
            if pointed_value in focus_submit_values:
                ic.is_answered = True
                event.app.exit(result=[pointed_value])
                return
        ic.is_answered = True
        event.app.exit(result=selected_values)

    @bindings.add(Keys.Any)
    def swallow(_event):  # type: ignore[no-untyped-def]
        return

    result = Question(
        Application(
            layout=layout,
            key_bindings=bindings,
            style=merged_style,
        )
    ).unsafe_ask()
    if result is None:
        raise KeyboardInterrupt
    return result


class QuestionaryPrompts:
    async def select(self, message: str, choices: Sequence[T]) -> T:
        def _ask() -> T:
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

    async def checkbox(
        self,
        message: str,
        choices: Sequence[T],
        *,
        focus_submit_values: frozenset[object] | None = None,
    ) -> list[T]:
        def _ask() -> list[T]:
            if focus_submit_values:
                selection = _ask_checkbox(
                    message,
                    list(choices),
                    focus_submit_values=focus_submit_values,
                )
            else:
                selection = questionary.checkbox(
                    message,
                    choices=list(choices),
                ).ask()

            if selection is None:
                raise KeyboardInterrupt
            return selection

        return await asyncio.to_thread(_ask)

    async def print_message(self, message: str, *, style: str = "fg:red") -> None:
        await asyncio.to_thread(lambda: questionary.print(message, style=style))
