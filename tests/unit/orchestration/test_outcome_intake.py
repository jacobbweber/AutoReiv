"""CARD-230 Outcome intake: durable Job + testable success_rule [REQ-INTAKE-001..004].

Red→green: outcome-shaped → Job+success_rule; vibes reject; chitchat stays ReAct;
matched IDs authority / agent picker cannot widen; fail-closed missing fields before phase 1.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.outcome_intake import (
    OutcomeIntakeError,
    assert_intake_ready_for_phase1,
    derive_success_rule,
    is_outcome_shaped,
    is_testable_success_rule,
    is_vibes_only_success_rule,
    matched_ids_authority,
)
from src.application.orchestration.standing_job_graph import (
    StandingRoute,
    route_standing_chat,
)
from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    TrustTier,
)
from src.domain.orchestration.models import PhaseStatus
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
            roles=["assistant"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.assistant",
            kind=CapabilityKind.AGENT,
            name="Assistant",
            summary="Day-to-day coordinator handoff",
            keywords=["assistant", "handoff", "coordinate"],
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
            keywords=["health", "probe", "http", "200"],
            roles=["assistant"],
        )
    )


# --- REQ-INTAKE-001 ---------------------------------------------------------


def test_req_intake_001_outcome_shaped_creates_durable_job(orch, resolver, store):
    """Outcome-shaped ask → durable Job on standing path; no goal_mode toggle."""
    _seed(resolver)
    ask = (
        "Deliver a wiki research brief, then hand off to the assistant, "
        "finally verify health returns 200 for the notes API."
    )
    assert is_outcome_shaped(ask) is True
    assert route_standing_chat(ask) == StandingRoute.MULTI_STEP_JOB_GRAPH

    job = orch.create_job_from_catalog_resolve(
        intent=ask,
        session_id="sess_intake_001",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    assert job.id
    assert getattr(job, "success_rule", "").strip()
    assert store.get_job(job.id).id == job.id
    phases = store.list_phases_for_job(job.id)
    assert len(phases) >= 1
    assert all(p.status == PhaseStatus.QUEUED for p in phases)


def test_req_intake_001_goal_deliverable_language_routes_to_job_graph():
    """Goal/deliverable language (not only first/then) is outcome-shaped [REQ-INTAKE-001]."""
    goalish = (
        "Build a durable health-check deliverable that proves the wiki API "
        "returns HTTP 200 and the notes index exists on disk."
    )
    assert is_outcome_shaped(goalish) is True
    assert route_standing_chat(goalish) == StandingRoute.MULTI_STEP_JOB_GRAPH


def test_req_intake_001_short_chitchat_stays_plain_react():
    """Short tool turns stay plain ReAct (215 rule) [REQ-INTAKE-001]."""
    assert is_outcome_shaped("What time is it") is False
    assert route_standing_chat("What time is it") == StandingRoute.SHORT_REACT
    assert route_standing_chat("thanks") == StandingRoute.SHORT_REACT


# --- REQ-INTAKE-002 ---------------------------------------------------------


def test_req_intake_002_persists_testable_success_rule(orch, resolver, store):
    """Job persists testable success_rule stop condition [REQ-INTAKE-002]."""
    _seed(resolver)
    ask = (
        "First research wiki notes, then handoff, finally verify "
        "done when health Z returns 200."
    )
    job = orch.create_job_from_catalog_resolve(
        intent=ask,
        session_id="sess_intake_002",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    rule = (job.success_rule or "").strip()
    assert rule
    assert is_testable_success_rule(rule) is True
    assert is_vibes_only_success_rule(rule) is False
    # Round-trip from store
    reloaded = store.get_job(job.id)
    assert (reloaded.success_rule or "").strip() == rule


def test_req_intake_002_vibes_only_success_rule_rejected_at_intake():
    """Free-text vibes-only success_rule is reject at intake [REQ-INTAKE-002]."""
    assert is_vibes_only_success_rule("looks good") is True
    assert is_vibes_only_success_rule("seems fine") is True
    assert is_testable_success_rule("looks good") is False
    with pytest.raises(OutcomeIntakeError):
        derive_success_rule("polish the UI", explicit="looks good")


def test_req_intake_002_derive_prefers_structured_stop_condition():
    """derive_success_rule extracts testable stop conditions from intent."""
    rule = derive_success_rule(
        "Ship the notes API; done when health Z returns 200 and test Y passes."
    )
    assert is_testable_success_rule(rule)
    assert "200" in rule or "passes" in rule.lower() or "done when" in rule.lower()


# --- REQ-INTAKE-003 ---------------------------------------------------------


def test_req_intake_003_matched_ids_are_authority_agent_cannot_widen(
    orch, resolver, store
):
    """Catalog matched IDs are capability authority; agent picker cannot widen."""
    _seed(resolver)
    ask = (
        "First research the wiki notes, then handoff to the assistant, "
        "finally execute a health verify that returns 200."
    )
    job = orch.create_job_from_catalog_resolve(
        intent=ask,
        session_id="sess_intake_003",
        agent_id="assistant",  # preference only
        role="assistant",
        verify_checker=None,
    )
    matched = orch.matched_capability_ids_for_job(job.id)
    assert matched, "catalog resolve must yield matched IDs"
    # Agent picker / caller cannot widen beyond resolve result
    widened = matched_ids_authority(
        matched,
        preferred_agent_id="assistant",
        widen_attempt=["tool.secret_exfil", "tool.unrelated_admin"],
    )
    assert widened == list(matched)
    assert "tool.secret_exfil" not in widened
    assert "tool.unrelated_admin" not in widened


# --- REQ-INTAKE-004 ---------------------------------------------------------


def test_req_intake_004_fail_closed_missing_success_rule_or_matched_ids(
    orch, resolver, store
):
    """Missing success_rule or matched_capability_ids ⇒ do not start phase 1."""
    _seed(resolver)
    ask = (
        "First research wiki notes, then handoff, finally verify "
        "done when the notes index exists."
    )
    job = orch.create_job_from_catalog_resolve(
        intent=ask,
        session_id="sess_intake_004",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    # Happy path: ready
    assert_intake_ready_for_phase1(
        success_rule=job.success_rule,
        matched_capability_ids=orch.matched_capability_ids_for_job(job.id),
    )

    with pytest.raises(OutcomeIntakeError):
        assert_intake_ready_for_phase1(
            success_rule="",
            matched_capability_ids=["tool.wiki_note_search"],
        )
    with pytest.raises(OutcomeIntakeError):
        assert_intake_ready_for_phase1(
            success_rule="done when notes index exists",
            matched_capability_ids=[],
        )


def test_req_intake_004_phase1_start_gated_by_intake(orch, resolver, store):
    """Orchestrator start_phase fail-closes when standing intake fields missing [REQ-INTAKE-004]."""
    _seed(resolver)
    from src.domain.orchestration.models import PhaseSpec

    # Standing catalog template without success_rule / matched IDs => fail closed.
    bare = orch.create_job_with_phases(
        goal="catalog-shaped goal missing intake fields",
        session_id="sess_intake_004b",
        agent_id="assistant",
        phase_specs=[
            PhaseSpec(name="Research", success_rule="", assigned_agent_id="assistant")
        ],
        template_id="catalog_resolve_rhe",
    )
    assert not (getattr(bare, "success_rule", None) or "").strip()
    assert not orch.matched_capability_ids_for_job(bare.id)

    with pytest.raises(OutcomeIntakeError):
        orch.start_phase(bare.current_phase_id)


def test_req_intake_005_no_second_orchestrator_module_exists():
    """Extends standing path only — outcome_intake is a helper, not a second orch."""
    import src.application.orchestration.outcome_intake as oi

    assert hasattr(oi, "derive_success_rule")
    assert hasattr(oi, "assert_intake_ready_for_phase1")
    assert not hasattr(oi, "OutcomeOrchestrator")
    assert not hasattr(oi, "GoalModeEngine")

def test_derive_success_rule_prefers_colon_done_when_over_parenthetical():
    """CARD-257: bare done-when, in parens must not steal Done-when: clause."""
    ask = (
        "Write a short Wiki note in 00_Inbox explaining standing Jobs "
        "(phases Formulate then Execute, done-when, and why HITL parks on create). "
        "Done-when: I can open that note via wiki_note_read. Keep it under 200 words."
    )
    rule = derive_success_rule(ask)
    assert "wiki_note_read" in rule.lower() or "open that note" in rule.lower()
    assert "parks on create" not in rule.lower()

