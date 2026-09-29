"""CARD-573: Agent Studio Always auto-run preference; new routines follow it, saved routines keep theirs.

Real FastAPI app + SQLite on the per-test temp data folder (tests/conftest.py).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization
from src.infrastructure.agents.agent_files import meta_from_profile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def boot():
    db = os.environ["AUTOREIV_DB_PATH"]
    wiki = Path(os.environ["AUTOREIV_WIKI_PATH"])
    wiki.mkdir(parents=True, exist_ok=True)
    store = SQLiteStateStore(db_path=db)
    store.initialize_db()
    app = create_app(state_store=store, wiki_path=str(wiki))
    return TestClient(app), app


def _agent(client, agent_id):
    body = client.get(f"/api/agents/{agent_id}").json()
    return body.get("agent") or body


def _save(client, agent_id, **changes):
    agent = _agent(client, agent_id)
    payload = {**agent, **changes, "expected_skills_version": agent["skills_version"]}
    for key in [k for k, v in changes.items() if v is ...]:
        payload.pop(key)
    res = client.put(f"/api/agents/{agent_id}", json=payload)
    assert res.status_code == 200, res.text
    return _agent(client, agent_id)


def _routine(client, rid):
    return next(r for r in client.get("/api/routines").json() if r["id"] == rid)


def test_field_defaults_off_and_is_written_to_the_agent_file_only_when_on():
    base = dict(id="x", name="X", description="d", system_prompt="p")
    assert AgentProfile(**base).always_auto_run is False
    assert "always_auto_run" not in meta_from_profile(AgentProfile(**base))[0]
    assert meta_from_profile(AgentProfile(**base, always_auto_run=True))[0]["always_auto_run"] is True
    assert "always_auto_run" in AgentCustomization.model_fields  # per-agent override path


def test_agent_studio_saves_and_keeps_the_preference(boot):
    client, app = boot
    assert _agent(client, "tutor")["always_auto_run"] is False
    assert _save(client, "tutor", always_auto_run=True)["always_auto_run"] is True
    assert app.state.registry.get_agent("tutor").always_auto_run is True
    # A save that omits the field (older client) keeps it.
    assert _save(client, "tutor", always_auto_run=...)["always_auto_run"] is True
    assert _save(client, "tutor", always_auto_run=False)["always_auto_run"] is False


def test_new_routine_follows_the_agent_and_saved_routines_keep_their_value(boot):
    client, _app = boot
    body = {"name": "x", "prompt_template": "Say hi.", "cron_expr": "0 * * * *", "enabled": False}
    assert client.post("/api/routines", json={**body, "id": "r-before", "agent_id": "tutor"}).status_code == 200
    _save(client, "tutor", always_auto_run=True)
    assert client.post("/api/routines", json={**body, "id": "r-new", "agent_id": "tutor"}).status_code == 200
    assert client.post("/api/routines", json={**body, "id": "r-ask", "agent_id": "tutor", "approval_mode": "ask"}).status_code == 200
    assert client.post("/api/routines", json={**body, "id": "r-other", "agent_id": "autoreiv"}).status_code == 200
    assert _routine(client, "r-before")["approval_mode"] == "ask"  # existing routine unchanged
    assert _routine(client, "r-new")["approval_mode"] == "run"  # new routine starts with Auto-run on
    assert _routine(client, "r-ask")["approval_mode"] == "ask"  # the routine's own value wins
    assert _routine(client, "r-other")["approval_mode"] == "ask"  # agent without the preference
    # An update that omits approval_mode keeps the saved value; an explicit value wins.
    assert client.put("/api/routines/r-ask", json={**body, "agent_id": "tutor"}).status_code == 200
    assert _routine(client, "r-ask")["approval_mode"] == "ask"
    assert client.put("/api/routines/r-new", json={**body, "agent_id": "tutor", "approval_mode": "ask"}).status_code == 200
    assert _routine(client, "r-new")["approval_mode"] == "ask"
