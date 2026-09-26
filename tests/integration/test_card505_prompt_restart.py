"""CARD-505 operator contract: a Max-Turns-only Agent Studio save never locks AutoReiv across restarts."""

from __future__ import annotations

import os
from pathlib import Path

from starlette.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


def _app(db: str, wiki: Path):
    store = SQLiteStateStore(db_path=db)
    store.initialize_db()
    return create_app(state_store=store, wiki_path=str(wiki))


def test_max_turns_save_and_restarts_keep_autoreiv_on_platform_updates():
    db = os.environ["AUTOREIV_DB_PATH"]
    wiki = Path(os.environ["AUTOREIV_WIKI_PATH"])
    wiki.mkdir(parents=True, exist_ok=True)
    with TestClient(_app(db, wiki)):
        pass
    with TestClient(_app(db, wiki)) as client:
        body = client.get("/api/agents/autoreiv").json()
        agent = body.get("agent") or body
        payload = {**agent, "max_turns": int(agent.get("max_turns") or 50) + 1, "system_prompt": agent["system_prompt"].strip()}
        assert client.put("/api/agents/autoreiv", json=payload).status_code == 200
    with TestClient(_app(db, wiki)) as client:
        status = client.get("/api/platform-packs/sync-status").json()
        entry = next(r for r in status["results"] if r["pack_id"] == "autoreiv")
        assert entry["status"] not in {"skipped_user_modified", "promoted_partial"}, entry
        agent = client.get("/api/agents/autoreiv").json()
        agent = agent.get("agent") or agent
        assert int(agent["max_turns"]) == int(payload["max_turns"])
