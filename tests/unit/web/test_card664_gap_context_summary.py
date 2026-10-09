"""CARD-664: a gap keeps the context_summary it was created with, through the repository and the API."""

import sqlite3

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.connection import SQLiteConnectionManager
from src.infrastructure.memory.repositories.capability_gaps import CapabilityGapRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

SUMMARY = "I do not have a direct email-sending tool in my skill set, so I could not email the notes."


def _repo(tmp_path):
    return CapabilityGapRepository(connection_manager=SQLiteConnectionManager(db_path=str(tmp_path / "gaps.db")))


def test_repository_keeps_context_summary(tmp_path):
    repo = _repo(tmp_path)
    gap = repo.create_gap(
        "wiki", user_prompt="email me the notes", missing_capability="email sending", context_summary=SUMMARY
    )
    assert gap.context_summary == SUMMARY
    assert repo.get_gap(gap.id).context_summary == SUMMARY
    assert [g.context_summary for g in repo.list_gaps(agent_id="wiki")] == [SUMMARY]
    assert [g.context_summary for g in repo.list_gaps()] == [SUMMARY]


def test_repository_gap_without_summary_still_works(tmp_path):
    repo = _repo(tmp_path)
    gap = repo.create_gap("wiki", turn_text="email me the notes", identified_capability="email sending")
    assert gap.context_summary is None
    assert repo.get_gap(gap.id).context_summary is None
    assert repo.list_gaps(agent_id="wiki")[0].identified_capability == "email sending"


def test_old_database_gains_the_column_and_keeps_its_gaps(tmp_path):
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE agent_capability_gaps (
            id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, session_id TEXT, turn_text TEXT NOT NULL,
            identified_capability TEXT NOT NULL, suggested_tool_name TEXT,
            status TEXT NOT NULL DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO agent_capability_gaps (id, agent_id, turn_text, identified_capability)
        VALUES ('gap_old', 'wiki', 'old turn', 'old capability');
        """
    )
    conn.commit()
    conn.close()

    repo = CapabilityGapRepository(connection_manager=SQLiteConnectionManager(db_path=str(db)))
    old = repo.get_gap("gap_old")
    assert old.identified_capability == "old capability"
    assert old.context_summary is None
    new = repo.create_gap("wiki", turn_text="t", identified_capability="c", context_summary=SUMMARY)
    assert repo.get_gap(new.id).context_summary == SUMMARY


@pytest.mark.slow
@pytest.mark.asyncio
async def test_gaps_api_returns_context_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    app = create_app(state_store=SQLiteStateStore(db_path=str(tmp_path / "api.db")))
    app.state.gateway = None  # explicit capability below: no synthesis, never a model call

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        base = {"turn_text": "email me the notes", "identified_capability": "Email sending"}
        with_summary = (await ac.post("/api/agents/wiki/gaps", json={**base, "context_summary": SUMMARY})).json()
        assert with_summary["gap"]["context_summary"] == SUMMARY

        reply_only = (await ac.post("/api/agents/wiki/gaps", json={**base, "assistant_response": SUMMARY})).json()
        assert reply_only["gap"]["context_summary"] == SUMMARY

        bare = await ac.post("/api/agents/wiki/gaps", json=base)
        assert bare.status_code == 200
        assert bare.json()["gap"]["context_summary"] is None

        listed = {g["id"]: g for g in (await ac.get("/api/agents/wiki/gaps")).json()["gaps"]}
        assert listed[with_summary["gap"]["id"]]["context_summary"] == SUMMARY
        assert listed[reply_only["gap"]["id"]]["context_summary"] == SUMMARY
        assert listed[bare.json()["gap"]["id"]]["context_summary"] is None
        everyone = {g["id"]: g for g in (await ac.get("/api/agents/gaps")).json()["gaps"]}
        assert everyone[with_summary["gap"]["id"]]["context_summary"] == SUMMARY
