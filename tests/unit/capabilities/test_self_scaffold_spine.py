"""CARD-218 Self-Scaffold Spine [REQ-SCAFFOLD-001..008].

Red→green: candidate cannot run unsandboxed; rollback restores prior trusted.
Cite: SoK Agentic Skills arXiv 2602.20867.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.capabilities.scaffold_spine import (
    CandidateUnsandboxedError,
    SelfScaffoldSpine,
    UnscopedTrustedWriteError,
)
from src.application.skills.user_catalog import UserSkillCatalog
from src.domain.capabilities.models import TrustTier
from src.domain.capabilities.scaffold import ScaffoldPhase
from src.infrastructure.memory.repositories.capability_catalog import CapabilityCatalogRepository
from src.infrastructure.memory.repositories.scaffold_spine import ScaffoldSpineRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers import capabilities as capabilities_router_mod


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
def spine(temp_db_path, skills_dir):
    store = SQLiteStateStore(db_path=temp_db_path)
    catalog = UserSkillCatalog(skills_dir=skills_dir)
    cap_repo = CapabilityCatalogRepository(store)
    spine_repo = ScaffoldSpineRepository(store)
    return SelfScaffoldSpine(
        spine_repo=spine_repo,
        capability_repo=cap_repo,
        catalog=catalog,
    )


def test_req_scaffold_001_draft_always_candidate(spine):
    rec = spine.draft(
        kind="skill",
        name="wiki-helper",
        summary="Draft wiki helper skill",
        pack_id="wiki-helper",
        content="# Wiki Helper\n\nSearch notes.\n",
    )
    assert rec.phase == ScaffoldPhase.DRAFT
    assert rec.trust_tier == TrustTier.CANDIDATE
    assert rec.sandboxed is False
    entry = spine.capability_repo.get_entry(rec.capability_id)
    assert entry is not None
    assert entry.trust_tier == TrustTier.CANDIDATE


def test_req_scaffold_003_candidate_cannot_run_unsandboxed(spine):
    rec = spine.draft(
        kind="tool",
        name="scratch_tool",
        summary="candidate tool",
        pack_id="scratch-tool",
        content="# Scratch\n",
    )
    with pytest.raises(CandidateUnsandboxedError, match="cannot run unsandboxed"):
        spine.assert_can_run(rec.id)
    # After sandbox mark, run gate passes (thin slice: honest sandboxed flag).
    spine.mark_sandbox_exec(rec.id, evidence="unit-sandbox-ok")
    spine.assert_can_run(rec.id)


def test_req_scaffold_004_rollback_restores_prior_trusted(spine, skills_dir):
    # Seed a trusted pack on disk + catalog entry.
    pack_id = "okta-admin"
    spine.catalog.save_pack(
        pack_id,
        "okta-admin",
        "Prior trusted playbook",
        "# Prior Trusted\n\nList users only.\n",
    )
    trusted = spine.draft(
        kind="skill",
        name="okta-admin",
        summary="prior",
        pack_id=pack_id,
        content="# Prior Trusted\n\nList users only.\n",
        skip_disk_write=True,
    )
    # Force promote baseline to trusted for rollback target.
    spine.mark_sandbox_exec(trusted.id, evidence="baseline")
    spine.version(trusted.id)
    spine.hitl_approve(trusted.id)
    baseline = spine.get(trusted.id)
    assert baseline.phase == ScaffoldPhase.TRUSTED
    assert baseline.trust_tier == TrustTier.TRUSTED
    prior_body = (skills_dir / pack_id / "SKILL.md").read_text(encoding="utf-8")
    assert "Prior Trusted" in prior_body

    # New candidate revision overwrites pack content after full path.
    cand = spine.draft(
        kind="skill",
        name="okta-admin",
        summary="candidate rewrite",
        pack_id=pack_id,
        content="# Candidate Rewrite\n\nDangerous reset.\n",
    )
    spine.mark_sandbox_exec(cand.id, evidence="sandbox")
    spine.version(cand.id)
    spine.hitl_approve(cand.id)
    rewritten = (skills_dir / pack_id / "SKILL.md").read_text(encoding="utf-8")
    assert "Candidate Rewrite" in rewritten

    rolled = spine.rollback(cand.id)
    assert rolled['success'] is True
    restored = (skills_dir / pack_id / "SKILL.md").read_text(encoding="utf-8")
    assert "Prior Trusted" in restored
    assert "Candidate Rewrite" not in restored
    entry = spine.capability_repo.get_entry(cand.capability_id)
    assert entry.trust_tier == TrustTier.TRUSTED
    after = spine.get(cand.id)
    assert after.phase == ScaffoldPhase.TRUSTED
    assert after.rolled_back is True


def test_req_scaffold_005_unscoped_trusted_write_rejected(spine):
    with pytest.raises(UnscopedTrustedWriteError, match="reject"):
        spine.write_trusted_unscoped(
            kind="skill",
            name="evil",
            pack_id="evil",
            content="# Evil\n",
        )


def test_req_scaffold_002_lifecycle_phases(spine):
    rec = spine.draft(
        kind="skill",
        name="demo",
        summary="demo",
        pack_id="demo-pack",
        content="# Demo\n",
    )
    assert rec.phase == ScaffoldPhase.DRAFT
    rec = spine.mark_sandbox_exec(rec.id, evidence="ok")
    assert rec.phase == ScaffoldPhase.SANDBOX_EXEC
    assert rec.sandboxed is True
    rec = spine.version(rec.id)
    assert rec.phase == ScaffoldPhase.VERSIONED
    assert rec.snapshot_id
    rec = spine.hitl_approve(rec.id)
    assert rec.phase == ScaffoldPhase.TRUSTED
    assert rec.trust_tier == TrustTier.TRUSTED


def test_api_forge_candidate_queue_and_gates(temp_db_path, skills_dir):
    store = SQLiteStateStore(db_path=temp_db_path)
    catalog = UserSkillCatalog(skills_dir=skills_dir)
    cap_repo = CapabilityCatalogRepository(store)
    spine_repo = ScaffoldSpineRepository(store)
    spine = SelfScaffoldSpine(
        spine_repo=spine_repo,
        capability_repo=cap_repo,
        catalog=catalog,
    )
    app = FastAPI()
    app.state.store = store
    app.state.scaffold_spine = spine
    app.state.capability_catalog_repo = cap_repo
    app.include_router(capabilities_router_mod.router)
    client = TestClient(app)

    created = client.post(
        "/api/capabilities/scaffold/draft",
        json={
            "kind": "skill",
            "name": "queue-demo",
            "summary": "forge queue",
            "pack_id": "queue-demo",
            "content": "# Queue Demo\n",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["record"]["trust_tier"] == "candidate"
    rid = body["record"]["id"]

    run_bad = client.post(f"/api/capabilities/scaffold/{rid}/assert-run")
    assert run_bad.status_code == 409
    assert "unsandboxed" in run_bad.json()["detail"].lower()

    queue = client.get("/api/capabilities/scaffold/candidates")
    assert queue.status_code == 200
    qbody = queue.json()
    assert qbody["forge_queue"] is True
    assert any(r["id"] == rid for r in qbody["candidates"])

    sb = client.post(
        f"/api/capabilities/scaffold/{rid}/sandbox",
        json={"evidence": "api-sandbox"},
    )
    assert sb.status_code == 200
    run_ok = client.post(f"/api/capabilities/scaffold/{rid}/assert-run")
    assert run_ok.status_code == 200

    reject = client.post(
        "/api/capabilities/scaffold/write-trusted",
        json={
            "kind": "skill",
            "name": "nope",
            "pack_id": "nope",
            "content": "# Nope\n",
        },
    )
    assert reject.status_code == 400
