# -*- coding: utf-8 -*-
"""CARD-255 Self-scaffold queue E2E [REQ-SSQ-001..005].

Full path candidate->sandbox->HITL->trusted; rollback; trusted-only next Job;
no auto-trust; Education gap Ask -> Forge -> Approve -> next Job uses skill.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.capabilities.scaffold_spine import SelfScaffoldSpine
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.self_scaffold_queue_e2e import (
    EDUCATION_GAP_ASK_RULE,
    next_job_resolve_uses_trusted,
    open_forge_candidate_from_education_gap,
    rollback_promoted_scaffold,
    run_self_scaffold_queue_e2e,
    sandbox_version_hitl_approve,
)
from src.application.skills.user_catalog import UserSkillCatalog
from src.domain.capabilities.models import CapabilityIndexEntry, CapabilityKind, TrustTier
from src.domain.capabilities.scaffold import ScaffoldPhase
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


def test_req_ssq_001_full_path_candidate_sandbox_hitl_trusted(orch, store, spine):
    opened = open_forge_candidate_from_education_gap(
        orch, spine=spine, session_id="sess_ssq001"
    )
    assert opened["forge_queue_has_candidate"] is True
    assert opened["trust_tier"] == "candidate"
    rid = opened["record_id"]
    approved = sandbox_version_hitl_approve(orch, spine=spine, record_id=rid)
    assert approved["trust_tier"] == "trusted"
    rec = spine.get(rid)
    assert rec.phase == ScaffoldPhase.TRUSTED
    assert rec.trust_tier == TrustTier.TRUSTED
    entry = spine.capability_repo.get_entry(rec.capability_id)
    assert entry.trust_tier == TrustTier.TRUSTED


def test_req_ssq_002_rollback_restores_prior_trusted(orch, spine, skills_dir):
    result = run_self_scaffold_queue_e2e(
        orch, spine=spine, session_id="sess_ssq002", with_rollback_baseline=True
    )
    assert result["rollback_ok"] is True
    body = (skills_dir / "education-wiki-notes-index" / "SKILL.md").read_text(encoding="utf-8")
    assert "Prior Trusted" in body
    assert "Candidate skill" not in body
    after = spine.get(result["opened"]["record_id"])
    assert after.rolled_back is True


def test_req_ssq_003_trusted_only_no_auto_trust_next_job(orch, spine):
    opened = open_forge_candidate_from_education_gap(
        orch, spine=spine, session_id="sess_ssq003"
    )
    cap_id = opened["capability_id"]
    # Still candidate - standing next Job must NOT match it.
    blocked = next_job_resolve_uses_trusted(
        orch,
        intent=EDUCATION_GAP_ASK_RULE + " education wiki notes index",
        capability_id=cap_id,
        session_id="sess_ssq003_blocked",
    )
    assert blocked["uses_trusted_skill"] is False
    assert cap_id not in blocked["matched_capability_ids"]

    # Direct resolver proof: trusted_only filters candidates.
    resolver = orch._capability_resolver
    all_match = resolver.resolve(
        "education wiki notes index", trusted_only=False, limit=12
    )
    trusted_match = resolver.resolve(
        "education wiki notes index", trusted_only=True, limit=12
    )
    all_ids = {e.id for e in all_match.matched}
    trusted_ids = {e.id for e in trusted_match.matched}
    assert cap_id in all_ids
    assert cap_id not in trusted_ids


def test_req_ssq_004_education_gap_ask_forge_approve_next_job_uses(orch, spine):
    opened = open_forge_candidate_from_education_gap(
        orch, spine=spine, session_id="sess_ssq004"
    )
    assert opened["education_gap_ask"] if "education_gap_ask" in opened else opened.get("ok")
    assert opened["forge_queue_has_candidate"] is True
    assert opened["gap"]
    approved = sandbox_version_hitl_approve(
        orch, spine=spine, record_id=opened["record_id"]
    )
    assert approved["trust_tier"] == "trusted"
    # Reuse 251: parked job resumes same job_id when metadata present.
    fr = approved.get("forge_result") or {}
    assert fr.get("same_job") is True or fr.get("action") in {
        "forge_approve_resume",
        "promote_only",
    }
    assert fr.get("job_id") == opened["job_id"] or fr.get("same_job") is True

    next_res = next_job_resolve_uses_trusted(
        orch,
        intent=EDUCATION_GAP_ASK_RULE + " education wiki notes index",
        capability_id=opened["capability_id"],
        session_id="sess_ssq004_next",
    )
    assert next_res["uses_trusted_skill"] is True
    assert opened["capability_id"] in next_res["matched_capability_ids"]


def test_req_ssq_005_full_e2e_helper_ok(orch, spine):
    result = run_self_scaffold_queue_e2e(
        orch, spine=spine, session_id="sess_ssq005", with_rollback_baseline=True
    )
    assert result["ok"] is True
    assert result["no_auto_trust"] is True
    assert result["next_job"]["uses_trusted_skill"] is True
    assert result["rollback_ok"] is True


def test_req_ssq_003_orch_formulate_passes_trusted_only():
    import inspect
    from src.application.orchestration import job_phase_orchestrator as jpo

    src = inspect.getsource(jpo.JobPhaseOrchestrator.create_job_from_catalog_resolve)
    assert "trusted_only=True" in src