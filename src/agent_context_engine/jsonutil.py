"""Validate JSON without changing numeric lexemes, key order, or string escapes."""
import json
from decimal import Decimal
from typing import Any
from .errors import ValidationError


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ValidationError("Duplicate JSON key; passthrough required")
        result[key] = value
    return result


def strict_loads(text: str, *, decimals: bool = False) -> Any:
    def invalid(value: str) -> Any:
        raise ValidationError("Non-finite JSON constant")
    try:
        return json.loads(text, object_pairs_hook=_pairs,
                          parse_float=Decimal if decimals else float,
                          parse_constant=invalid)
    except (ValueError, RecursionError) as exc:
        raise ValidationError("Malformed or excessively nested JSON") from exc


def compact_json(text: str) -> str:
    strict_loads(text, decimals=True)
    out: list[str] = []
    quoted = escaped = False
    for char in text:
        if quoted:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
            out.append(char)
        elif char not in " \r\n\t":
            out.append(char)
    return "".join(out)


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def fields(obj: Any, required: set[str], optional: set[str] | frozenset[str] = frozenset()) -> None:
    if not isinstance(obj, dict) or not required <= obj.keys() or obj.keys() - required - optional:
        raise ValidationError("Missing or unknown fields")
