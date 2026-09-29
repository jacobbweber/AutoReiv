"""CARD-572: only an explicit Run as a job (Chat box or routine setting) starts a standing Job."""

from __future__ import annotations

import re
from pathlib import Path

from src.domain.routines.models import Routine, ScheduleType, routine_runs_as_job
from src.web.routers.chat import ChatStreamRequest

ROOT = Path(__file__).resolve().parents[3]
GONE = ("route_standing_chat", "is_outcome_shaped", "is_multi_step_outcome", "_GOAL_DELIVERABLE", "StandingRoute", "goal_mode")


def test_keyword_routing_and_goal_mode_are_gone_from_src():
    """Guard: no code path classifies message text to start a Job; the dead goal_mode flag is gone."""
    offenders = []
    for path in list((ROOT / "src").rglob("*.py")) + list((ROOT / "src/web/static").rglob("*.js")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name in GONE:
            if re.search(rf"\b{name}\b", text):
                offenders.append(f"{path.relative_to(ROOT).as_posix()}: {name}")
    assert offenders == []


def test_chat_request_has_run_as_job_off_by_default():
    fields = ChatStreamRequest.model_fields
    assert "run_as_job" in fields and fields["run_as_job"].default is False
    assert "goal_mode" not in fields


def test_chat_starts_a_job_only_from_the_flag():
    src = (ROOT / "src/web/routers/chat.py").read_text(encoding="utf-8")
    assert "if (not resume) and req.run_as_job:" in src
    assert src.count("create_job_from_catalog_resolve(") == 1


def test_routine_runs_as_job_only_from_its_setting():
    base = dict(id="r", name="r", agent_id="autoreiv", schedule_type=ScheduleType.INTERVAL, interval_seconds=60)
    words = "First research the wiki, then write a note that summarizes it, finally verify it exists."
    assert routine_runs_as_job(Routine(prompt=words, **base)) is False
    assert routine_runs_as_job(Routine(prompt="hi", metadata={"run_as_job": True}, **base)) is True
    assert routine_runs_as_job(Routine(prompt="hi", metadata={"run_as_job": "yes"}, **base)) is False
    executor = (ROOT / "src/application/routines/executor.py").read_text(encoding="utf-8")
    assert "routine_runs_as_job(routine)" in executor


def test_routine_api_saves_and_keeps_run_as_job(tmp_path):
    from fastapi.testclient import TestClient

    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app

    app = create_app(state_store=SQLiteStateStore(db_path=str(tmp_path / "s.db")))
    with TestClient(app) as client:
        body = {"name": "r572", "agent_id": "autoreiv", "prompt_template": "First do X, then Y.", "cron_expr": "0 * * * *"}
        assert client.post("/api/routines", json=body).status_code == 200
        row = next(r for r in client.get("/api/routines").json() if r["id"] == "r572")
        assert row["run_as_job"] is False
        assert client.put("/api/routines/r572", json={**body, "run_as_job": True}).status_code == 200
        row = next(r for r in client.get("/api/routines").json() if r["id"] == "r572")
        assert row["run_as_job"] is True
        # An update that omits the field keeps the saved value.
        assert client.put("/api/routines/r572", json=body).status_code == 200
        row = next(r for r in client.get("/api/routines").json() if r["id"] == "r572")
        assert row["run_as_job"] is True
