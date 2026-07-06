from typing import TypeVar

from k_commerce_cli.services.tools import ToolInvocationResult, ToolRequestError

T = TypeVar("T")


def expect_tool_result(
    tool_name: str,
    result: ToolInvocationResult,
    result_type: type[T],
) -> T:
    if isinstance(result, result_type):
        return result
    raise ToolRequestError(tool_name, f"Expected {result_type.__name__} result")
