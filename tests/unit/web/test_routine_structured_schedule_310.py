"""CARD-310: structured schedule API create/preview + pause still blocks."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def app():
    store = SQLiteStateStore(db_path=":memory:")
    return create_app(state_store=store)


@pytest.mark.asyncio
async def test_preview_and_create_biweekly_structured(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        rule = {
            "weekdays": [2],
            "hour": 18,
            "minute": 0,
            "every_n_weeks": 2,
            "anchor_date": "2026-09-01",
        }
        prev = await ac.post(
            "/api/routines/preview-schedule",
            json={"schedule_rule": rule, "from_time": "2026-09-01T12:00:00+00:00"},
        )
        assert prev.status_code == 200
        body = prev.json()
        assert body["next_run_at"].startswith("2026-09-01T18:00:00")
        assert body["cron_representable"] is False
        assert body["cron_expression"] is None

        create = await ac.post(
            "/api/routines",
            json={
                "id": "card310-biweekly",
                "name": "CARD-310 Biweekly",
                "agent_id": "assistant",
                "prompt_template": "biweekly ping",
                "schedule_type": "structured",
                "schedule_rule": rule,
                "enabled": True,
            },
        )
        assert create.status_code == 200
        routine = create.json()["routine"]
        assert routine["schedule_type"] == "structured"
        assert routine["metadata"]["schedule_rule"]["every_n_weeks"] == 2
        assert routine["next_run_at"] is not None
        assert routine.get("cron_expression") in (None, "")

        listed = await ac.get("/api/routines")
        item = next(r for r in listed.json() if r["id"] == "card310-biweekly")
        assert item["schedule_rule"]["anchor_date"] == "2026-09-01"
        assert item["next_run_at"] is not None

        toggle = await ac.post("/api/routines/card310-biweekly/toggle")
        assert toggle.status_code == 200
        assert toggle.json()["enabled"] is False

        # Weekly representable cron preview
        weekly = await ac.post(
            "/api/routines/preview-schedule",
            json={"schedule_rule": {"weekdays": [1, 2, 3, 4, 5], "hour": 9, "minute": 0}},
        )
        assert weekly.status_code == 200
        assert weekly.json()["cron_expression"] == "0 9 * * 1,2,3,4,5"
