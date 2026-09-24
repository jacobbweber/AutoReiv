"""JSON helpers that tolerate datetime/date at serialization boundaries."""

from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID


def json_default(obj: Any) -> Any:
    """Convert non-JSON-native values to JSON-safe primitives (ISO strings preferred)."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except TypeError:
            return obj.model_dump()
    if hasattr(obj, "isoformat"):
        try:
            return obj.isoformat()
        except Exception:
            pass
    return str(obj)


def to_jsonable(value: Any) -> Any:
    """Deep-convert values so bare ``json.dumps`` never sees datetime/date/UUID/Path/Enum.

    Applied at the kernel tool-result boundary so every sink (tool message,
    telemetry sizing, SSE, accidental raw ``json.dumps``) is safe — including
    education mastery ``next_due`` and ``get_session_info`` session timestamps.
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return to_jsonable(value.model_dump(mode="json"))
        except TypeError:
            return to_jsonable(value.model_dump())
    return value


def dumps_jsonable(obj: Any, *, indent: Optional[int] = None, sort_keys: bool = False) -> str:
    """json.dumps with datetime/date-safe default (never raises TypeError on datetime)."""
    return json.dumps(obj, default=json_default, indent=indent, sort_keys=sort_keys)


def dumps_tool_output(output: Any) -> str:
    """Serialize a tool result payload for ChatMessage content / telemetry sizing."""
    if isinstance(output, (dict, list)):
        return dumps_jsonable(to_jsonable(output))
    if output is None:
        return ""
    return str(output)
