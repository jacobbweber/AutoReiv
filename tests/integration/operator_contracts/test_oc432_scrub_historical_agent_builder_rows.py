"""CARD-432 operator contract: historical agent-builder ids become developer.

REQ-432-001: boot sets sessions.agent_id, messages.agent_id, jobs.agent_id,
and phases.assigned_agent_id from agent-builder to developer.
REQ-432-002: those rows are not deleted and message content is unchanged.
REQ-432-003: a second boot leaves rows that already say developer unchanged.
REQ-432-004: boot does not recreate an agent-builder profile.

Temp user-data only [ADR-0055].
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from src.infrastructure.memory.sqlite_store import SQLiteStateStore

_TRANSCRIPT = "Old Agent Builder chat. The words agent-builder stay in this message. Do not edit this transcript."
_DEV_TRANSCRIPT = "Already on Developer. Leave this message and its agent id alone."
_OTHER_TRANSCRIPT = "Platform chat. This agent id is autoreiv and must stay autoreiv."


def _refuse_live(user_data: Path) -> None:
    local_app = os.environ.get("LOCALAPPDATA") or ""
    if not local_app:
        return
    live_root = (Path(local_app) / "AutoReiv").resolve()
    ud = str(user_data.resolve()).replace("\\", "/").lower()
    live = str(live_root).replace("\\", "/").lower()
    assert ud != live and not ud.startswith(live + "/"), f"operator contracts must not use live user-data: {user_data}"


def _snapshot(db: Path) -> dict:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        sessions = [
            dict(row) for row in conn.execute("SELECT id, agent_id, title, updated_at FROM sessions ORDER BY id")
        ]
        messages = [
            dict(row)
            for row in conn.execute("SELECT id, session_id, agent_id, role, content FROM messages ORDER BY id")
        ]
        jobs = [dict(row) for row in conn.execute("SELECT id, session_id, agent_id, goal FROM jobs ORDER BY id")]
        phases = [
            dict(row) for row in conn.execute("SELECT id, job_id, assigned_agent_id, name FROM phases ORDER BY id")
        ]
        profiles = conn.execute("SELECT COUNT(*) FROM custom_agents WHERE id = ?", ("agent-builder",)).fetchone()[0]
    finally:
        conn.close()
    return {
        "sessions": sessions,
        "messages": messages,
        "jobs": jobs,
        "phases": phases,
        "agent_builder_profiles": profiles,
        "counts": {
            "sessions": len(sessions),
            "messages": len(messages),
            "jobs": len(jobs),
            "phases": len(phases),
        },
    }


def _boot(store: SQLiteStateStore, wiki: Path, create_app, test_client_cls):
    app = create_app(state_store=store, wiki_path=str(wiki))
    return app, test_client_cls(app)


