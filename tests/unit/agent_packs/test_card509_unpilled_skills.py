"""CARD-509: an Agent Studio Save must not turn off skills Studio does not show (D1-D5).

Real FastAPI app + SQLite on the per-test temp data folder (tests/conftest.py). A "restart" is a
second create_app on the same database. Jacob's real AppData is never touched.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.platform_pack_promotion import PLATFORM_OPERATOR_DISABLED_SKILLS_SETTING
from src.web.app import create_app


@pytest.fixture
def boot():
    db = os.environ["AUTOREIV_DB_PATH"]
    wiki = Path(os.environ["AUTOREIV_WIKI_PATH"])
    wiki.mkdir(parents=True, exist_ok=True)

    def _boot():
        store = SQLiteStateStore(db_path=db)
        store.initialize_db()
        app = create_app(state_store=store, wiki_path=str(wiki))
        return TestClient(app), store, app

    return _boot


def _agent(client, agent_id):
    body = client.get(f"/api/agents/{agent_id}").json()
    return body.get("agent") or body


def _pill_ids(agent):
    return [s["id"] for s in agent.get("pack_skills") or []]


def _disabled(store, agent_id):
    return list((store.get_setting(PLATFORM_OPERATOR_DISABLED_SKILLS_SETTING) or {}).get(agent_id) or [])


def _put(client, agent_id, **changes):
    agent = _agent(client, agent_id)
    payload = {**agent, "system_prompt": (agent["system_prompt"] or "").strip(), **changes}
    res = client.put(f"/api/agents/{agent_id}", json=payload)
    assert res.status_code == 200, res.text
    return res


def test_every_allowed_or_shipped_skill_with_a_runbook_gets_a_pill(boot):
    """D3: coding on AutoReiv and build-agent-pack on Developer are shown; no duplicates of catalog pills."""
    client, _store, _app = boot()
    auto = _agent(client, "autoreiv")
    dev = _agent(client, "developer")
    assert "coding" in _pill_ids(auto)
    assert "build-agent-pack" in _pill_ids(dev)
    for agent in (auto, dev):
        ids = _pill_ids(agent)
        assert len(ids) == len(set(ids))
        assert "wiki-inbox" not in ids  # platform skills come from the catalog, not pack_skills
    coding = next(s for s in auto["pack_skills"] if s["id"] == "coding")
    assert coding["name"] == "Repository Code & Files"


def test_scalar_save_with_the_full_list_keeps_coding_and_records_nothing(boot):
    """REQ-509: Max-Turns-only save (what Studio now sends) keeps coding; nothing recorded as disabled."""
    client, store, _app = boot()
    _put(client, "autoreiv", max_turns=51)
    assert "coding" in _agent(client, "autoreiv")["allowed_skill"]
    assert "coding" not in _disabled(store, "autoreiv")


def test_skill_studio_could_not_show_is_never_recorded_disabled(boot):
    """D2: a save that leaves out a skill with no pill (no SKILL.md, not a platform skill) records nothing."""
    client, store, app = boot()
    prof = store.get_agent_profile("autoreiv")
    prof.allowed_skill = list(prof.allowed_skill) + ["c509-ghost-skill"]
    store.save_custom_agent_profile(prof)
    app.state.registry.register_custom_agent(prof)
    agent = _agent(client, "autoreiv")
    assert "c509-ghost-skill" not in _pill_ids(agent)
    _put(client, "autoreiv", allowed_skill=[s for s in agent["allowed_skill"] if s != "c509-ghost-skill"], max_turns=52)
    assert "c509-ghost-skill" not in _disabled(store, "autoreiv")


def test_a_skill_switched_off_stays_off_after_a_second_save_and_restart(boot):
    """D2: switching a shown skill off is recorded, and a later unrelated save does not forget it."""
    client, store, _app = boot()
    skills = [s for s in _agent(client, "autoreiv")["allowed_skill"] if s != "coding"]
    _put(client, "autoreiv", allowed_skill=skills)
    assert "coding" in _disabled(store, "autoreiv")
    _put(client, "autoreiv", max_turns=53)
    assert "coding" in _disabled(store, "autoreiv")
    client2, _store2, _app2 = boot()
    assert "coding" not in _agent(client2, "autoreiv")["allowed_skill"]


def test_locked_developer_missing_build_agent_pack_is_not_auto_repaired(boot):
    """D4 control: a locked Developer without build-agent-pack keeps its list on restart; the pill still shows."""
    client, store, app = boot()
    agent = _agent(client, "developer")
    _put(
        client,
        "developer",
        allowed_skill=[s for s in agent["allowed_skill"] if s != "build-agent-pack"],
        system_prompt=agent["system_prompt"].strip() + "\nAlways follow SOLID and DRY principles.",
    )
    # Jacob's install already had the one-time CARD-425 grants recorded, so none re-fire here
    from src.infrastructure.skills.platform_packs import (
        USER_MODIFIED_ADDITIVE_SKILL_GRANTS,
        USER_MODIFIED_SKILL_GRANT_SETTING,
    )

    store.set_setting(USER_MODIFIED_SKILL_GRANT_SETTING, {"developer": list(USER_MODIFIED_ADDITIVE_SKILL_GRANTS["developer"])})
    client2, store2, _app2 = boot()
    dev = _agent(client2, "developer")
    assert "build-agent-pack" not in dev["allowed_skill"]
    assert "build-agent-pack" in _pill_ids(dev)
