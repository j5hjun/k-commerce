from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, TypeAlias, TypeIs, override

from .types import JSONPrimitive, JSONValue, ToolInvocationResult

if TYPE_CHECKING:
    from dataclasses import Field


class DataclassInstance(Protocol):
    __dataclass_fields__: dict[str, "Field[SerializableValue]"]

    @override
    def __getattribute__(self, __name: str) -> SerializableValue: ...


SerializableValue: TypeAlias = (
    JSONPrimitive
    | StrEnum
    | DataclassInstance
    | Mapping[str, "SerializableValue"]
    | Sequence["SerializableValue"]
)


def _is_dataclass_instance(value: SerializableValue | ToolInvocationResult) -> TypeIs[DataclassInstance]:
    return is_dataclass(value) and not isinstance(value, type)


def to_jsonable(value: SerializableValue | ToolInvocationResult) -> JSONValue:
    if isinstance(value, StrEnum):
        return str(value)
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, Sequence):
        return [to_jsonable(item) for item in value]
    if _is_dataclass_instance(value):
        return {
            field.name: to_jsonable(value.__getattribute__(field.name))
            for field in value.__dataclass_fields__.values()
        }
    msg = f"Unsupported serializable value: {type(value).__name__}"
    raise TypeError(msg)
