"""CARD-539 REQ-539-005/-006/-011: Studio saves skills only; stale saves are refused; routing text is generated.

Real FastAPI app + SQLite on the per-test temp data folder (tests/conftest.py).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.application.agent_packs.allowed_tools import resolve_allowed_tools
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def boot():
    db = os.environ["AUTOREIV_DB_PATH"]
    wiki = Path(os.environ["AUTOREIV_WIKI_PATH"])
    wiki.mkdir(parents=True, exist_ok=True)
    store = SQLiteStateStore(db_path=db)
    store.initialize_db()
    app = create_app(state_store=store, wiki_path=str(wiki))
    return TestClient(app), store, app


def _agent(client, agent_id):
    body = client.get(f"/api/agents/{agent_id}").json()
    return body.get("agent") or body


def test_put_ignores_legacy_tool_lists_and_get_shows_derived_tools(boot):
    client, _store, app = boot
    agent = _agent(client, "autoreiv")
    assert agent["skills_version"]
    payload = {**agent, "allowed_tool_names": ["execute_code", "get_weather"], "pack_tool_names": ["execute_code"],
               "expected_skills_version": agent["skills_version"]}
    res = client.put("/api/agents/autoreiv", json=payload)
    assert res.status_code == 200, res.text
    after = _agent(client, "autoreiv")
    profile = app.state.registry.get_agent("autoreiv")
    assert "get_weather" not in after["allowed_tool_names"]
    assert set(after["allowed_tool_names"]) == set(resolve_allowed_tools(profile).names)


def test_stale_skills_save_is_refused(boot):
    client, _store, _app = boot
    agent = _agent(client, "autoreiv")
    payload = {**agent, "allowed_skill": [], "expected_skills_version": "stale-version"}
    res = client.put("/api/agents/autoreiv", json=payload)
    assert res.status_code == 409
    assert _agent(client, "autoreiv")["allowed_skill"] == agent["allowed_skill"]


def test_platform_prompts_hand_off_instead_of_refusing():
    from src.domain.agents.good_agent_instructions import render_good_agent_instructions

    for pack in (ROOT / "platform-packs").glob("*/pack.json"):
        text = json.dumps(json.loads(pack.read_text("utf-8")))
        assert "Refuse requests outside" not in text, pack
    rendered = render_good_agent_instructions(name="Notes", role="notes", domain_focus="wiki notes")
    assert "Refuse" not in rendered and "Ask Developer" in rendered


def test_domain_and_routing_text_come_from_ticked_skills():
    from src.application.agent_packs.allowed_tools import domain_line, routing_summary
    from src.domain.kernel.models import AgentProfile

    agent = AgentProfile(id="notes", name="Notes", description="d", system_prompt="p",
                         allowed_skill=["wiki-knowledge", "sqlite-storage"])
    line = domain_line(agent)
    assert "Notes" in line and "wiki" in line.lower()
    summary = routing_summary(agent)
    assert 0 < len(summary) <= 160 and "wiki" in summary.lower()
    assert "wiki_note_search" not in summary


def test_directory_cards_route_by_skills_not_tools():
    from src.application.orchestration.directory_service import AgentDirectoryService
    from src.domain.kernel.models import AgentProfile

    agent = AgentProfile(id="notes", name="Notes", description="d", system_prompt="p",
                         allowed_skill=["wiki-knowledge"], allowed_tool_names=["execute_code"])

    class _Reg:
        def list_agents(self):
            return [agent]

    card = AgentDirectoryService(agent_registry=_Reg(), state_store=object()).get_agent_card("notes")
    text = card.model_dump_json()
    assert "execute_code" not in text and "wiki_note_search" not in text
    assert "wiki-knowledge" in text
