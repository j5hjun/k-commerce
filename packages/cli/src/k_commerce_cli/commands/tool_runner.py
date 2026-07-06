from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import asyncclick as click
from pydantic import JsonValue as PydanticJSONValue
from pydantic import TypeAdapter, ValidationError

from k_commerce_cli.services.registry import get_provider as default_get_provider
from k_commerce_cli.services.registry import list_providers as default_list_providers
from k_commerce_cli.services.tools.invoke import invoke_tool
from k_commerce_cli.services.tools.serialization import to_jsonable
from k_commerce_cli.services.tools.types import JSONValue, ToolInvocationResult, ToolRequestError, ToolRuntimeOptions

REQUEST_FILE_OPTION_HELP: Final = "Read the canonical JSON request from a file."
TOOL_INVOCATION_TIMEOUT_SECONDS: Final = 20.0
JSON_VALUE_ADAPTER: Final[TypeAdapter[PydanticJSONValue]] = TypeAdapter(PydanticJSONValue)


@dataclass(frozen=True, slots=True)
class ToolRunnerError(Exception):
    error_type: str
    message: str
    tool_name: str | None = None
    field: str | None = None


def should_use_generic_runner(inline_json: str | None, request_file: Path | None) -> bool:
    return request_file is not None or (inline_json is not None and inline_json.lstrip().startswith(("{", "[")))


def is_canonical_tool_name(name: str) -> bool:
    return bool(name) and name == name.lower() and name.replace("_", "").isalnum()


def generic_tool_command(tool_name: str) -> click.Command:
    @click.command(name=tool_name)
    @click.argument("inline_json", required=False)
    @click.option(
        "--request-file",
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        default=None,
        help=REQUEST_FILE_OPTION_HELP,
    )
    async def command(
        inline_json: str | None,
        request_file: Path | None,
    ) -> None:
        await run_tool_command(tool_name, inline_json, request_file)

    return command


async def run_tool_command(
    tool_name: str,
    inline_json: str | None,
    request_file: Path | None,
) -> None:
    try:
        payload = _load_payload(tool_name, inline_json, request_file)
    except ToolRunnerError as exc:
        _emit_error(exc)
        raise click.exceptions.Exit(1) from exc

    try:
        result = await _invoke_tool_with_timeout(tool_name, payload)
    except ToolRunnerError as exc:
        _emit_error(exc)
        raise click.exceptions.Exit(1) from exc
    except TimeoutError as exc:
        _emit_error(
            ToolRunnerError(
                error_type="tool_error",
                message=str(exc),
                tool_name=tool_name,
            )
        )
        raise click.exceptions.Exit(1) from exc
    except ToolRequestError as exc:
        _emit_error(
            ToolRunnerError(
                error_type="tool_error",
                message=exc.message,
                tool_name=exc.tool_name,
                field=exc.field,
            )
        )
        raise click.exceptions.Exit(1) from exc
    except Exception:  # noqa: BLE001 - CLI security boundary emits sanitized JSON for unexpected provider/browser failures.
        _emit_error(
            ToolRunnerError(
                error_type="tool_error",
                message="Tool invocation failed.",
                tool_name=tool_name,
            )
        )
        raise click.exceptions.Exit(1) from None

    click.echo(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2))


async def _invoke_tool_with_timeout(tool_name: str, payload: JSONValue) -> ToolInvocationResult:
    timeout = asyncio.timeout(TOOL_INVOCATION_TIMEOUT_SECONDS)
    try:
        async with timeout:
            return await invoke_tool(
                tool_name,
                payload,
                runtime_options=ToolRuntimeOptions(
                    get_provider=default_get_provider,
                    list_providers=default_list_providers,
                ),
            )
    except TimeoutError as exc:
        if not timeout.expired():
            raise
        raise ToolRunnerError(
            error_type="tool_timeout",
            message=f"Tool invocation timed out after {TOOL_INVOCATION_TIMEOUT_SECONDS:g} seconds.",
            tool_name=tool_name,
        ) from exc


def _load_payload(
    tool_name: str,
    inline_json: str | None,
    request_file: Path | None,
) -> JSONValue:
    if inline_json is not None and request_file is not None:
        raise ToolRunnerError(
            error_type="usage_conflict",
            message="Pass either inline JSON or --request-file, not both.",
            tool_name=tool_name,
        )
    if request_file is not None:
        try:
            return _parse_json(tool_name, request_file.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ToolRunnerError(
                error_type="request_file",
                message=f"Could not read request file: {exc}",
                tool_name=tool_name,
            ) from exc
    if inline_json is None:
        raise ToolRunnerError(
            error_type="missing_request",
            message="Pass inline JSON or --request-file.",
            tool_name=tool_name,
        )
    return _parse_json(tool_name, inline_json)


def _parse_json(tool_name: str, source: str) -> JSONValue:
    try:
        return JSON_VALUE_ADAPTER.validate_json(source)
    except ValidationError as exc:
        raise ToolRunnerError(
            error_type="malformed_json",
            message="Malformed JSON: invalid JSON request.",
            tool_name=tool_name,
        ) from exc


def _emit_error(error: ToolRunnerError) -> None:
    body: dict[str, JSONValue] = {
        "type": error.error_type,
        "message": error.message,
    }
    if error.tool_name is not None:
        body["tool_name"] = error.tool_name
    if error.field is not None:
        body["field"] = error.field
    click.echo(json.dumps({"error": body}, ensure_ascii=False, indent=2), err=True)
