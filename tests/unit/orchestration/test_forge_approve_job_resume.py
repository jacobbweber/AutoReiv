"""CARD-251: Forge Approve resumes same job_id (origin session); no orphan.

Parked mid-job HITL -> Forge Approve -> promote + unpark same job_id.
Never soft-delete parked Jobs. Observe one tree. Orphan mint prevented.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.capabilities.scaffold_spine import SelfScaffoldSpine
from src.application.observability.standing_journey import build_standing_journey
from src.application.orchestration.chat_job_binding import latest_open_job_for_session
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.mid_job_self_scaffold import (
    apply_mid_job_scaffold_on_gap,
    detect_mid_job_capability_gap,
    forge_approve_and_resume_job,
    parked_job_id_from_scaffold,
)
from src.application.skills.user_catalog import UserSkillCatalog
from src.domain.capabilities.models import CapabilityIndexEntry, CapabilityKind, TrustTier
from src.domain.capabilities.scaffold import ScaffoldPhase
from src.domain.orchestration.models import JobStatus, PhaseStatus
from src.infrastructure.memory.repositories.capability_catalog import CapabilityCatalogRepository
from src.infrastructure.memory.repositories.scaffold_spine import ScaffoldSpineRepository
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
def skills_dir(tmp_path):
    d = tmp_path / "skills"
    d.mkdir()
    return d


@pytest.fixture
def store(temp_db_path):
    return SQLiteStateStore(db_path=temp_db_path)


@pytest.fixture
def spine(store, skills_dir):
    catalog = UserSkillCatalog(skills_dir=skills_dir)
    cap_repo = CapabilityCatalogRepository(store)
    spine_repo = ScaffoldSpineRepository(store)
    return SelfScaffoldSpine(
        spine_repo=spine_repo,
        capability_repo=cap_repo,
        catalog=catalog,
    )


@pytest.fixture
def orch(store, spine):
    resolver = CapabilityCatalogResolver(spine.capability_repo)
    return JobPhaseOrchestrator(
        store,
        capability_resolver=resolver,
        skill_catalog=spine.catalog,
    )


def _seed_trusted_probe(spine):
    entry = CapabilityIndexEntry(
        id="tool.health_probe",
        kind=CapabilityKind.TOOL,
        name="health_probe",
        summary="HTTP health probe",
        keywords=["health", "probe", "http", "200"],
        trust_tier=TrustTier.TRUSTED,
        source="builtin",
    )
    spine.capability_repo.upsert_entry(entry)
    return entry


def _parked_mid_job(orch, store, spine, *, session_id: str):
    _seed_trusted_probe(spine)
    job = orch.create_job_with_phases(
        goal="forge approve resume proof",
        session_id=session_id,
        agent_id="assistant",
        phase_specs=[
            {
                "name": "Execute",
                "success_rule": "done when wiki notes indexed and health returns 200",
                "verify_checker": "pytest",
            },
        ],
        success_rule="done when wiki notes indexed and health returns 200",
        template_id="catalog_resolve_rhe",
    )
    orch._matched_ids[job.id] = ["tool.health_probe"]
    phases = store.list_phases_for_job(job.id)
    orch._commit_checkpoint(
        phases[0],
        verifier_status="none",
        hitl_park_state=False,
        matched_capability_ids=["tool.health_probe"],
    )
    started = orch.start_phase(phases[0].id)
    gap = detect_mid_job_capability_gap(
        matched_ids=orch.matched_capability_ids_for_job(job.id),
        success_rule=job.success_rule,
        matched_entry_keywords={"tool.health_probe": ["health", "probe", "http", "200"]},
    )
    opened = apply_mid_job_scaffold_on_gap(
        orch,
        spine=spine,
        phase_id=started.id,
        gap=gap,
        kind="skill",
        name="wiki-notes-index",
        pack_id="wiki-notes-index",
        summary="Index wiki notes",
        content="# Wiki Notes Index\n",
        park=True,
    )
    rid = opened["record_id"]
    spine.mark_sandbox_exec(rid, evidence="unit-sandbox")
    spine.version(rid)
    return store.get_job(job.id), store.get_phase(started.id), rid


def test_req_forge_resume_001_same_job_id_origin_session(orch, store, spine):
    job, phase, rid = _parked_mid_job(orch, store, spine, session_id="sess_forge_251")
    assert store.get_job(job.id).status == JobStatus.WAITING_APPROVAL
    rec = spine.get(rid)
    assert parked_job_id_from_scaffold(rec) == job.id

    result = forge_approve_and_resume_job(orch, spine=spine, record_id=rid)
    assert result["ok"] is True
    assert result["job_id"] == job.id
    assert result["session_id"] == "sess_forge_251"
    assert result["same_job"] is True
    assert result["resumed"] is True
    assert result["orphan"] is False
    assert result["soft_deleted"] is False

    job_after = store.get_job(job.id)
    assert job_after.id == job.id
    assert job_after.status == JobStatus.RUNNING
    assert store.get_phase(phase.id).status == PhaseStatus.RUNNING
    rec2 = spine.get(rid)
    assert rec2.phase == ScaffoldPhase.TRUSTED
    assert rec2.trust_tier == TrustTier.TRUSTED


def test_req_forge_resume_002_no_soft_delete_one_observe_tree(orch, store, spine):
    job, _phase, rid = _parked_mid_job(orch, store, spine, session_id="sess_forge_251_obs")
    before_jobs = store.list_jobs_for_session("sess_forge_251_obs")
    assert len(before_jobs) == 1

    result = orch.forge_approve_and_resume(spine=spine, record_id=rid)
    assert result["soft_deleted"] is False
    assert result["job_id"] == job.id

    after_jobs = store.list_jobs_for_session("sess_forge_251_obs")
    assert len(after_jobs) == 1
    assert after_jobs[0].id == job.id
    assert after_jobs[0].status != JobStatus.CANCELLED

    journey = build_standing_journey(store, job_id=job.id)
    assert isinstance(journey, dict)
    tl = journey.get("timeline") or []
    kinds = [e.get("kind") for e in tl if isinstance(e, dict)]
    spans = journey.get("spans") or []
    assert (
        "forge_approve_resume" in kinds
        or any("forge_approve" in str(s) for s in spans)
        or "scaffold_hitl" in kinds
    )
    open_job = latest_open_job_for_session(store, "sess_forge_251_obs")
    assert open_job is not None
    assert open_job.id == job.id


def test_req_forge_resume_standalone_promote_only(orch, store, spine):
    _seed_trusted_probe(spine)
    rec = spine.draft(
        kind="skill",
        name="standalone-candidate",
        pack_id="standalone-candidate",
        summary="no job",
        content="# Solo\n",
        keywords=["solo"],
    )
    spine.mark_sandbox_exec(rec.id, evidence="unit")
    spine.version(rec.id)
    result = forge_approve_and_resume_job(orch, spine=spine, record_id=rec.id)
    assert result["action"] == "promote_only"
    assert result["job_id"] is None
    assert result["resumed"] is False
    assert spine.get(rec.id).trust_tier == TrustTier.TRUSTED


def test_parked_job_id_from_scaffold_metadata():
    class R:
        metadata = {"job_id": "job_abc", "phase_id": "ph_1"}

    assert parked_job_id_from_scaffold(R()) == "job_abc"
