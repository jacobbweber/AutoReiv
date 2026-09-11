"""CARD-233 Mid-job self-scaffold via 218 spine [REQ-SCAFFOLD-001..005].

Gap -> candidate via 218 (not trusted); HITL before trusted; no silent candidate-as-trusted;
park or continue-with-matched-only until promote; after HITL -> re-resolve updates matched IDs;
journey scaffold_candidate + HITL + re-resolve spans; reject unscoped trusted write mid-phase.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.capabilities.scaffold_spine import (
    SelfScaffoldSpine,
    UnscopedTrustedWriteError,
)
from src.application.observability.standing_journey import build_standing_journey
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.mid_job_self_scaffold import (
    apply_mid_job_scaffold_on_gap,
    assert_candidate_not_trusted,
    detect_mid_job_capability_gap,
    promote_scaffold_and_reresolve,
    reject_unscoped_trusted_write_mid_phase,
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


def _running_job_with_gap(orch, store, *, session_id: str, matched=None):
    job = orch.create_job_with_phases(
        goal="mid-job scaffold proof",
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
    ids = list(matched if matched is not None else ["tool.health_probe"])
    orch._matched_ids[job.id] = list(ids)
    phases = store.list_phases_for_job(job.id)
    orch._commit_checkpoint(
        phases[0],
        verifier_status="none",
        hitl_park_state=False,
        matched_capability_ids=ids,
    )
    started = orch.start_phase(phases[0].id)
    return store.get_job(job.id), started


def test_detect_mid_job_capability_gap_when_family_missing():
    gap = detect_mid_job_capability_gap(
        matched_ids=["tool.health_probe"],
        success_rule="done when wiki notes indexed and health returns 200",
        matched_entry_keywords={"tool.health_probe": ["health", "probe", "http", "200"]},
    )
    assert gap.is_gap is True
    assert "wiki" in gap.missing_families or gap.reason


def test_detect_no_gap_when_sufficient():
    gap = detect_mid_job_capability_gap(
        matched_ids=["tool.health_probe", "skill.wiki_index"],
        success_rule="done when wiki notes indexed and health returns 200",
        matched_entry_keywords={
            "tool.health_probe": ["health", "probe", "http", "200"],
            "skill.wiki_index": ["wiki", "notes", "index", "search"],
        },
    )
    assert gap.is_gap is False


def test_req_scaffold_001_gap_opens_candidate_via_218_not_trusted(orch, store, spine):
    _seed_trusted_probe(spine)
    job, phase = _running_job_with_gap(orch, store, session_id="sess_s001")
    gap = detect_mid_job_capability_gap(
        matched_ids=orch.matched_capability_ids_for_job(job.id),
        success_rule=job.success_rule,
        matched_entry_keywords={"tool.health_probe": ["health", "probe", "http", "200"]},
    )
    assert gap.is_gap is True

    result = apply_mid_job_scaffold_on_gap(
        orch,
        spine=spine,
        phase_id=phase.id,
        gap=gap,
        kind="skill",
        name="wiki-notes-index",
        pack_id="wiki-notes-index",
        summary="Index wiki notes for standing job",
        content="# Wiki Notes Index\n\nSearch and index notes.\n",
        park=True,
    )
    assert result["ok"] is True
    assert result["trust_tier"] == "candidate"
    assert result["phase"] == "draft"
    assert result.get("trusted_write") is False
    rec = spine.get(result["record_id"])
    assert rec.trust_tier == TrustTier.CANDIDATE
    assert rec.phase == ScaffoldPhase.DRAFT
    entry = spine.capability_repo.get_entry(rec.capability_id)
    assert entry is not None
    assert entry.trust_tier == TrustTier.CANDIDATE


def test_req_scaffold_002_path_hitl_before_trusted_then_reresolve(orch, store, spine):
    _seed_trusted_probe(spine)
    job, phase = _running_job_with_gap(orch, store, session_id="sess_s002")
    gap = detect_mid_job_capability_gap(
        matched_ids=orch.matched_capability_ids_for_job(job.id),
        success_rule=job.success_rule,
        matched_entry_keywords={"tool.health_probe": ["health", "probe", "http", "200"]},
    )
    opened = apply_mid_job_scaffold_on_gap(
        orch,
        spine=spine,
        phase_id=phase.id,
        gap=gap,
        kind="skill",
        name="wiki-notes-index",
        pack_id="wiki-notes-index",
        summary="Index wiki notes",
        content="# Wiki Notes Index\n",
        park=True,
    )
    rid = opened["record_id"]
    before = orch.matched_capability_ids_for_job(job.id)
    assert opened["capability_id"] not in before

    spine.mark_sandbox_exec(rid, evidence="unit-sandbox")
    spine.version(rid)
    promoted = promote_scaffold_and_reresolve(
        orch,
        spine=spine,
        job_id=job.id,
        record_id=rid,
        intent=job.success_rule or job.goal,
    )
    assert promoted["ok"] is True
    assert promoted["trust_tier"] == "trusted"
    rec = spine.get(rid)
    assert rec.phase == ScaffoldPhase.TRUSTED
    assert rec.trust_tier == TrustTier.TRUSTED
    after = orch.matched_capability_ids_for_job(job.id)
    assert rec.capability_id in after
    cp = orch.get_latest_checkpoint(job.id)
    assert rec.capability_id in list(cp.matched_capability_ids)


def test_req_scaffold_002_reject_unscoped_trusted_write_mid_phase(spine):
    with pytest.raises(UnscopedTrustedWriteError):
        reject_unscoped_trusted_write_mid_phase(
            spine, kind="skill", name="evil", pack_id="evil"
        )


def test_req_scaffold_003_park_until_promote_no_silent_candidate_trusted(orch, store, spine):
    _seed_trusted_probe(spine)
    job, phase = _running_job_with_gap(orch, store, session_id="sess_s003")
    gap = detect_mid_job_capability_gap(
        matched_ids=orch.matched_capability_ids_for_job(job.id),
        success_rule=job.success_rule,
        matched_entry_keywords={"tool.health_probe": ["health", "probe", "http", "200"]},
    )
    result = apply_mid_job_scaffold_on_gap(
        orch,
        spine=spine,
        phase_id=phase.id,
        gap=gap,
        kind="skill",
        name="wiki-notes-index",
        pack_id="wiki-notes-index",
        summary="Index wiki notes",
        content="# Wiki\n",
        park=True,
    )
    assert result["action"] == "park"
    assert store.get_phase(phase.id).status == PhaseStatus.WAITING_APPROVAL
    assert store.get_job(job.id).status == JobStatus.WAITING_APPROVAL
    with pytest.raises(PermissionError):
        assert_candidate_not_trusted(spine, result["record_id"])
    assert orch.matched_capability_ids_for_job(job.id) == ["tool.health_probe"]


def test_req_scaffold_003_continue_with_matched_only(orch, store, spine):
    _seed_trusted_probe(spine)
    job, phase = _running_job_with_gap(orch, store, session_id="sess_s003b")
    gap = detect_mid_job_capability_gap(
        matched_ids=orch.matched_capability_ids_for_job(job.id),
        success_rule=job.success_rule,
        matched_entry_keywords={"tool.health_probe": ["health", "probe", "http", "200"]},
    )
    result = apply_mid_job_scaffold_on_gap(
        orch,
        spine=spine,
        phase_id=phase.id,
        gap=gap,
        kind="skill",
        name="wiki-notes-index",
        pack_id="wiki-notes-index",
        summary="Index wiki notes",
        content="# Wiki\n",
        park=False,
    )
    assert result["action"] == "continue_matched_only"
    assert store.get_phase(phase.id).status == PhaseStatus.RUNNING
    assert store.get_job(job.id).status == JobStatus.RUNNING
    assert result["capability_id"] not in orch.matched_capability_ids_for_job(job.id)
    with pytest.raises(PermissionError):
        assert_candidate_not_trusted(spine, result["record_id"])


def test_req_scaffold_004_journey_spans_and_forge_queue(orch, store, spine):
    _seed_trusted_probe(spine)
    job, phase = _running_job_with_gap(orch, store, session_id="sess_s004")
    gap = detect_mid_job_capability_gap(
        matched_ids=orch.matched_capability_ids_for_job(job.id),
        success_rule=job.success_rule,
        matched_entry_keywords={"tool.health_probe": ["health", "probe", "http", "200"]},
    )
    opened = apply_mid_job_scaffold_on_gap(
        orch,
        spine=spine,
        phase_id=phase.id,
        gap=gap,
        kind="skill",
        name="wiki-notes-index",
        pack_id="wiki-notes-index",
        summary="Index wiki notes",
        content="# Wiki\n",
        park=True,
    )
    rid = opened["record_id"]
    candidates = spine.list_candidates()
    assert any(c.id == rid for c in candidates)

    spine.mark_sandbox_exec(rid, evidence="ok")
    spine.version(rid)
    promote_scaffold_and_reresolve(
        orch,
        spine=spine,
        job_id=job.id,
        record_id=rid,
        intent=job.success_rule or job.goal,
    )

    journey = build_standing_journey(store, job_id=job.id)
    assert journey["ok"] is True
    kinds = [t.get("kind") for t in journey.get("timeline") or []]
    span_names = [s.get("name") for s in journey.get("spans") or []]
    assert "scaffold_candidate" in kinds or any(
        "scaffold_candidate" in str(n) for n in span_names
    ), (kinds, span_names)
    assert (
        "scaffold_hitl" in kinds
        or "hitl" in kinds
        or any("hitl" in str(n) for n in span_names)
    ), (kinds, span_names)
    assert (
        "catalog_reresolve" in kinds
        or "re_resolve" in kinds
        or any(
            "reresolve" in str(n).replace("-", "_") or "re_resolve" in str(n)
            for n in span_names
        )
    ), (kinds, span_names)


def test_req_scaffold_005_extends_standing_no_second_product():
    import inspect

    from src.application.orchestration import mid_job_self_scaffold as mjs

    assert not hasattr(mjs, "MidJobScaffoldOrchestrator")
    assert not hasattr(mjs, "SecondScaffoldProduct")
    src = inspect.getsource(mjs)
    assert "SelfScaffoldSpine" in src or "spine.draft" in src
    assert "write_trusted_unscoped" in src or "UnscopedTrustedWrite" in src
