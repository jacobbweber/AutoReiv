"""CARD-228 Progressive SKILL.md disclosure [REQ-PSKILL-001..005].

Resolve = skill metadata only (id, title, risk, HITL).
Bind = one body when phase selects skill.
Dump-all bodies at resolve forbidden.
Chat still mounts ticked tool schemas every turn (AGENTS.md invariant).
"""

from __future__ import annotations

import inspect
import os
import tempfile
from pathlib import Path

import pytest

from src.application.capabilities.progressive_skills import (
    FORBIDDEN_DUMP_SKILL_BODY_ATTRS,
    SKILL_BODY_PAYLOAD_KEYS,
    entry_to_resolve_view,
    skill_metadata_view,
)
from src.application.capabilities.resolver import (
    CapabilityCatalogResolver,
    ResolveResult,
)
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.skills.user_catalog import UserSkillCatalog
from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    RiskLevel,
)
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.repositories.capability_catalog import (
    CapabilityCatalogRepository,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.fixture
def store(temp_db_path):
    return SQLiteStateStore(db_path=temp_db_path)


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    root = tmp_path / "skills"
    pack = root / "platform-health"
    pack.mkdir(parents=True)
    (pack / "SKILL.md").write_text(
        "---\n"
        "name: platform-health\n"
        "description: Host telemetry and health checks.\n"
        "---\n\n"
        "## Overview\n"
        "FULL_RUNBOOK_BODY_MARKER_DO_NOT_DUMP_AT_RESOLVE\n\n"
        "## Tools\n"
        "Use host_health.\n\n"
        "## Order\n"
        "1. Check\n2. Report\n\n"
        "## Pitfalls\n"
        "Do not skip HITL on high risk.\n\n"
        "## Done-when\n"
        "Health report written.\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture
def resolver(store):
    return CapabilityCatalogResolver(CapabilityCatalogRepository(store))


@pytest.fixture
def catalog(skills_dir):
    return UserSkillCatalog(skills_dir=skills_dir)


@pytest.fixture
def orch(store, resolver, catalog, tmp_path):
    return JobPhaseOrchestrator(
        store,
        capability_resolver=resolver,
        data_dir=str(tmp_path),
        skill_catalog=catalog,
    )


def _seed_with_body_in_metadata(resolver: CapabilityCatalogResolver) -> None:
    """Simulate theatre: someone stuffed SKILL.md body into capability metadata."""
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="skill.platform-health",
            kind=CapabilityKind.SKILL,
            name="platform-health",
            summary="Host telemetry and health",
            keywords=["health", "sre", "telemetry", "execute"],
            roles=["sre"],
            risk_level=RiskLevel.HIGH,
            requires_hitl=True,
            metadata={
                "pack_id": "platform-health",
                "instructions": "FULL_RUNBOOK_BODY_MARKER_DO_NOT_DUMP_AT_RESOLVE\n" * 20,
                "body": "FULL_RUNBOOK_BODY_MARKER_DO_NOT_DUMP_AT_RESOLVE",
                "content": "FULL_RUNBOOK_BODY_MARKER_DO_NOT_DUMP_AT_RESOLVE",
            },
        )
    )
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.wiki_note_search",
            kind=CapabilityKind.TOOL,
            name="wiki_note_search",
            summary="Search wiki notes",
            keywords=["wiki", "search", "notes"],
            roles=["librarian"],
        )
    )


def test_req_pskill_001_resolve_returns_skill_metadata_only(resolver):
    """Resolve skill matches: id/title/risk/HITL only — no SKILL.md body [REQ-PSKILL-001]."""
    _seed_with_body_in_metadata(resolver)
    result = resolver.resolve("health execute telemetry", role="sre")
    payload = result.as_dict()
    assert payload.get("subset_only") is True
    assert payload.get("skill_bodies_omitted") is True

    skill_rows = [
        m for m in payload["matched"] if m.get("kind") == "skill" or str(m.get("id", "")).startswith("skill.")
    ]
    assert skill_rows, "expected at least one skill match"
    for row in skill_rows:
        assert set(row.keys()) >= {"id", "title", "risk", "requires_hitl"}
        assert "instructions" not in row
        assert "body" not in row
        assert "content" not in row
        blob = str(row)
        assert "FULL_RUNBOOK_BODY_MARKER_DO_NOT_DUMP_AT_RESOLVE" not in blob
        assert row.get("metadata_only") is True
        assert row.get("body_loaded") is False
        # metadata must not re-smuggle body keys
        meta = row.get("metadata") or {}
        for key in SKILL_BODY_PAYLOAD_KEYS:
            assert key not in meta


