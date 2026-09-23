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

from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import AgentProfile
from src.domain.orchestration.models import Job, Phase
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


def test_oc432_boot_rewrites_historical_agent_builder_ids_without_deletes(tmp_path, monkeypatch):
    """Opening an old Agent Builder chat shows Developer. The transcript stays."""
    # Import while the autouse fixture still points at an empty data dir.
    # src.web.app calls create_app() at import, and that boot must not move this test's db.
    from starlette.testclient import TestClient

    from src.web.app import create_app

    user_data = (tmp_path / "user-data").resolve()
    wiki = user_data / "wiki"
    db = user_data / "autoreiv.db"
    user_data.mkdir(parents=True, exist_ok=True)
    wiki.mkdir(parents=True, exist_ok=True)
    _refuse_live(user_data)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(user_data))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki))
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "local")

    store = SQLiteStateStore(db_path=str(db))
    store.initialize_db()
    store.save_agent_profile(
        AgentProfile(
            id="agent-builder",
            name="Agent Builder",
            description="Leftover profile that boot must delete and not recreate.",
            system_prompt="You are a retired hidden builtin that must not boot.",
            is_builtin=True,
            show_in_chat=False,
        )
    )

    stale = store.create_session(agent_id="agent-builder", title="Old Agent Builder chat", session_id="sess-432")
    user_id = store.save_message(stale.id, "agent-builder", ChatMessage(role=Role.USER, content=_TRANSCRIPT))
    assistant_id = store.save_message(
        stale.id,
        "agent-builder",
        ChatMessage(role=Role.ASSISTANT, content="I drafted the pack under Agent Builder."),
    )
    kept = store.create_session(agent_id="developer", title="Already Developer", session_id="sess-432-dev")
    kept_id = store.save_message(kept.id, "developer", ChatMessage(role=Role.USER, content=_DEV_TRANSCRIPT))
    other = store.create_session(agent_id="autoreiv", title="Platform chat", session_id="sess-432-other")
    other_id = store.save_message(other.id, "autoreiv", ChatMessage(role=Role.USER, content=_OTHER_TRANSCRIPT))

    store.create_job(
        Job(
            id="job-432",
            goal="Old Agent Builder job",
            session_id=stale.id,
            agent_id="agent-builder",
            status="done",
        ),
        phases=[
            Phase(
                id="phase-432",
                job_id="job-432",
                name="author",
                index=0,
                assigned_agent_id="agent-builder",
                status="done",
            )
        ],
    )
    store.create_job(
        Job(
            id="job-432-dev",
            goal="Already Developer job",
            session_id=kept.id,
            agent_id="developer",
            status="done",
        ),
        phases=[
            Phase(
                id="phase-432-dev",
                job_id="job-432-dev",
                name="keep",
                index=0,
                assigned_agent_id="developer",
                status="done",
            )
        ],
    )

    before = _snapshot(db)
    assert before["counts"] == {"sessions": 3, "messages": 4, "jobs": 2, "phases": 2}
    assert before["agent_builder_profiles"] == 1
    assert {row["id"] for row in before["messages"]} == {user_id, assistant_id, kept_id, other_id}

    app, client = _boot(store, wiki, create_app, TestClient)
    with client:
        listed = client.get("/api/sessions")
        assert listed.status_code == 200
        by_id = {row["id"]: row for row in listed.json()}
        assert set(by_id) == {"sess-432", "sess-432-dev", "sess-432-other"}
        assert by_id["sess-432"]["agent_id"] == "developer"
        assert by_id["sess-432"]["title"] == "Old Agent Builder chat"
        assert by_id["sess-432-dev"]["agent_id"] == "developer"
        assert by_id["sess-432-other"]["agent_id"] == "autoreiv"

        messages = client.get("/api/sessions/sess-432/messages")
        assert messages.status_code == 200
        bodies = [row["content"] for row in messages.json()]
        assert bodies == [_TRANSCRIPT, "I drafted the pack under Agent Builder."]
        assert "agent-builder" in bodies[0]

        journey = client.get("/api/jobs/job-432")
        assert journey.status_code == 200
        timeline = journey.json()["timeline"]
        job_event = next(row for row in timeline if row["kind"] == "job")
        phase_event = next(row for row in timeline if row["kind"] == "phase" and row["phase_id"] == "phase-432")
        assert job_event["agent_id"] == "developer"
        assert phase_event["assigned_agent_id"] == "developer"

        missing = client.get("/api/agents/agent-builder")
        assert missing.status_code == 404
        roster = {row["id"] for row in client.get("/api/agents").json()}
        assert "agent-builder" not in roster

    assert app.state.registry.get_agent("agent-builder") is None
    assert store.get_agent_profile("agent-builder") is None

    after = _snapshot(db)
    assert after["counts"] == before["counts"]
    assert after["agent_builder_profiles"] == 0
    assert {row["id"] for row in after["messages"]} == {user_id, assistant_id, kept_id, other_id}
    rewritten = {row["id"]: row for row in after["messages"]}
    assert rewritten[user_id]["agent_id"] == "developer"
    assert rewritten[user_id]["content"] == _TRANSCRIPT
    assert rewritten[assistant_id]["agent_id"] == "developer"
    assert rewritten[assistant_id]["content"] == "I drafted the pack under Agent Builder."
    assert rewritten[kept_id]["agent_id"] == "developer"
    assert rewritten[kept_id]["content"] == _DEV_TRANSCRIPT
    assert rewritten[other_id]["agent_id"] == "autoreiv"
    assert rewritten[other_id]["content"] == _OTHER_TRANSCRIPT
    jobs = {row["id"]: row for row in after["jobs"]}
    phases = {row["id"]: row for row in after["phases"]}
    assert jobs["job-432"]["agent_id"] == "developer"
    assert jobs["job-432-dev"]["agent_id"] == "developer"
    assert phases["phase-432"]["assigned_agent_id"] == "developer"
    assert phases["phase-432-dev"]["assigned_agent_id"] == "developer"
    sessions = {row["id"]: row for row in after["sessions"]}
    assert sessions["sess-432-dev"]["updated_at"] == next(
        row["updated_at"] for row in before["sessions"] if row["id"] == "sess-432-dev"
    )
    assert sessions["sess-432-other"]["agent_id"] == "autoreiv"

    _boot(store, wiki, create_app, TestClient)
    second = _snapshot(db)
    assert second == after
    assert store.get_agent_profile("agent-builder") is None
    assert store.get_session("sess-432").agent_id == "developer"
    assert store.get_job("job-432").agent_id == "developer"
    assert store.get_phase("phase-432").assigned_agent_id == "developer"
