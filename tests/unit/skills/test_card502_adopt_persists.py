"""CARD-502: an adopted Teach skill is live on the next message and survives restart (REQ-502-001..008).

Real FastAPI app + SQLite on the per-test temp data folder (tests/conftest.py). A "restart" is a
second create_app on the same database and data folder, which reloads platform/ agents and skills
plus the user copies in the data folder (CARD-570 layout: <data>/skills/<id>/SKILL.md, <data>/agents/<id>.md).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.domain.kernel.models import AgentOrigin, AgentProfile, AgentTone, ModelPurpose
from src.infrastructure.content.store import get_store
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

pytestmark = pytest.mark.slow

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


def _user_skill(skill_id):
    return _data_root() / "skills" / skill_id / "SKILL.md"


def _user_agent(agent_id):
    return _data_root() / "agents" / f"{agent_id}.md"


def test_adopt_is_listed_on_next_read_and_in_next_turn_prompt(boot):
    """REQ-502-001/002/005/008."""
    client, _store, app = boot()
    res = _adopt(client)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["active"] is True
    assert body["already_adopted"] is False
    assert "cite-sources" in _skills(client, "autoreiv")
    agent = app.state.registry.get_agent("autoreiv")
    assert "cite-sources" in agent.allowed_skill
    prompt = app.state.kernel._build_effective_system_message(agent, None).content
    assert "Always cite the source C502" in prompt
    assert _user_skill("cite-sources").is_file()
    # CARD-570: Adopt saves the agent user copy the same way an Agent Studio save does
    assert "cite-sources" in _user_agent("autoreiv").read_text(encoding="utf-8")


def test_adopted_skill_survives_restart_with_keep_customizations_on(boot):
    """REQ-502-003 (Adopt)."""
    client, _store, _app = boot()
    assert _adopt(client).status_code == 200
    client2, _s2, app2 = boot()
    assert "cite-sources" in _skills(client2, "autoreiv")
    assert _user_skill("cite-sources").is_file()
    assert "cite-sources" in _user_agent("autoreiv").read_text(encoding="utf-8")
    prompt = app2.state.kernel._build_effective_system_message(app2.state.registry.get_agent("autoreiv"), None).content
    assert "Always cite the source C502" in prompt


def test_readopt_updates_one_entry_and_the_runbook(boot):
    """REQ-502-006 (a)."""
    client, _store, _app = boot()
    assert _adopt(client).json()["already_adopted"] is False
    second = _adopt(client, runbook=RUNBOOK_V2)
    assert second.status_code == 200, second.text
    assert second.json()["already_adopted"] is True
    assert _skills(client, "autoreiv").count("cite-sources") == 1
    text = _user_skill("cite-sources").read_text(encoding="utf-8")
    assert "C502 v2" in text


def test_platform_skill_id_clash_is_refused(boot):
    """REQ-502-006 (b): 409, nothing changes."""
    client, _store, _app = boot()
    stock = get_store().skills.shipped_path("wiki-inbox")
    assert stock.is_file()
    before_text = stock.read_text(encoding="utf-8")
    before = _skills(client, "autoreiv")
    res = _adopt(client, skill_id="wiki-inbox")
    assert res.status_code == 409, res.text
    assert "already has a platform skill called wiki-inbox" in res.json()["detail"]
    assert stock.read_text(encoding="utf-8") == before_text
    assert _skills(client, "autoreiv") == before
    assert not _user_skill("wiki-inbox").exists()


def test_unknown_agent_is_404_and_creates_no_folder(boot):
    """REQ-502-007."""
    client, _store, _app = boot()
    res = _adopt(client, agent_id="nobody-c502")
    assert res.status_code == 404, res.text
    assert "nobody-c502" in res.json()["detail"]
    assert not _user_agent("nobody-c502").exists()
    assert not _user_skill("cite-sources").exists()


def test_custom_agent_adopt_is_listed(boot):
    """D8: custom agents use the same save."""
    client, _store, app = boot()
    app.state.registry.register_custom_agent(AgentProfile(
        id="c502-helper", name="Helper", description="fixture", system_prompt="You help.",
        origin=AgentOrigin.CUSTOM, tone=AgentTone.DEFAULT, purpose=ModelPurpose.TASK_EXECUTION,
        allowed_skill=[], show_in_chat=True,
    ))
    res = _adopt(client, agent_id="c502-helper")
    assert res.status_code == 200, res.text
    assert res.json()["active"] is True
    assert "cite-sources" in app.state.registry.get_agent("c502-helper").allowed_skill
