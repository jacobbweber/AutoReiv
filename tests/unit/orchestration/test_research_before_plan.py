"""CARD-231 Standing research-before-plan on capability gap only [REQ-RESEARCH-001..005].

Thin/gap → Research phase before Formulate/Execute.
Sufficient → skip research (Formulate/Execute only).
Research writes memory.db + catalog-gap proposals; never trusted skill/tool writes.
Checkpoint persists research_inserted + reason; journey surfaces research span.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.observability.standing_journey import build_standing_journey
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.research_before_plan import (
    SUFFICIENT_MATCH_MIN,
    assess_catalog_match,
    run_standing_research,
)
from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    TrustTier,
)
from src.domain.orchestration.models import HandoffPacket
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
def resolver(store):
    return CapabilityCatalogResolver(CapabilityCatalogRepository(store))


@pytest.fixture
def orch(store, resolver):
    return JobPhaseOrchestrator(store, capability_resolver=resolver)


def _seed_rich(resolver: CapabilityCatalogResolver) -> None:
    """Enough matches to cover wiki + health + handoff → sufficient."""
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.wiki_note_search",
            kind=CapabilityKind.TOOL,
            name="wiki_note_search",
            summary="Search wiki notes",
            keywords=["wiki", "search", "notes", "research", "inventory"],
            roles=["assistant"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.assistant",
            kind=CapabilityKind.AGENT,
            name="Assistant",
            summary="Day-to-day coordinator handoff",
            keywords=["assistant", "handoff", "coordinate", "execute"],
            roles=["assistant"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.health_probe",
            kind=CapabilityKind.TOOL,
            name="health_probe",
            summary="Probe HTTP health endpoints",
            keywords=["health", "probe", "http", "200", "verify"],
            roles=["assistant"],
        )
    )


def _seed_thin_one(resolver: CapabilityCatalogResolver) -> None:
    """Single weak match → below threshold."""
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.wiki_note_search",
            kind=CapabilityKind.TOOL,
            name="wiki_note_search",
            summary="Search wiki notes",
            keywords=["wiki", "search", "notes"],
            roles=["assistant"],
        )
    )


def _packet(goal: str = "g", facts=None) -> HandoffPacket:
    return HandoffPacket(
        goal=goal,
        facts=list(facts or ["ok"]),
        constraints=[],
        done_when="done",
        budget={},
    )


# --- Heuristic unit ---------------------------------------------------------


def test_heuristic_empty_matched_ids_is_thin():
    a = assess_catalog_match([], "done when health returns 200")
    assert a.sufficient is False
    assert a.research_inserted is True
    assert a.reason == "empty_matched_ids"
    assert a.match_count == 0


def test_heuristic_below_threshold_is_thin():
    assert SUFFICIENT_MATCH_MIN == 2
    a = assess_catalog_match(
        ["tool.wiki_note_search"],
        "done when notes index exists",
        matched_entry_keywords={"tool.wiki_note_search": ["wiki", "notes"]},
    )
    assert a.sufficient is False
    assert a.research_inserted is True
    assert a.reason.startswith("below_threshold:")


def test_heuristic_missing_critical_roles_is_thin():
    a = assess_catalog_match(
        ["tool.wiki_note_search", "agent.assistant"],
        "done when health Z returns 200",
        matched_entry_keywords={
            "tool.wiki_note_search": ["wiki", "notes", "search"],
            "agent.assistant": ["assistant", "handoff"],
        },
    )
    assert a.sufficient is False
    assert a.research_inserted is True
    assert "missing_critical_roles" in a.reason
    assert "health" in a.reason


def test_heuristic_sufficient_skips_research():
    a = assess_catalog_match(
        ["tool.wiki_note_search", "tool.health_probe", "agent.assistant"],
        "done when health Z returns 200",
        matched_entry_keywords={
            "tool.wiki_note_search": ["wiki", "notes"],
            "tool.health_probe": ["health", "probe", "200"],
            "agent.assistant": ["assistant", "execute"],
        },
    )
    assert a.sufficient is True
    assert a.research_inserted is False
    assert a.reason == "sufficient_match"


# --- REQ-RESEARCH-001 / 002 -------------------------------------------------


def test_req_research_001_thin_inserts_research_before_formulate(orch, resolver, store):
    """Thin match → Research phase before Formulate/Execute [REQ-RESEARCH-001]."""
    _seed_thin_one(resolver)
    job = orch.create_job_from_catalog_resolve(
        intent=(
            "First search wiki notes inventory, then formulate a plan, "
            "finally verify done when the notes index exists."
        ),
        session_id="sess_r001",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    phases = store.list_phases_for_job(job.id)
    names = [p.name for p in phases]
    assert names[0].lower().startswith("research"), names
    assert any(n.lower().startswith("formulate") for n in names), names
    assert names[-1].lower().startswith("execute"), names
    # Research is strictly before formulate
    ri = next(i for i, n in enumerate(names) if n.lower().startswith("research"))
    fi = next(i for i, n in enumerate(names) if n.lower().startswith("formulate"))
    assert ri < fi
    cp = orch.get_latest_checkpoint(job.id)
    assert cp is not None
    assert cp.research_inserted is True
    assert cp.research_reason


def test_req_research_002_sufficient_skips_research(orch, resolver, store):
    """Sufficient match → Formulate/Execute only; no research latency tax [REQ-RESEARCH-002]."""
    _seed_rich(resolver)
    job = orch.create_job_from_catalog_resolve(
        intent=(
            "First research the wiki notes inventory, then handoff to the assistant, "
            "finally verify done when health Z returns 200."
        ),
        session_id="sess_r002",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    phases = store.list_phases_for_job(job.id)
    names = [p.name for p in phases]
    assert not any(n.lower().startswith("research") for n in names), names
    assert any(n.lower().startswith("formulate") for n in names), names
    assert names[-1].lower().startswith("execute"), names
    cp = orch.get_latest_checkpoint(job.id)
    assert cp is not None
    assert cp.research_inserted is False
    assert cp.research_reason == "sufficient_match"


# --- REQ-RESEARCH-003 -------------------------------------------------------


def test_req_research_003_writes_memory_db_not_trusted(orch, resolver, store, tmp_path):
    """Research writes memory.db + gap proposals; never trusted skill/tool [REQ-RESEARCH-003]."""
    _seed_thin_one(resolver)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    orch_mem = JobPhaseOrchestrator(
        store, capability_resolver=resolver, data_dir=str(data_dir)
    )
    job = orch_mem.create_job_from_catalog_resolve(
        intent=(
            "Search wiki notes then verify done when health endpoint returns 200."
        ),
        session_id="sess_r003",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    assert orch_mem.get_latest_checkpoint(job.id).research_inserted is True

    # Fake scaffold / trusted writer must never be called from research.
    trusted_writer = MagicMock()
    result = run_standing_research(
        orch_mem,
        job_id=job.id,
        intent=job.goal,
        success_rule=job.success_rule,
        matched_capability_ids=orch_mem.matched_capability_ids_for_job(job.id),
        assessment=assess_catalog_match(
            orch_mem.matched_capability_ids_for_job(job.id),
            job.success_rule,
            matched_entry_keywords={
                "tool.wiki_note_search": ["wiki", "notes", "search"],
            },
        ),
        trusted_skill_writer=trusted_writer,
        trusted_tool_writer=trusted_writer,
        data_dir=str(data_dir),
    )
    assert result["ok"] is True
    assert result["memory_fact_ids"], "must write memory.db facts"
    assert result.get("catalog_gap_proposals") is not None
    trusted_writer.assert_not_called()

    mem_files = list(Path(data_dir).rglob("*_memory.db"))
    storage_files = list(Path(data_dir).rglob("*_storage.db"))
    assert mem_files, "research must touch memory.db"
    assert not storage_files, "research must never touch storage.db"


# --- REQ-RESEARCH-004 -------------------------------------------------------


def test_req_research_004_checkpoint_and_journey_research_span(orch, resolver, store):
    """Checkpoint research_inserted + reason; journey shows research span [REQ-RESEARCH-004]."""
    _seed_thin_one(resolver)
    job = orch.create_job_from_catalog_resolve(
        intent=(
            "Search wiki notes then formulate and verify done when notes index exists."
        ),
        session_id="sess_r004",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    cp = orch.get_latest_checkpoint(job.id)
    assert cp.research_inserted is True
    assert isinstance(cp.research_reason, str) and cp.research_reason

    # Emit research journey event the way production does after research write.
    run_standing_research(
        orch,
        job_id=job.id,
        intent=job.goal,
        success_rule=job.success_rule,
        matched_capability_ids=orch.matched_capability_ids_for_job(job.id),
        assessment=assess_catalog_match(
            orch.matched_capability_ids_for_job(job.id),
            job.success_rule,
        ),
    )
    journey = build_standing_journey(store, job_id=job.id)
    assert journey["ok"] is True
    kinds = [t.get("kind") for t in journey.get("timeline") or []]
    assert "research" in kinds or any(
        str(s.get("name") or "").startswith("standing.research")
        for s in (journey.get("spans") or [])
    ), (kinds, [s.get("name") for s in journey.get("spans") or []])
    span_names = [s.get("name") for s in journey.get("spans") or []]
    assert any(str(n).startswith("standing.research") for n in span_names), span_names


def test_req_research_005_no_second_orchestrator():
    """Extends standing path only — no parallel ResearchOrchestrator [REQ-RESEARCH-005]."""
    import inspect

    from src.application.orchestration import job_phase_orchestrator as mod
    from src.application.orchestration import research_before_plan as rbp

    src = inspect.getsource(mod.JobPhaseOrchestrator)
    assert "assess_catalog_match" in src or "research_inserted" in src
    assert not hasattr(rbp, "ResearchOrchestrator")
    assert not hasattr(rbp, "SecondJobGraph")
