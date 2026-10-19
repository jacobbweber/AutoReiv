"""CARD-723 tests: matrix slot validation, chat stream approval_mode validation, Teach card reconciliation, and drawer refresh."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


def _make_client(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(data_dir / "autoreiv.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(data_dir / "wiki"))

    store = SQLiteStateStore(str(data_dir / "autoreiv.db"))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)
    registry, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=str(data_dir / "wiki"),
        skills_dir=str(data_dir / "skills"),
    )
    app = create_app(state_store=store, agent_registry=registry, tool_registry=tool_reg, wiki_path=str(data_dir / "wiki"))
    return TestClient(app), store, registry, data_dir


def test_matrix_rejects_out_of_range_or_invalid_max_concurrent_generations(tmp_path: Path, monkeypatch) -> None:
    """POST /api/settings/matrix must return HTTP 400 when max_concurrent_generations is outside 1..3 or invalid."""
    client, _store, _registry, _data_dir = _make_client(tmp_path, monkeypatch)

    for invalid_slots in (0, 4, -1, "four", True):
        res = client.post(
            "/api/settings/matrix",
            json={"default_model": "default", "max_concurrent_generations": invalid_slots},
        )
        assert res.status_code == 400, f"Expected 400 for max_concurrent_generations={invalid_slots!r}, got {res.status_code}"
        assert "max_concurrent_generations" in res.json().get("detail", "")

    for valid_slots in (1, 2, 3):
        res = client.post(
            "/api/settings/matrix",
            json={"default_model": "default", "max_concurrent_generations": valid_slots},
        )
        assert res.status_code == 200
        assert res.json()["matrix"]["max_concurrent_generations"] == valid_slots


def test_chat_stream_rejects_invalid_approval_mode(tmp_path: Path, monkeypatch) -> None:
    """POST /api/chat/stream must return HTTP 400 when approval_mode is an unrecognized string like 'auto'."""
    client, store, _registry, _data_dir = _make_client(tmp_path, monkeypatch)
    sess = store.create_session(agent_id="autoreiv", title="Approval Mode Test")

    for bad_mode in ("auto", "invalid", "yes", "always"):
        res = client.post(
            "/api/chat/stream",
            json={
                "agent_id": "autoreiv",
                "session_id": sess.id,
                "content": "hello",
                "approval_mode": bad_mode,
            },
        )
        assert res.status_code == 400, f"Expected 400 for approval_mode={bad_mode!r}, got {res.status_code}"
        assert "approval_mode" in str(res.json().get("detail", ""))


def test_reloaded_teach_card_reconciles_when_skill_removed_or_unticked(tmp_path: Path, monkeypatch) -> None:
    """GET /api/sessions/{id}/messages must revert adoption_state from 'adopted' to 'pending' when the skill is removed or unticked."""
    client, store, _registry, _data_dir = _make_client(tmp_path, monkeypatch)
    sess = store.create_session(agent_id="autoreiv", title="Teach Reconcile")

    proposal_payload = {
        "skill_id": "temp-lesson-723",
        "name": "Temp Lesson 723",
        "target_agent_id": "autoreiv",
        "adoption_state": "pending",
        "runbook_markdown": "---\nname: Temp Lesson 723\ndescription: Temporary lesson for reconciliation test.\n---\n\n# Temp Lesson 723\nFollow steps.\n",
    }
    msg_id = store.save_message(
        session_id=sess.id,
        agent_id="autoreiv",
        message=ChatMessage(role=Role.SKILL_PROPOSAL, content=json.dumps(proposal_payload), name="distill_skill"),
    )

    adopt_res = client.post(
        "/api/skills/adopt",
        json={
            "target_agent_id": "autoreiv",
            "skill_id": "temp-lesson-723",
            "runbook_markdown": proposal_payload["runbook_markdown"],
            "session_id": sess.id,
            "message_id": msg_id,
        },
    )
    assert adopt_res.status_code == 200

    msgs_after_adopt = client.get(f"/api/sessions/{sess.id}/messages").json()
    prop_after_adopt = json.loads(msgs_after_adopt[0]["content"])
    assert prop_after_adopt["adoption_state"] == "adopted"

    del_res = client.delete("/api/skills/user-skills/temp-lesson-723?confirm=true")
    assert del_res.status_code == 200

    msgs_after_delete = client.get(f"/api/sessions/{sess.id}/messages").json()
    prop_after_delete = json.loads(msgs_after_delete[0]["content"])
    assert prop_after_delete["adoption_state"] == "pending"


def test_scroll_setup_refreshes_sessions_on_drawer_open() -> None:
    """chat/scroll.js and chat.js wire onOpenSessionsDrawer so clicking #toggleSidebarBtn refreshes sessions."""
    scroll_js = Path("src/web/static/modules/studios/chat/scroll.js").read_text(encoding="utf-8")
    chat_js = Path("src/web/static/modules/studios/chat.js").read_text(encoding="utf-8")
    assert "onOpenSessionsDrawer" in scroll_js
    assert "onOpenSessionsDrawer" in chat_js