def test_req_pskill_002_bind_loads_one_body_on_phase_select(orch, resolver, catalog):
    """Phase bind/select loads exactly one SKILL.md body [REQ-PSKILL-002]."""
    _seed_with_body_in_metadata(resolver)
    job = orch.create_job_from_catalog_resolve(
        intent="health execute telemetry",
        session_id="sess_pskill",
        agent_id="assistant",
        role="sre",
    )
    phases = orch._store.list_phases_for_job(job.id)
    phase = phases[0]
    orch.start_phase(phase.id)

    bound = orch.bind_skill_for_phase(phase.id, "skill.platform-health")
    assert bound["success"] is True
    assert bound["event"] == "skill_bound"
    assert bound["skill_id"] == "skill.platform-health"
    assert "FULL_RUNBOOK_BODY_MARKER_DO_NOT_DUMP_AT_RESOLVE" in (bound.get("body") or "")
    assert bound.get("body_loaded") is True

    # Resolve still has no bodies after bind.
    again = resolver.resolve("health execute telemetry", role="sre").as_dict()
    assert "FULL_RUNBOOK_BODY_MARKER_DO_NOT_DUMP_AT_RESOLVE" not in str(again)

    # Standing journey records one skill_bound event.
    events = orch._store.list_standing_journey_events(job.id)
    kinds = [e.get("kind") for e in events]
    assert kinds.count("skill_bound") == 1


def test_req_pskill_003_dump_all_skill_bodies_forbidden():
    """Dump-all skill bodies at resolve must not exist [REQ-PSKILL-003]."""
    for attr in FORBIDDEN_DUMP_SKILL_BODY_ATTRS:
        assert not hasattr(CapabilityCatalogResolver, attr)
        assert not hasattr(ResolveResult, attr)
        assert not hasattr(JobPhaseOrchestrator, attr)


def test_req_pskill_004_chat_still_lists_ticked_tool_schemas():
    """Progressive skills must NOT hide ticked tool schemas on Chat turns [REQ-PSKILL-004]."""
    from src.application.kernel.tool_registry import ScopedToolRegistry

    reg = ScopedToolRegistry()
    reg.register_tool(
        name="wiki_note_search",
        description="Search wiki",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        handler=lambda **kwargs: {"ok": True},
    )
    reg.register_tool(
        name="skill_view",
        description="Open a runbook",
        parameters={
            "type": "object",
            "properties": {"pack_id": {"type": "string"}},
            "required": ["pack_id"],
        },
        handler=lambda **kwargs: {"ok": True},
    )
    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Test assistant",
        system_prompt="test",
        allowed_tool_names=["wiki_note_search", "skill_view"],
        allowed_skill=["platform-health"],
    )
    tools = reg.get_tools_for_agent(agent)
    names = {t.name for t in tools}
    assert "wiki_note_search" in names
    assert "skill_view" in names
    for t in tools:
        assert isinstance(t.parameters, dict)
        assert t.parameters.get("type") == "object"
        assert "properties" in t.parameters

    # Source invariant: chat stream still mounts tools via get_tools_for_agent.
    from src.web.routers import chat as chat_mod

    src = inspect.getsource(chat_mod)
    assert "get_tools_for_agent" in src


def test_req_pskill_005_phase_start_binds_one_not_dump_all(orch, resolver):
    """start_phase progressive bind selects one skill body — never dump-all [REQ-PSKILL-005]."""
    _seed_with_body_in_metadata(resolver)
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="skill.other-runbook",
            kind=CapabilityKind.SKILL,
            name="other-runbook",
            summary="Another runbook",
            keywords=["health", "execute", "other"],
            roles=["sre"],
            metadata={"instructions": "SECOND_BODY_SHOULD_NOT_AUTO_DUMP"},
        )
    )
    job = orch.create_job_from_catalog_resolve(
        intent="health execute telemetry",
        session_id="sess_bind_one",
        agent_id="assistant",
        role="sre",
    )
    phases = orch._store.list_phases_for_job(job.id)
    phase = phases[0]
    results = orch.bind_matched_skill_on_phase_start(phase.id)
    assert len(results) == 1
    assert results[0]["success"] is True
    assert results[0]["event"] == "skill_bound"
    # Only one body loaded — not both skills' bodies.
    bodies = [r.get("body") or "" for r in results]
    assert sum(1 for b in bodies if b) == 1


def test_entry_to_resolve_view_strips_body_keys():
    entry = CapabilityIndexEntry.self_authored(
        id="skill.x",
        kind=CapabilityKind.SKILL,
        name="X",
        risk_level=RiskLevel.MEDIUM,
        requires_hitl=False,
        metadata={"instructions": "SECRET_BODY", "pack_id": "x"},
    )
    view = entry_to_resolve_view(entry)
    assert view["id"] == "skill.x"
    assert view["title"] == "X"
    assert "SECRET_BODY" not in str(view)
    meta = skill_metadata_view(entry)
    assert meta["risk"] == "medium"
    assert meta["requires_hitl"] is False
