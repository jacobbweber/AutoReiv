"""CARD-437/438: datetime-safe JSON at tool/telemetry/SSE boundaries.

Live regression (CARD-438 education-mode Tutor chat): get_session_info returned
raw datetime created_at/updated_at; agent_kernel.stream_turn then hit
json.dumps(tool_res.output) / sizing path -> TypeError shown as Tutor reply.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from src.application.kernel.tool_registry import _tool_context
from src.application.skills.platform_primitives import PlatformPrimitiveTools
from src.infrastructure.serialization.json_safe import (
    dumps_jsonable,
    dumps_tool_output,
    json_default,
    to_jsonable,
)


def test_dumps_tool_output_with_datetime_in_course_tutor_payload():
    """Regression: Tutor chat died with TypeError when tool output contained datetime.

    Observability: agent_kernel.stream_turn json.dumps(tool_res.output) at former L1648.
    Education course/tutor-shaped payloads are the high-probability source.
    """
    due = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
    payload = {
        "course": {
            "course_id": "course_f4f105904ee1",
            "topic_id": "okta",
            "created_at": due,
            "updated_at": due,
        },
        "tutor_context": {
            "topic": "okta",
            "weak_items": [
                {
                    "item_id": "m1",
                    "next_due": due,
                    "last_graded_at": due,
                }
            ],
        },
        "chrome": {
            "mastery": [{"next_due": due, "grade": "miss"}],
            "as_of": due,
            "day": date(2026, 9, 23),
        },
    }

    with pytest.raises(TypeError, match="datetime"):
        json.dumps(payload)

    encoded = dumps_tool_output(payload)
    assert isinstance(encoded, str)
    assert "course_f4f105904ee1" in encoded
    assert "2026-09-27" in encoded
    again = json.loads(encoded)
    assert again["course"]["course_id"] == "course_f4f105904ee1"
    assert again["tutor_context"]["weak_items"][0]["next_due"].startswith("2026-09-27")


def test_to_jsonable_makes_education_mastery_payload_raw_json_dumps_safe():
    """CARD-438: after kernel-boundary sanitize, even bare json.dumps must succeed.

    Covers mastery/quiz-grade shaped outputs with datetime next_due (and session info).
    """
    due = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)
    education_tool_shaped = {
        "success": True,
        "durable": True,
        "grade": "pass",
        "next_due": due,
        "item": {"item_id": "edu_1", "next_due": due, "last_graded_at": due},
    }
    session_info_shaped = {
        "session_id": "s1",
        "agent_id": "tutor",
        "created_at": due,
        "updated_at": due,
        "status": "active",
    }

    with pytest.raises(TypeError, match="datetime"):
        json.dumps(education_tool_shaped)
    with pytest.raises(TypeError, match="datetime"):
        json.dumps(session_info_shaped)

    safe_edu = to_jsonable(education_tool_shaped)
    safe_sess = to_jsonable(session_info_shaped)
    # Bare json.dumps must not raise after sanitization (missed sink defense).
    assert json.loads(json.dumps(safe_edu))["next_due"].startswith("2026-09-27")
    assert json.loads(json.dumps(safe_sess))["created_at"].startswith("2026-09-27")
    assert dumps_tool_output(education_tool_shaped)
    assert dumps_tool_output(session_info_shaped)


def test_get_session_info_output_is_json_serializable():
    """Live path: Tutor called get_session_info; created_at/updated_at were datetime."""
    due = datetime(2026, 9, 23, 12, 0, 0, tzinfo=timezone.utc)

    class _Store:
        def get_session(self, session_id: str):
            return SimpleNamespace(created_at=due, updated_at=due)

    tools = PlatformPrimitiveTools(state_store=_Store())
    token = _tool_context.set(
        {"agent_id": "tutor", "session_id": "sess-1", "approval_mode": "ask"}
    )
    try:
        info = tools.get_session_info()
    finally:
        _tool_context.reset(token)

    assert info["session_id"] == "sess-1"
    assert info["agent_id"] == "tutor"
    # Must be JSON-native (no datetime) so any kernel/SSE sink is safe.
    json.dumps(info)
    assert isinstance(info["created_at"], str)
    assert isinstance(info["updated_at"], str)
    assert info["created_at"].startswith("2026-09-23")


def test_dumps_jsonable_default_isoformat():
    dt = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert json_default(dt) == dt.isoformat()
    assert '"2026-01-02' in dumps_jsonable({"t": dt})


def test_dumps_tool_output_non_container():
    assert dumps_tool_output(None) == ""
    assert dumps_tool_output("plain") == "plain"
    assert dumps_tool_output(42) == "42"
