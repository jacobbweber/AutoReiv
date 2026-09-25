"""CARD-502: an adopted Teach skill is live on the next message and survives restart (REQ-502-001..008).

Real FastAPI app + SQLite on the per-test temp data folder (tests/conftest.py). A "restart" is a
second create_app on the same database and data folder, which re-runs platform pack promotion.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.domain.kernel.models import AgentOrigin, AgentProfile, AgentTone, ModelPurpose
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.platform_pack_promotion import list_pack_content_backups
from src.web.app import create_app

RUNBOOK = "---\nname: cite-sources\ndescription: Always cite the source C502\n---\n\n# Cite Sources\n\n1. Quote it\n"
RUNBOOK_V2 = "---\nname: cite-sources\ndescription: Always cite the source C502 v2\n---\n\n# Cite Sources\n\n1. Link it\n"


@pytest.fixture
def boot(tmp_path):
    db = os.environ["AUTOREIV_DB_PATH"]
    wiki = Path(os.environ["AUTOREIV_WIKI_PATH"])
    wiki.mkdir(parents=True, exist_ok=True)

    def _boot():
        store = SQLiteStateStore(db_path=db)
        store.initialize_db()
        app = create_app(state_store=store, wiki_path=str(wiki))
        return TestClient(app), store, app

    return _boot


def _data_root() -> Path:
    return Path(os.environ["AUTOREIV_DATA_DIR"])


def _skills(client, agent_id):
    res = client.get(f"/api/agents/{agent_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    return list((body.get("agent") or body).get("allowed_skill") or [])


def _adopt(client, agent_id="autoreiv", skill_id="cite-sources", runbook=RUNBOOK):
    return client.post(
        "/api/skills/adopt",
        json={"target_agent_id": agent_id, "skill_id": skill_id, "runbook_markdown": runbook},
    )


def _pack_json(agent_id):
    return json.loads((_data_root() / "packs" / agent_id / "pack.json").read_text(encoding="utf-8"))


def test_adopt_is_listed_on_next_read_and_in_next_turn_prompt(boot):
    """REQ-502-001/002/005/008."""
    client, store, app = boot()
    res = _adopt(client)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["active"] is True
    assert body["already_adopted"] is False
    assert body["resets_on_restart"] is False
    assert "cite-sources" in _skills(client, "autoreiv")
    agent = app.state.registry.get_agent("autoreiv")
    assert "cite-sources" in agent.allowed_skill
    prompt = app.state.kernel._build_effective_system_message(agent, None).content
    assert "Always cite the source C502" in prompt
    assert (_data_root() / "packs" / "autoreiv" / "skills" / "cite-sources" / "SKILL.md").is_file()
    assert not bool(getattr(store.get_agent_profile("autoreiv"), "user_modified", False))


def test_adopted_skill_survives_restart_with_keep_customizations_on(boot):
    """REQ-502-003 (Adopt)."""
    client, _store, _app = boot()
    assert _adopt(client).status_code == 200
    client2, _s2, app2 = boot()
    assert "cite-sources" in _skills(client2, "autoreiv")
    pj = _pack_json("autoreiv")
    assert "cite-sources" in pj["allowed_skill"]
    assert any((s.get("id") if isinstance(s, dict) else s) == "cite-sources" for s in pj.get("skills") or [])
    prompt = app2.state.kernel._build_effective_system_message(app2.state.registry.get_agent("autoreiv"), None).content
    assert "Always cite the source C502" in prompt


def test_agent_studio_extra_tick_survives_restart(boot):
    """REQ-502-003 (Agent Studio tick, D3)."""
    client, _store, _app = boot()
    tutor = client.get("/api/agents/tutor").json()
    tutor = tutor.get("agent") or tutor
    assert "build-agent-pack" not in tutor["allowed_skill"]
    put = client.put("/api/agents/tutor", json={**tutor, "allowed_skill": [*tutor["allowed_skill"], "build-agent-pack"]})
    assert put.status_code == 200, put.text
    assert "build-agent-pack" in _skills(client, "tutor")
    client2, _s2, _a2 = boot()
    assert "build-agent-pack" in _skills(client2, "tutor")


def test_keep_customizations_off_warns_and_restart_removes_but_keeps_file(boot):
    """REQ-502-004 / D4."""
    client, store, _app = boot()
    assert client.put("/api/settings/platform-pack-keep-customizations", json={"enabled": False}).status_code == 200
    res = _adopt(client)
    assert res.status_code == 200, res.text
    assert res.json()["resets_on_restart"] is True
    client2, store2, _a2 = boot()
    assert "cite-sources" not in _skills(client2, "autoreiv")
    assert (_data_root() / "packs" / "autoreiv" / "skills" / "cite-sources" / "SKILL.md").is_file()
    assert list_pack_content_backups(store2, "autoreiv"), "a backup is written before the reset"


def test_readopt_updates_one_entry_and_the_runbook(boot):
    """REQ-502-006 (a)."""
    client, _store, _app = boot()
    assert _adopt(client).json()["already_adopted"] is False
    second = _adopt(client, runbook=RUNBOOK_V2)
    assert second.status_code == 200, second.text
    assert second.json()["already_adopted"] is True
    assert _skills(client, "autoreiv").count("cite-sources") == 1
    text = (_data_root() / "packs" / "autoreiv" / "skills" / "cite-sources" / "SKILL.md").read_text(encoding="utf-8")
    assert "C502 v2" in text


def test_platform_skill_id_clash_is_refused(boot):
    """REQ-502-006 (b): 409, nothing changes."""
    client, _store, _app = boot()
    stock = _data_root() / "packs" / "autoreiv" / "skills" / "wiki-inbox" / "SKILL.md"
    before_text = stock.read_text(encoding="utf-8")
    before = _skills(client, "autoreiv")
    res = _adopt(client, skill_id="wiki-inbox")
    assert res.status_code == 409, res.text
    assert "already has a platform skill called wiki-inbox" in res.json()["detail"]
    assert stock.read_text(encoding="utf-8") == before_text
    assert _skills(client, "autoreiv") == before


def test_unknown_agent_is_404_and_creates_no_folder(boot):
    """REQ-502-007."""
    client, _store, _app = boot()
    res = _adopt(client, agent_id="nobody-c502")
    assert res.status_code == 404, res.text
    assert "nobody-c502" in res.json()["detail"]
    assert not (_data_root() / "packs" / "nobody-c502").exists()


def test_custom_agent_adopt_is_listed(boot):
    """D8: custom agents use the same save."""
    client, _store, app = boot()
    app.state.registry.register_custom_agent(AgentProfile(
        id="c502-helper", name="Helper", description="fixture", system_prompt="You help.",
        origin=AgentOrigin.CUSTOM, tone=AgentTone.DEFAULT, purpose=ModelPurpose.TASK_EXECUTION,
        allowed_skill=[], allowed_tool_names=[], show_in_chat=True,
    ))
    res = _adopt(client, agent_id="c502-helper")
    assert res.status_code == 200, res.text
    assert res.json()["active"] is True
    assert "cite-sources" in app.state.registry.get_agent("c502-helper").allowed_skill
