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
from src.infrastructure.agents.max_turns_upgrade import (
    AGENT_MAX_TURNS_DEFAULT_50_SETTING,
    apply_default_max_turns_upgrade,
)
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


@pytest.mark.asyncio
async def test_req_445_001_agent_builder_scaffold_uses_default():
    from src.application.skills.agent_builder_tools import AgentBuilderTools

    tools = AgentBuilderTools.__new__(AgentBuilderTools)
    spec = await tools.propose_agent_specification(role="Log Reader", objective="read logs")
    assert spec["max_turns"] == DEFAULT_AGENT_MAX_TURNS


def test_req_445_001_handoff_child_profile_fallback_uses_default():
    src = (REPO / "src/application/orchestration/handoff_engine.py").read_text(encoding="utf-8")
    assert 'getattr(target_profile, "max_turns", 10) or 10' not in src
    assert "DEFAULT_AGENT_MAX_TURNS" in src


def test_req_445_002_repository_null_max_turns_falls_back_to_50(tmp_path: Path):
    store = _store(tmp_path)
    store.save_custom_agent_profile(_profile("nullish", 30))
    conn = sqlite3.connect(store.db_path)
    conn.execute("UPDATE custom_agents SET max_turns = NULL WHERE id = 'nullish'")
    conn.commit()
    conn.close()
    got = store.get_agent_profile("nullish")
    assert got is not None and got.max_turns == 50
    assert {p.id: p.max_turns for p in store.list_custom_agent_profiles()}["nullish"] == 50


def test_req_445_002_fresh_schema_default_is_50(tmp_path: Path):
    store = _store(tmp_path)
    conn = sqlite3.connect(store.db_path)
    cols = {r[1]: r[4] for r in conn.execute("PRAGMA table_info(custom_agents)").fetchall()}
    conn.close()
    assert cols["max_turns"] == str(DEFAULT_AGENT_MAX_TURNS)


def test_req_445_002_legacy_schema_new_rows_still_get_50(tmp_path: Path):
    """Existing DBs keep the old column DEFAULT 10, but every insert binds max_turns explicitly."""
    store = _store(tmp_path)
    store.save_custom_agent_profile(AgentProfile(id="fresh", name="Fresh", description="d", system_prompt="p"))
    assert _stored(store, "custom_agents", "id", "fresh") == 50


# --- REQ-445-004 / 005 / 006: one-time upgrade -------------------------------------------


def _seed_live_like(store: SQLiteStateStore) -> None:
    for agent_id, turns in (("autoreiv", 10), ("direct", 10), ("developer", 25), ("tutor", 100)):
        store.save_custom_agent_profile(_profile(agent_id, turns))
    store.save_agent_override(_override("developer", 25))
    store.save_agent_override(_override("tutor", 100))
    store.save_agent_override(_override("ov-only", 10))


def test_req_445_004_upgrade_raises_exactly_10_and_records_key(tmp_path: Path):
    store = _store(tmp_path)
    _seed_live_like(store)

    record = apply_default_max_turns_upgrade(store)

    assert record is not None
    assert record["raised"] == ["autoreiv", "direct", "ov-only"]
    assert record["from"] == 10 and record["to"] == 50
    assert record["applied_at"]
    assert store.get_setting(AGENT_MAX_TURNS_DEFAULT_50_SETTING) == record
    assert _stored(store, "custom_agents", "id", "autoreiv") == 50
    assert _stored(store, "custom_agents", "id", "direct") == 50
    assert _stored(store, "custom_agents", "id", "developer") == 25
    assert _stored(store, "custom_agents", "id", "tutor") == 100
    assert _stored(store, "agent_overrides", "agent_id", "developer") == 25
    assert _stored(store, "agent_overrides", "agent_id", "tutor") == 100
    assert _stored(store, "agent_overrides", "agent_id", "ov-only") == 50


def test_req_445_004_upgrade_does_not_lock_packs(tmp_path: Path):
    """CARD-449: max_turns is a setting, not a lock - the upgrade must not set user_modified."""
    store = _store(tmp_path)
    _seed_live_like(store)
    apply_default_max_turns_upgrade(store)
    assert store.get_agent_profile("autoreiv").user_modified is False
    assert store.get_agent_profile("direct").user_modified is False


def test_req_445_005_upgrade_runs_once_even_if_10_is_saved_later(tmp_path: Path):
    store = _store(tmp_path)
    _seed_live_like(store)
    first = apply_default_max_turns_upgrade(store)
    store.save_custom_agent_profile(_profile("autoreiv", 10))  # operator picks 10 on purpose

    assert apply_default_max_turns_upgrade(store) is None
    assert apply_default_max_turns_upgrade(store) is None  # double bootstrap (CARD-459)
    assert _stored(store, "custom_agents", "id", "autoreiv") == 10
    assert store.get_setting(AGENT_MAX_TURNS_DEFAULT_50_SETTING) == first


def test_req_445_004_upgrade_skips_stores_without_support():
    class _Bare:
        def get_setting(self, key, default=None):
            return default

    assert apply_default_max_turns_upgrade(_Bare()) is None
    assert apply_default_max_turns_upgrade(None) is None


def test_req_445_004_006_startup_install_applies_upgrade_and_keeps_operator_values(tmp_path: Path, monkeypatch):
    """Boot path: install_platform_agent_packs runs the upgrade after promotion; 25/100 survive sync."""
    from src.infrastructure.agents.registry import BuiltinAgentRegistry
    from src.infrastructure.data import resolver as resolver_mod
    from src.infrastructure.skills.platform_packs import install_platform_agent_packs

    monkeypatch.setattr(resolver_mod, "repo_root", lambda: REPO)
    store = _store(tmp_path)
    _seed_live_like(store)
    registry = BuiltinAgentRegistry(profiles=[], state_store=store)
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    install_platform_agent_packs(data_dir, registry, None, checkout_root=REPO)

    assert registry.get_agent("autoreiv").max_turns == 50
    assert registry.get_agent("direct").max_turns == 50
    assert registry.get_agent("developer").max_turns == 25
    assert registry.get_agent("tutor").max_turns == 100
    assert store.get_setting(AGENT_MAX_TURNS_DEFAULT_50_SETTING)["raised"][:2] == ["autoreiv", "direct"]

    # Second boot: nothing changes
    install_platform_agent_packs(data_dir, registry, None, checkout_root=REPO)
    assert registry.get_agent("tutor").max_turns == 100
    assert registry.get_agent("developer").max_turns == 25
    assert registry.get_agent("autoreiv").max_turns == 50


# --- REQ-445-007 / 008 + grep guards ------------------------------------------------------


def test_req_445_007_flashcard_skill_states_no_numeric_default_budget():
    text = (REPO / "platform-packs/tutor/skills/flashcard-turn/SKILL.md").read_text(encoding="utf-8")
    assert not re.search(r"default (turn )?budget of \d+", text, re.IGNORECASE)


def test_req_445_008_pack_manifest_has_no_max_turns_field():
    from src.application.agent_packs.schema import AgentPackManifest

    assert "max_turns" not in AgentPackManifest.model_fields


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
