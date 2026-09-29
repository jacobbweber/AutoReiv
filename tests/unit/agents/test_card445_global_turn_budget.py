"""CARD-445: global default turn budget 50 + one-time 10 -> 50 upgrade [REQ-445-001..008]."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError
from src.domain.kernel.models import DEFAULT_AGENT_MAX_TURNS, AgentProfile
from src.domain.settings.models import AgentCustomization
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

REPO = Path(__file__).resolve().parents[3]


def _store(tmp_path: Path) -> SQLiteStateStore:
    store = SQLiteStateStore(db_path=str(tmp_path / "card445.db"))
    store.initialize_db()
    return store


def _profile(agent_id: str, max_turns: int) -> AgentProfile:
    return AgentProfile(id=agent_id, name=agent_id.title(), description="d", system_prompt="p", max_turns=max_turns)


def _override(agent_id: str, max_turns: int) -> AgentCustomization:
    return AgentCustomization(agent_id=agent_id, max_turns=max_turns)


def _stored(store: SQLiteStateStore, table: str, key: str, agent_id: str):
    conn = sqlite3.connect(store.db_path)
    try:
        row = conn.execute(f"SELECT max_turns FROM {table} WHERE {key} = ?", (agent_id,)).fetchone()
    finally:
        conn.close()
    return None if row is None else row[0]


# --- REQ-445-001 / 002 / 003: one constant, default 50, range 1-1000 -----------------


def test_req_445_001_shared_constant_is_50_and_profile_uses_it():
    assert DEFAULT_AGENT_MAX_TURNS == 50
    assert AgentProfile.model_fields["max_turns"].default == DEFAULT_AGENT_MAX_TURNS
    assert AgentProfile(id="x", name="X", description="d", system_prompt="p").max_turns == 50


@pytest.mark.parametrize("value", [1, 1000])
def test_req_445_003_range_bounds_accepted(value):
    assert AgentProfile(id="x", name="X", description="d", system_prompt="p", max_turns=value).max_turns == value


@pytest.mark.parametrize("value", [0, 1001])
def test_req_445_003_out_of_range_rejected(value):
    with pytest.raises(ValidationError):
        AgentProfile(id="x", name="X", description="d", system_prompt="p", max_turns=value)


def test_req_445_001_guardrail_fallback_is_50_and_range_kept():
    base = {"id": "guard", "name": "Guard", "description": "d", "system_prompt": "You help people carefully."}
    assert AgentProfileGuardrail.validate(dict(base)).max_turns == 50
    for bad in (0, 1001):
        with pytest.raises(AgentValidationError):
            AgentProfileGuardrail.validate({**base, "max_turns": bad})


def test_req_445_001_agents_api_payload_default_is_50():
    from src.web.routers.agents import AgentProfilePayload

    assert AgentProfilePayload(name="n", description="d", system_prompt="p").max_turns == 50


def test_req_445_001_handoff_child_profile_fallback_uses_default():
    src = (REPO / "src/application/orchestration/handoff_engine.py").read_text(encoding="utf-8")
    assert 'getattr(target_profile, "max_turns", 10) or 10' not in src
    assert "DEFAULT_AGENT_MAX_TURNS" in src








# --- REQ-445-004 / 005 / 006: one-time upgrade -------------------------------------------


def _seed_live_like(store: SQLiteStateStore) -> None:
    for agent_id, turns in (("autoreiv", 10), ("direct", 10), ("developer", 25), ("tutor", 100)):
        store.save_custom_agent_profile(_profile(agent_id, turns))
    store.save_agent_override(_override("developer", 25))
    store.save_agent_override(_override("tutor", 100))
    store.save_agent_override(_override("ov-only", 10))












# --- REQ-445-007 / 008 + grep guards ------------------------------------------------------




LEGACY_TEN_PATTERNS = {
    "src/domain/kernel/models.py": [r"max_turns: int = Field\(default=10\b"],
    "src/domain/agents/guardrails.py": [r'payload\.get\("max_turns", 10\)'],
    "src/web/routers/agents.py": [r"max_turns: Optional\[int\] = 10\b"],
    "src/infrastructure/memory/repositories/settings.py": [r'r\["max_turns"\] or 10\b'],
    "src/application/skills/agent_builder_tools.py": [r'"max_turns": 10\b'],
    "src/infrastructure/memory/schema.py": [r"\n    max_turns INTEGER DEFAULT 10,"],
    "src/web/static/modules/studios/forge.js": [r"max_turns \|\| 10\b", r"\|\| 10,"],
    "src/web/templates/index.html": [r'id="forgeMaxTurnsInput"[^>]*value="10"'],
}


@pytest.mark.parametrize("rel", sorted(LEGACY_TEN_PATTERNS))
def test_req_445_001_no_literal_10_default_left(rel):
    text = (REPO / rel).read_text(encoding="utf-8")
    for pat in LEGACY_TEN_PATTERNS[rel]:
        assert not re.search(pat, text), f"{rel} still has legacy default: {pat}"


def test_req_445_001_agent_studio_default_matches_backend_constant():
    js = (REPO / "src/web/static/modules/studios/forge.js").read_text(encoding="utf-8")
    html = (REPO / "src/web/templates/index.html").read_text(encoding="utf-8")
    m = re.search(r"const DEFAULT_AGENT_MAX_TURNS = (\d+);", js)
    assert m and int(m.group(1)) == DEFAULT_AGENT_MAX_TURNS
    m2 = re.search(r'id="forgeMaxTurnsInput"[^>]*value="(\d+)"', html)
    assert m2 and int(m2.group(1)) == DEFAULT_AGENT_MAX_TURNS
