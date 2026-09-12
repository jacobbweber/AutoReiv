"""CARD-257 Research gate skip-or-continue + status honesty [REQ-RGATE-001..003]."""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.outcome_intake import derive_success_rule
from src.application.orchestration.research_before_plan import (
    assess_catalog_match,
    auto_complete_prepared_research,
    format_job_failed_honesty,
    is_research_phase,
    research_already_prepared,
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


def _seed_wiki_read(resolver: CapabilityCatalogResolver) -> None:
    resolver.upsert(
        CapabilityIndexEntry(
            id="tool.wiki_note_read",
            kind=CapabilityKind.TOOL,
            name="wiki_note_read",
            summary="Read a wiki note",
            keywords=["wiki", "note", "read", "open", "inbox"],
            roles=["assistant"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )


# --- REQ-RGATE-001 -----------------------------------------------------------


def test_outcome_covered_by_matched_wiki_skips_research():
    """wiki_note_* covering wiki done-when → sufficient even when count < 2."""
    a = assess_catalog_match(
        ["tool.wiki_note_read"],
        "done when I can open that note via wiki_note_read",
        matched_entry_keywords={
            "tool.wiki_note_read": ["wiki", "note", "read", "open", "inbox"]
        },
    )
    assert a.sufficient is True
    assert a.research_inserted is False
    assert a.reason == "outcome_covered_by_matched"
    assert a.match_count == 1


def test_below_threshold_still_thin_when_family_uncovered():
    """1 wiki tool + health done-when remains thin (uncovered family)."""
    a = assess_catalog_match(
        ["tool.wiki_note_search"],
        "done when health returns 200",
        matched_entry_keywords={"tool.wiki_note_search": ["wiki", "notes"]},
    )
    assert a.sufficient is False
    assert a.research_inserted is True
    assert a.reason.startswith("below_threshold:")


def test_cos_prompt_skips_research_on_wiki_cover(orch, resolver, store):
    _seed_wiki_read(resolver)
    ask = (
        "Write a short Wiki note in 00_Inbox explaining what a standing Job is in "
        "AutoReiv (phases Formulate then Execute, done-when, and why HITL parks on create). "
        "Done-when: I can open that note via wiki_note_read. Keep it under 200 words."
    )
    job = orch.create_job_from_catalog_resolve(
        intent=ask,
        session_id="sess_card257_cover",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
        matched_capability_ids=["tool.wiki_note_read"],
    )
    phases = [p.name for p in store.list_phases_for_job(job.id)]
    assert phases[0] != "Research" or "Research" not in phases
    assert phases == ["Formulate", "Execute"] or (
        phases[0] == "Formulate" and "Execute" in phases
    )
    cp = orch.get_latest_checkpoint(job.id)
    assert cp is not None
    assert bool(getattr(cp, "research_inserted", True)) is False
    assert getattr(cp, "research_reason", "") in {
        "outcome_covered_by_matched",
        "sufficient_match",
    }


# --- REQ-RGATE-002 -----------------------------------------------------------


def test_research_auto_complete_advances_without_llm(orch, resolver, store):
    """Thin research still inserts, but auto-complete advances to Formulate."""
    _seed_wiki_read(resolver)
    # Force thin: health rule with wiki tool only via explicit matched ids path
    job = orch.create_job_from_catalog_resolve(
        intent="Probe service health; done when health returns 200",
        session_id="sess_card257_auto",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
        matched_capability_ids=["tool.wiki_note_read"],
    )
    phases = store.list_phases_for_job(job.id)
    assert phases[0].name.lower().startswith("research")
    assert research_already_prepared(orch, job.id) is True
    research = phases[0]
    started = orch.start_phase(research.id)
    assert is_research_phase(started)
    result = auto_complete_prepared_research(orch, started, job)
    assert result["ok"] is True
    refreshed = store.get_phase(research.id)
    assert refreshed.status == PhaseStatus.DONE
    # Formulate should be current / still runnable
    phases2 = store.list_phases_for_job(job.id)
    formulate = next(p for p in phases2 if p.name == "Formulate")
    assert formulate.status == PhaseStatus.QUEUED
    job2 = store.get_job(job.id)
    assert job2.status.value != "failed"


# --- REQ-RGATE-003 -----------------------------------------------------------


def test_format_job_failed_honesty_never_says_done():
    msg = format_job_failed_honesty(
        job_id="job_deadbeef",
        phase_name="Research",
        reason="phase_llm_timeout after 120.0s",
    )
    assert "FAILED" in msg
    assert "job_deadbeef" in msg
    assert "Research" in msg
    assert "Not done" in msg
    assert "Done." not in msg
    assert "success criterion met" not in msg.lower()


# --- Done-when colon preference ---------------------------------------------


def test_derive_success_rule_prefers_colon_done_when():
    ask = (
        "Write a short Wiki note in 00_Inbox explaining what a standing Job is in "
        "AutoReiv (phases Formulate then Execute, done-when, and why HITL parks on create). "
        "Done-when: I can open that note via wiki_note_read. Keep it under 200 words."
    )
    rule = derive_success_rule(ask)
    assert "wiki_note_read" in rule.lower() or "open that note" in rule.lower()
    assert "parks on create" not in rule.lower()
