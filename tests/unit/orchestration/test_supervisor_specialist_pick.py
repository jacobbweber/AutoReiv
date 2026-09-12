"""CARD-234 Supervisor specialist pick from matched catalog [REQ-SUPER-001..005].

Pick only from matched catalog agent/pack IDs; never-widen child <= parent;
out-of-catalog handoff rejected; no match => park/scaffold or fail-closed (not invent);
journey supervisor_pick + child_job_id; Chat strip parent<->child.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.observability.standing_journey import build_standing_journey
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.standing_a2a_handoff import (
    child_ids_do_not_widen,
    linked_child_job_ids,
    matched_ids_for_parent,
)
from src.application.orchestration.supervisor_specialist_pick import (
    OutOfCatalogHandoffError,
    catalog_specialist_ids,
    match_specialty_candidates,
    pick_specialist_from_matched,
    reject_out_of_catalog_handoff,
    supervisor_specialist_handoff,
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


def _seed_catalog(resolver: CapabilityCatalogResolver) -> None:
    resolver.upsert(
        CapabilityIndexEntry(
            id="tool.wiki_note_search",
            kind=CapabilityKind.TOOL,
            name="wiki_note_search",
            summary="Search wiki notes",
            keywords=["wiki", "search", "notes", "research"],
            roles=["assistant", "researcher"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.assistant",
            kind=CapabilityKind.AGENT,
            name="Assistant",
            summary="Day-to-day coordinator",
            keywords=["assistant", "coordinate", "handoff"],
            roles=["assistant", "autoreiv"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.researcher",
            kind=CapabilityKind.AGENT,
            name="Researcher",
            summary="Wiki and research specialist",
            keywords=["research", "wiki", "notes", "survey", "specialist"],
            roles=["researcher", "assistant"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="pack.fleet-ops",
            kind=CapabilityKind.PACK,
            name="Fleet Ops Pack",
            summary="Homelab fleet operations pack",
            keywords=["fleet", "homelab", "ops", "infra"],
            roles=["admin", "engineer"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
            metadata={"agent_id": "fleet-ops"},
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.auditor",
            kind=CapabilityKind.AGENT,
            name="Auditor",
            summary="Audit specialist not in typical research match",
            keywords=["audit", "compliance", "review"],
            roles=["auditor"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )


def _running_parent(orch, resolver, *, session_id: str, matched=None):
    _seed_catalog(resolver)
    ids = list(
        matched
        if matched is not None
        else [
            "tool.wiki_note_search",
            "agent.assistant",
            "agent.researcher",
            "pack.fleet-ops",
        ]
    )
    job = orch.create_job_with_phases(
        goal="supervisor pick proof: research then specialist handoff",
        session_id=session_id,
        agent_id="assistant",
        phase_specs=[
            {
                "name": "Execute",
                "success_rule": "done when research specialist completes wiki survey",
                "verify_checker": "pytest",
            },
        ],
        success_rule="done when research specialist completes wiki survey",
        template_id="catalog_resolve_rhe",
    )
    orch._matched_ids[job.id] = list(ids)
    phases = orch._store.list_phases_for_job(job.id)
    orch._commit_checkpoint(
        phases[0],
        verifier_status="none",
        hitl_park_state=False,
        matched_capability_ids=ids,
    )
    started = orch.start_phase(phases[0].id)
    return orch._store.get_job(job.id), started, ids


def _entry_meta(resolver, ids):
    meta = {}
    store = getattr(resolver, "_store", None)
    getter = getattr(store, "get_entry", None) if store is not None else None
    for cid in ids:
        entry = getter(cid) if callable(getter) else None
        if entry is None:
            continue
        kind = getattr(entry.kind, "value", entry.kind)
        meta[cid] = {
            "kind": str(kind),
            "name": entry.name,
            "keywords": list(entry.keywords or []),
            "roles": list(entry.roles or []),
            "metadata": dict(getattr(entry, "metadata", None) or {}),
        }
    return meta


def test_catalog_specialist_ids_agents_and_packs_only():
    ids = [
        "tool.wiki_note_search",
        "agent.researcher",
        "pack.fleet-ops",
        "skill.wiki_index",
    ]
    specs = catalog_specialist_ids(ids)
    assert specs == ["agent.researcher", "pack.fleet-ops"]
    assert "tool.wiki_note_search" not in specs


def test_req_super_001_pick_only_from_matched_catalog_ids(orch, resolver):
    job, phase, ids = _running_parent(orch, resolver, session_id="sess_s001")
    meta = _entry_meta(resolver, ids)
    pick = pick_specialist_from_matched(
        matched_ids=ids,
        specialty="research wiki survey",
        entry_meta=meta,
    )
    assert pick.ok is True
    assert pick.picked_catalog_id in {"agent.researcher", "pack.fleet-ops", "agent.assistant"}
    assert pick.picked_catalog_id in ids
    assert pick.picked_agent_id  # resolved agent id for handoff
    assert pick.invented is False
    # Must not invent free-form role theatre id
    assert pick.picked_agent_id not in {"research-specialist", "wiki-surveyor", "invented-agent"}


def test_req_super_002_handoff_never_widen_same_job(orch, resolver, store):
    """CARD-265: supervisor pick binds same job_id; privilege never widens."""
    job, phase, parent_ids = _running_parent(orch, resolver, session_id="sess_s002")
    meta = _entry_meta(resolver, parent_ids)
    result = supervisor_specialist_handoff(
        orch,
        phase_id=phase.id,
        specialty="research wiki",
        entry_meta=meta,
        session_id=f"{job.session_id}_child",
    )
    assert result["ok"] is True
    assert result["action"] == "handoff"
    assert result.get("same_job_id") == job.id
    assert result.get("child_job_id") in (None, job.id)
    assert result.get("privilege_escalated") is False
    eff = result.get("effective_matched_capability_ids") or result.get(
        "matched_capability_ids"
    ) or []
    assert child_ids_do_not_widen(parent_ids, eff)
    assert set(eff).issubset(set(parent_ids))
    assert linked_child_job_ids(orch, job.id) == []
    cp = orch.get_latest_checkpoint(job.id)
    assert cp is not None
    hooked = orch.supervisor_pick_specialist(
        phase.id,
        specialty="research wiki",
        entry_meta=meta,
        session_id=f"{job.session_id}_child2",
    )
    assert hooked.get("ok") is True
    assert hooked.get("same_job_id") == job.id or hooked.get("action") in {
        "handoff",
        "park",
        "scaffold",
        "fail_closed",
    }


def test_req_super_003_out_of_catalog_handoff_rejected(orch, resolver):
    job, phase, ids = _running_parent(orch, resolver, session_id="sess_s003")
    with pytest.raises(OutOfCatalogHandoffError):
        reject_out_of_catalog_handoff(
            target_agent_id="invented-role-theatre-agent",
            matched_ids=ids,
            entry_meta=_entry_meta(resolver, ids),
        )
    result = supervisor_specialist_handoff(
        orch,
        phase_id=phase.id,
        specialty="research",
        requested_agent_id="invented-role-theatre-agent",
        entry_meta=_entry_meta(resolver, ids),
        session_id=f"{job.session_id}_rej",
    )
    assert result["ok"] is False
    assert result["action"] == "rejected"
    assert result.get("invented") is False
    assert result.get("child_job_id") in (None, "")


def test_req_super_003_no_match_park_or_fail_closed_not_invent(orch, resolver):
    # Matched set has tools + assistant only — no research specialist agent/pack
    job, phase, ids = _running_parent(
        orch,
        resolver,
        session_id="sess_s003b",
        matched=["tool.wiki_note_search", "agent.assistant"],
    )
    meta = _entry_meta(resolver, ids)
    # Force specialty that cannot match assistant keywords strongly enough
    # by requiring an agent/pack keyword that is absent from matched specialists.
    pick = pick_specialist_from_matched(
        matched_ids=ids,
        specialty="quantum cryptography auditor compliance",
        entry_meta=meta,
    )
    assert pick.ok is False
    assert pick.invented is False
    assert pick.picked_agent_id is None

    result = supervisor_specialist_handoff(
        orch,
        phase_id=phase.id,
        specialty="quantum cryptography auditor compliance",
        entry_meta=meta,
        session_id=f"{job.session_id}_nomatch",
        on_no_match="park",
    )
    assert result["ok"] is False or result["action"] in {"park", "scaffold", "fail_closed"}
    assert result["action"] in {"park", "scaffold", "fail_closed"}
    assert result.get("invented") is False
    assert not result.get("child_job_id")
    # Parent parked when on_no_match=park
    if result["action"] == "park":
        refreshed = orch._store.get_phase(phase.id)
        assert refreshed.status == PhaseStatus.WAITING_APPROVAL or str(
            getattr(refreshed.react_state, "value", refreshed.react_state)
        ).upper() == "PARKED"


def test_req_super_004_journey_supervisor_pick_and_child_job_id(orch, resolver, store):
    job, phase, ids = _running_parent(orch, resolver, session_id="sess_s004")
    meta = _entry_meta(resolver, ids)
    result = supervisor_specialist_handoff(
        orch,
        phase_id=phase.id,
        specialty="research wiki",
        entry_meta=meta,
        session_id=f"{job.session_id}_jrny",
    )
    assert result["ok"] is True
    child_id = result["child_job_id"]
    journey = build_standing_journey(store, job_id=job.id)
    kinds = [e.get("kind") for e in (journey.get("timeline") or [])]
    assert "supervisor_pick" in kinds or any(
        (e.get("kind") == "supervisor_pick") for e in (journey.get("timeline") or [])
    )
    # Span tree
    span_names = [s.get("name") for s in (journey.get("spans") or [])]
    assert "standing.supervisor_pick" in span_names
    # child_job_id visible on journey
    assert child_id in (journey.get("child_job_ids") or []) or any(
        (e.get("payload") or {}).get("child_job_id") == child_id
        for e in (journey.get("timeline") or [])
        if e.get("kind") == "supervisor_pick"
    )


def test_req_super_004_chat_strip_parent_child_fields():
    """Chat strip API surfaces parent<->child when SSE/API fields exist."""
    chat_js = Path("src/web/static/modules/studios/chat.js").read_text(encoding="utf-8")
    html = Path("src/web/templates/index.html").read_text(encoding="utf-8")
    assert "formatJobPhaseStrip" in chat_js
    assert "parentJobId" in chat_js or "parent_job_id" in chat_js
    assert "childJobId" in chat_js or "child_job_id" in chat_js or "childJobIds" in chat_js
    # Strip shows parent<->child link UI or data attribute
    assert (
        'data-job-phase="link"' in html
        or "parent↔child" in chat_js
        or "parent<->child" in chat_js
        or "parentChildLabel" in chat_js
        or "parent_child" in chat_js
    )
    # applyJobPhaseEvent accepts supervisor_pick / a2a link fields
    assert "supervisor_pick" in chat_js or "parent_job_id" in chat_js
    assert "child_job_id" in chat_js or "child_job_ids" in chat_js


def test_match_specialty_candidates_prefer_keyword_overlap():
    meta = {
        "agent.assistant": {
            "kind": "agent",
            "name": "Assistant",
            "keywords": ["assistant", "coordinate"],
            "roles": ["assistant"],
            "metadata": {},
        },
        "agent.researcher": {
            "kind": "agent",
            "name": "Researcher",
            "keywords": ["research", "wiki", "survey"],
            "roles": ["researcher"],
            "metadata": {},
        },
        "pack.fleet-ops": {
            "kind": "pack",
            "name": "Fleet Ops",
            "keywords": ["fleet", "ops"],
            "roles": ["admin"],
            "metadata": {"agent_id": "fleet-ops"},
        },
        "tool.wiki_note_search": {
            "kind": "tool",
            "name": "wiki_note_search",
            "keywords": ["wiki", "search"],
            "roles": [],
            "metadata": {},
        },
    }
    cands = match_specialty_candidates(
        matched_ids=list(meta.keys()),
        specialty="research wiki survey",
        entry_meta=meta,
    )
    assert cands
    assert cands[0] == "agent.researcher"
    assert "tool.wiki_note_search" not in cands
