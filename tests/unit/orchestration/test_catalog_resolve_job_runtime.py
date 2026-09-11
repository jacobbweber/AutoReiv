"""CARD-220 Catalog resolve into JobPhaseOrchestrator [REQ-CATJOB-001..005].

Standing C runtime: intent → matched subset → Research/Handoff/Execute.
Persist matched capability IDs on checkpoint; resume reuses subset (no cold re-resolve).
Advance: only verified advances Execute; failed ⇒ park+replan; skip ≠ verified advance.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.orchestration.external_verifier_policy import (
    apply_phase_complete_verify_gate,
)
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    TrustTier,
)
from src.domain.orchestration.models import HandoffPacket, JobStatus, PhaseStatus
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


def _seed(resolver: CapabilityCatalogResolver) -> None:
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.wiki_note_search",
            kind=CapabilityKind.TOOL,
            name="wiki_note_search",
            summary="Search wiki notes",
            keywords=["wiki", "search", "notes", "research"],
            roles=["librarian"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.assistant",
            kind=CapabilityKind.AGENT,
            name="Assistant",
            summary="Day-to-day coordinator handoff",
            keywords=["assistant", "handoff", "coordinate"],
            roles=["general"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="skill.platform-health",
            kind=CapabilityKind.SKILL,
            name="platform-health",
            summary="Execute health checks",
            keywords=["health", "execute", "pytest", "verify"],
            roles=["sre"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="pack.homelab-admin",
            kind=CapabilityKind.PACK,
            name="Homelab Admin Pack",
            summary="Unrelated pack",
            keywords=["homelab", "vm", "hyperv"],
            roles=["homelab"],
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


def test_req_catjob_001_orchestrator_resolve_into_research_handoff_execute(orch, resolver, store):
    """Intent → matched subset → Research/Handoff/Execute standing plan [REQ-CATJOB-001]."""
    _seed(resolver)
    job = orch.create_job_from_catalog_resolve(
        intent="wiki search notes then handoff assistant and execute health",
        session_id="sess_catjob",
        agent_id="assistant",
        role="librarian",
    )
    phases = store.list_phases_for_job(job.id)
    assert len(phases) == 3
    names = [p.name.lower() for p in phases]
    assert names[0].startswith("research")
    assert names[1].startswith("handoff")
    assert names[2].startswith("execute")

    cp = orch.get_latest_checkpoint(job.id)
    assert cp is not None
    assert cp.matched_capability_ids
    assert "pack.homelab-admin" not in cp.matched_capability_ids
    assert "tool.wiki_note_search" in cp.matched_capability_ids


def test_req_catjob_002_resume_reuses_matched_ids_no_cold_reresolve(
    orch, resolver, store, temp_db_path
):
    """Checkpoint matched IDs reused on resume — no cold re-resolve drift [REQ-CATJOB-002]."""
    _seed(resolver)
    job = orch.create_job_from_catalog_resolve(
        intent="wiki search notes research",
        session_id="sess_reuse",
        agent_id="assistant",
        role="librarian",
    )
    cp0 = orch.get_latest_checkpoint(job.id)
    assert cp0 is not None
    locked_ids = list(cp0.matched_capability_ids)
    assert locked_ids

    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)

    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.poison_drift",
            kind=CapabilityKind.TOOL,
            name="poison_drift",
            summary="Would win a fresh resolve",
            keywords=["wiki", "search", "notes", "research"],
            roles=["librarian"],
        )
    )

    store2 = SQLiteStateStore(db_path=temp_db_path)
    orch2 = JobPhaseOrchestrator(
        store2,
        capability_resolver=CapabilityCatalogResolver(CapabilityCatalogRepository(store2)),
    )
    resume = orch2.resume_after_crash(job.id)

    assert resume.ok is True
    assert resume.resumed_from_checkpoint is True
    assert list(resume.matched_capability_ids) == locked_ids
    assert "tool.poison_drift" not in resume.matched_capability_ids
    assert orch2.matched_capability_ids_for_job(job.id) == locked_ids


def test_req_catjob_003_only_verified_advances_execute(orch, resolver, store):
    """Execute advances only on verified; skip does not; failed parks+replan [REQ-CATJOB-003]."""
    _seed(resolver)
    job = orch.create_job_from_catalog_resolve(
        intent="wiki search notes handoff execute health",
        session_id="sess_adv",
        agent_id="assistant",
    )
    phases = store.list_phases_for_job(job.id)
    research, handoff, execute = phases[0], phases[1], phases[2]

    orch.start_phase(research.id)
    g0 = apply_phase_complete_verify_gate(
        orch,
        phase_id=research.id,
        output_packet=_packet(job.goal, ["researched"]),
        checker_passed=None,
    )
    assert g0["status"] == "skipped_no_checker"
    assert g0.get("advanced") is True
    assert g0.get("verified_advance") is False

    orch.start_phase(handoff.id)
    g1 = apply_phase_complete_verify_gate(
        orch,
        phase_id=handoff.id,
        output_packet=_packet(job.goal, ["handed off"]),
        checker_passed=None,
    )
    assert g1["status"] == "skipped_no_checker"
    assert g1.get("advanced") is True
    assert g1.get("verified_advance") is False

    # Execute without checker: honest skip must NOT advance (lane=execute).
    execute = store.get_phase(execute.id)
    execute.verify_checker = None
    store.update_phase(execute)
    orch.start_phase(execute.id)
    g_skip = apply_phase_complete_verify_gate(
        orch,
        phase_id=execute.id,
        output_packet=_packet(job.goal, ["ran"]),
        checker_passed=None,
    )
    assert g_skip["status"] == "skipped_no_checker"
    assert g_skip.get("advanced") is False
    assert g_skip.get("verified_advance") is False
    assert store.get_job(job.id).status != JobStatus.DONE

    # Failed checker ⇒ park + needs_replan (never silent advance).
    job2 = orch.create_job_with_phases(
        goal="verify fail path",
        session_id="sess_adv2",
        agent_id="assistant",
        phase_specs=[
            {"name": "Execute", "success_rule": "green", "verify_checker": "pytest"},
            {"name": "After", "success_rule": "should-not-run"},
        ],
    )
    ex2 = store.list_phases_for_job(job2.id)[0]
    orch.start_phase(ex2.id)
    g_fail = apply_phase_complete_verify_gate(
        orch,
        phase_id=ex2.id,
        output_packet=_packet(job2.goal),
        checker_passed=False,
    )
    assert g_fail["status"] == "failed"
    assert g_fail.get("advanced") is False
    assert g_fail.get("needs_replan") is True
    assert g_fail.get("action") == "park"
    assert store.get_phase(ex2.id).status == PhaseStatus.WAITING_APPROVAL
    assert store.get_job(job2.id).status != JobStatus.DONE

    # Verified advances / finishes.
    job3 = orch.create_job_with_phases(
        goal="verify only",
        session_id="sess_adv3",
        agent_id="assistant",
        phase_specs=[
            {"name": "Execute", "success_rule": "green", "verify_checker": "pytest"},
        ],
    )
    ex3 = store.list_phases_for_job(job3.id)[0]
    orch.start_phase(ex3.id)
    g_ok = apply_phase_complete_verify_gate(
        orch,
        phase_id=ex3.id,
        output_packet=_packet("verify only", ["green"]),
        checker_passed=True,
    )
    assert g_ok["status"] == "verified"
    assert g_ok.get("verified_advance") is True
    assert store.get_job(job3.id).status == JobStatus.DONE


def test_req_catjob_004_no_second_graph_engine_extends_existing():
    """Extends existing modules; no parallel CatalogJobEngine [REQ-CATJOB-004]."""
    import inspect

    from src.application.orchestration import job_phase_orchestrator as mod

    src = inspect.getsource(mod.JobPhaseOrchestrator)
    assert "create_job_from_catalog_resolve" in src
    assert "matched_capability_ids" in src
    assert "class CatalogJobEngine" not in inspect.getsource(mod)
