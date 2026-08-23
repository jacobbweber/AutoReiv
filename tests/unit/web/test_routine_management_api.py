"""
Integration tests for Routine Management REST API [REQ-ROUT-002, REQ-ROUT-003].
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def app():
    store = SQLiteStateStore(db_path=":memory:")
    return create_app(state_store=store)


@pytest.mark.asyncio
async def test_routine_crud_and_agent_filter_api(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List baseline routines
        res = await ac.get("/api/routines")
        assert res.status_code == 200
        routines = res.json()
        assert len(routines) >= 2
        # Check humanized schedules present
        assert "human_schedule" in routines[0]
        assert "next_run_eta" in routines[0]

        # 2. Filter routines by agent_id
        sys_res = await ac.get("/api/routines?agent_id=system-agent")
        assert sys_res.status_code == 200
        sys_routines = sys_res.json()
        assert all(r["agent_id"] == "system-agent" for r in sys_routines)

        # 3. Create Custom Routine
        new_routine = {
            "id": "hourly-db-monitor",
            "name": "Hourly Database Query Monitor",
            "description": "Inspect slow queries and index usage",
            "agent_id": "system-agent",
            "schedule_type": "cron",
            "cron_expr": "*/30 * * * *",
            "prompt_template": "Query system telemetry for slow tool executions.",
            "enabled": True,
        }
        create_res = await ac.post("/api/routines", json=new_routine)
        assert create_res.status_code == 200
        assert create_res.json()["status"] == "created"

        # 4. Update Routine
        update_payload = {
            "name": "Postgres Query & Index Monitor",
            "description": "Inspect slow queries and suggest index fixes",
            "agent_id": "system-agent",
            "schedule_type": "cron",
            "cron_expr": "0 * * * *",
            "prompt_template": "Analyze all database query metrics over the last hour.",
            "enabled": True,
        }
        put_res = await ac.put("/api/routines/hourly-db-monitor", json=update_payload)
        assert put_res.status_code == 200
        assert put_res.json()["status"] == "updated"

        # 5. Toggle Routine Pause/Resume
        toggle_res = await ac.post("/api/routines/hourly-db-monitor/toggle")
        assert toggle_res.status_code == 200
        assert toggle_res.json()["enabled"] is False

        toggle_res2 = await ac.post("/api/routines/hourly-db-monitor/toggle")
        assert toggle_res2.status_code == 200
        assert toggle_res2.json()["enabled"] is True

        # 6. Delete Custom Routine
        del_res = await ac.delete("/api/routines/hourly-db-monitor")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # 7. Cannot delete built-in baseline routine
        bad_del = await ac.delete("/api/routines/routine-sre-health")
        assert bad_del.status_code == 400
