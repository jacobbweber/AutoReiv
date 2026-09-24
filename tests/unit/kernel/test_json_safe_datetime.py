"""CARD-437: datetime-safe JSON at tool/telemetry/SSE boundaries."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.infrastructure.serialization.json_safe import dumps_jsonable, dumps_tool_output, json_default


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
        import json

        json.dumps(payload)

    encoded = dumps_tool_output(payload)
    assert isinstance(encoded, str)
    assert "course_f4f105904ee1" in encoded
    assert "2026-09-27" in encoded
    # Round-trip through json.loads must succeed
    import json

    again = json.loads(encoded)
    assert again["course"]["course_id"] == "course_f4f105904ee1"
    assert again["tutor_context"]["weak_items"][0]["next_due"].startswith("2026-09-27")


def test_dumps_jsonable_default_isoformat():
    dt = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert json_default(dt) == dt.isoformat()
    assert '"2026-01-02' in dumps_jsonable({"t": dt})


def test_dumps_tool_output_non_container():
    assert dumps_tool_output(None) == ""
    assert dumps_tool_output("plain") == "plain"
    assert dumps_tool_output(42) == "42"
