"""CARD-500: /api/skills/distill takes the page's exact payload and refuses non-reply ids (REQ-500-001, REQ-500-003)."""

import json

import pytest
from fastapi.testclient import TestClient

from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.data.resolver import DataDirPaths
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

# The exact body chat/teach_modal.js builds (asserted on the page side by teach_distill_contract_500.test.js).
PAGE_BODY_KEYS = ("session_id", "message_id", "guidance")


@pytest.fixture
def env(tmp_path):
    store = SQLiteStateStore(str(tmp_path / "t.db"))
    store.initialize_db()
    data_dir = tmp_path / "data"
    (data_dir / "packs" / "autoreiv").mkdir(parents=True)
    (data_dir / "packs" / "autoreiv" / "pack.json").write_text(json.dumps({"id": "autoreiv", "allowed_skill": []}), encoding="utf-8")
    app = create_app(state_store=store)
    app.state.gateway = None  # no model: heuristic path, remedy echoes the guidance
    app.state.data_dir_paths = DataDirPaths(
        root=data_dir, db_path=tmp_path / "t.db", wiki_path=tmp_path / "wiki", skills_path=tmp_path / "skills",
        agents_path=tmp_path / "agents", job_templates_path=tmp_path / "templates",
    )
    sess = store.create_session(agent_id="autoreiv", title="t")
    user_id = store.save_message(sess.id, "autoreiv", ChatMessage(role=Role.USER, content="what is 2+2"))
    reply_id = store.save_message(sess.id, "autoreiv", ChatMessage(role=Role.ASSISTANT, content="5"))
    return TestClient(app), store, sess.id, user_id, reply_id


def test_page_payload_guidance_reaches_the_distiller(env, monkeypatch):
    """REQ-500-001 / D1: the page's body shape delivers the typed lesson; no alias needed."""
    client, _, sid, _, reply_id = env
    seen = {}
    from src.application.skills import distillation_service as ds

    real = ds.SkillDistillationService.distill_turn

    async def spy(self, session_id, message_id, guidance=None):
        seen.update(session_id=session_id, message_id=message_id, guidance=guidance)
        return await real(self, session_id=session_id, message_id=message_id, guidance=guidance)

    monkeypatch.setattr(ds.SkillDistillationService, "distill_turn", spy)
    body = dict(zip(PAGE_BODY_KEYS, (sid, reply_id, "always check arithmetic")))
    res = client.post("/api/skills/distill", json=body)
    assert res.status_code == 200, res.text
    assert seen == {"session_id": sid, "message_id": reply_id, "guidance": "always check arithmetic"}
    assert res.json()["plain_summary"]["remedy"] == "always check arithmetic"


@pytest.mark.parametrize("which", ["user_message", "unknown_id", "other_session"])
def test_distill_refuses_an_id_that_is_not_a_reply_in_this_chat(env, which):
    """REQ-500-003 / D4: 404 with a plain reason; no fallback turn, no proposal saved."""
    client, store, sid, user_id, _ = env
    if which == "user_message":
        mid = user_id
    elif which == "unknown_id":
        mid = "no-such-message"
    else:
        other = store.create_session(agent_id="autoreiv", title="other")
        store.save_message(other.id, "autoreiv", ChatMessage(role=Role.USER, content="hi"))
        mid = store.save_message(other.id, "autoreiv", ChatMessage(role=Role.ASSISTANT, content="hello"))
    before = len(store.get_messages(sid))
    res = client.post("/api/skills/distill", json={"session_id": sid, "message_id": mid, "guidance": "x"})
    assert res.status_code == 404, res.text
    detail = res.json()["detail"]
    assert isinstance(detail, str) and "reply" in detail.lower()
    assert len(store.get_messages(sid)) == before
