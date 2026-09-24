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


def dumps_jsonable(obj: Any, *, indent: Optional[int] = None, sort_keys: bool = False) -> str:
    """json.dumps with datetime/date-safe default (never raises TypeError on datetime)."""
    return json.dumps(obj, default=json_default, indent=indent, sort_keys=sort_keys)


def dumps_tool_output(output: Any) -> str:
    """Serialize a tool result payload for ChatMessage content / telemetry sizing."""
    if isinstance(output, (dict, list)):
        return dumps_jsonable(output)
    if output is None:
        return ""
    return str(output)
