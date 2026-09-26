"""CARD-502 operator contract: Adopt and an Agent Studio tick are still listed after a restart (REQ-502-003)."""

from __future__ import annotations

import os
from pathlib import Path

from starlette.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

RUNBOOK = "---\nname: cite-sources\ndescription: Always cite the source\n---\n\n# Cite Sources\n"


def _app(db: str, wiki: Path):
    store = SQLiteStateStore(db_path=db)
    store.initialize_db()
    return create_app(state_store=store, wiki_path=str(wiki))


def _skills(client, agent_id):
    body = client.get(f"/api/agents/{agent_id}").json()
    return (body.get("agent") or body).get("allowed_skill") or []


def test_adopt_and_studio_tick_survive_restart():
    db = os.environ["AUTOREIV_DB_PATH"]
    wiki = Path(os.environ["AUTOREIV_WIKI_PATH"])
    wiki.mkdir(parents=True, exist_ok=True)
    with TestClient(_app(db, wiki)) as client:
        res = client.post("/api/skills/adopt", json={"target_agent_id": "autoreiv", "skill_id": "cite-sources", "runbook_markdown": RUNBOOK})
        assert res.status_code == 200, res.text
        assert res.json()["active"] is True
        tutor = client.get("/api/agents/tutor").json()
        tutor = tutor.get("agent") or tutor
        assert client.put("/api/agents/tutor", json={**tutor, "allowed_skill": [*tutor["allowed_skill"], "build-agent-pack"]}).status_code == 200
    with TestClient(_app(db, wiki)) as client:
        assert "cite-sources" in _skills(client, "autoreiv")
        assert "build-agent-pack" in _skills(client, "tutor")
