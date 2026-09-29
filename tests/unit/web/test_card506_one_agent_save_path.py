"""CARD-506: one agent-save path. POST /api/settings/agents/{id} is gone; PUT /api/agents/{id} saves model fields."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def client():
    db = os.environ["AUTOREIV_DB_PATH"]
    wiki = Path(os.environ["AUTOREIV_WIKI_PATH"])
    wiki.mkdir(parents=True, exist_ok=True)
    store = SQLiteStateStore(db_path=db)
    store.initialize_db()
    return TestClient(create_app(state_store=store, wiki_path=str(wiki)))


def _agent(client, agent_id):
    body = client.get(f"/api/agents/{agent_id}").json()
    return body.get("agent") or body


def test_duplicate_settings_save_route_is_gone(client):
    res = client.post("/api/settings/agents/developer", json={"agent_id": "developer", "max_turns": 7})
    assert res.status_code in (404, 405)
    static = Path("src/web/static")
    assert not [p for p in static.rglob("*.js") if "/api/settings/agents" in p.read_text(encoding="utf-8")]


def test_agent_studio_put_saves_model_provider_and_context(client):
    agent = _agent(client, "developer")
    payload = {
        **agent,
        "model": "qwen3.8:latest",
        "provider": "ollama",
        "context_window": 131072,
        "expected_skills_version": agent["skills_version"],
    }
    res = client.put("/api/agents/developer", json=payload)
    assert res.status_code == 200, res.text
    after = _agent(client, "developer")
    assert after["model"] == "qwen3.8:latest"
    assert after["provider"] == "ollama"
    assert after["context_window"] == 131072
