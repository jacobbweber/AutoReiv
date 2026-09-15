"""Unit tests for CARD-329: Capability-gap smoke.

Tests:
1. REQ-GAP-SMOKE-001: Forced missing skill/tool produces a durable Training Optimization candidate (persisted, restart-safe).
2. REQ-GAP-SMOKE-002: Approve registers the candidate into Training Optimization inventory.
3. REQ-GAP-SMOKE-003: Reject leaves inventory unchanged.
4. REQ-GAP-SMOKE-004: Full smoke runner test_card329_capability_gap_smoke proves the entire loop.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.web.routers.capabilities as capabilities_router
from src.application.capabilities.capability_gap_smoke import (
    approve_capability_candidate,
    force_missing_capability_gap,
    reject_capability_candidate,
    run_capability_gap_smoke,
)
from src.application.capabilities.scaffold_spine import SelfScaffoldSpine
from src.application.skills.user_catalog import UserSkillCatalog
from src.domain.capabilities.models import TrustTier
from src.domain.capabilities.scaffold import ScaffoldPhase
from src.infrastructure.memory.repositories.capability_catalog import CapabilityCatalogRepository
from src.infrastructure.memory.repositories.capability_gaps import CapabilityGapRepository
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
    s = SQLiteStateStore(db_path=temp_db_path)
    s.initialize_db()
    return s


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
def gap_repo(store):
    return CapabilityGapRepository(connection_factory=store._get_connection)


def test_req_gap_smoke_001_forced_missing_tool_produces_durable_candidate(gap_repo, spine):
    """REQ-GAP-SMOKE-001: Forced missing tool creates durable gap row + durable spine candidate."""
    result = force_missing_capability_gap(
        gap_repo=gap_repo,
        spine=spine,
        agent_id="assistant",
        missing_tool="quantum_simulator",
        user_prompt="Run a quantum circuit simulation with 8 qubits",
    )

    assert result["success"] is True
    gap_id = result["gap_id"]
    record_id = result["record_id"]

    # Verify gap row in SQLite
    gap = gap_repo.get_gap(gap_id)
    assert gap is not None
    assert gap.agent_id == "assistant"
    assert gap.status == "pending"
    assert "quantum_simulator" in (gap.suggested_tool_name or "")

    # Verify candidate record in scaffold spine
    rec = spine.get(record_id)
    assert rec is not None
    assert rec.phase == ScaffoldPhase.DRAFT
    assert rec.trust_tier == TrustTier.CANDIDATE

    # Verify candidate appears in candidate list
    candidates = spine.list_candidates()
    assert any(c.id == record_id for c in candidates)


def test_req_gap_smoke_002_approve_registers_into_trusted_inventory(gap_repo, spine):
    """REQ-GAP-SMOKE-002: Approve registers the candidate into Training Optimization inventory."""
    # Create candidate
    forced = force_missing_capability_gap(
        gap_repo=gap_repo,
        spine=spine,
        agent_id="assistant",
        missing_tool="pdf_table_extractor",
        user_prompt="Extract tabular data from revenue report PDF",
    )
    rec_id = forced["record_id"]
    gap_id = forced["gap_id"]

    # Before approve, not in trusted inventory
    trusted_before = spine.capability_repo.list_entries(trust_tier=TrustTier.TRUSTED)
    assert not any("pdf_table_extractor" in (e.name or "") for e in trusted_before)

    # Approve
    app_res = approve_capability_candidate(
        gap_repo=gap_repo,
        spine=spine,
        record_id=rec_id,
        gap_id=gap_id,
    )
    assert app_res["success"] is True
    assert app_res["trust_tier"] == "trusted"

    # After approve, present in trusted inventory
    trusted_after = spine.capability_repo.list_entries(trust_tier=TrustTier.TRUSTED)
    assert any("pdf_table_extractor" in (e.name or "") for e in trusted_after)

    # Gap status updated
    gap = gap_repo.get_gap(gap_id)
    assert gap.status == "trained"


def test_req_gap_smoke_003_reject_leaves_inventory_unchanged(gap_repo, spine):
    """REQ-GAP-SMOKE-003: Reject leaves trusted inventory unchanged."""
    initial_trusted = spine.capability_repo.list_entries(trust_tier=TrustTier.TRUSTED)
    initial_count = len(initial_trusted)

    # Create candidate
    forced = force_missing_capability_gap(
        gap_repo=gap_repo,
        spine=spine,
        agent_id="assistant",
        missing_tool="malicious_unwanted_tool",
        user_prompt="Attempt dangerous operation",
    )
    rec_id = forced["record_id"]
    gap_id = forced["gap_id"]

    # Reject
    rej_res = reject_capability_candidate(
        gap_repo=gap_repo,
        spine=spine,
        record_id=rec_id,
        gap_id=gap_id,
        reason="Operator declined capability addition",
    )
    assert rej_res["success"] is True
    assert rej_res["status"] == "rejected"

    # Verify inventory is completely unchanged
    trusted_after = spine.capability_repo.list_entries(trust_tier=TrustTier.TRUSTED)
    assert len(trusted_after) == initial_count
    assert not any("malicious_unwanted_tool" in (e.name or "") for e in trusted_after)

    # Gap status updated to dismissed
    gap = gap_repo.get_gap(gap_id)
    assert gap.status == "dismissed"


def test_req_gap_smoke_004_full_smoke_runner(gap_repo, spine):
    """REQ-GAP-SMOKE-004: Comprehensive smoke runner executes full cycle and returns receipt."""
    receipt = run_capability_gap_smoke(
        gap_repo=gap_repo,
        spine=spine,
        agent_id="assistant",
    )
    assert receipt["passed"] is True
    assert "force_gap_receipt" in receipt
    assert "reject_receipt" in receipt
    assert "approve_receipt" in receipt
    assert receipt["inventory_integrity_verified"] is True


def test_api_capability_gap_smoke_endpoints(temp_db_path, skills_dir):
    """CARD-329 API integration: verify HTTP endpoints for force-gap, reject, and smoke loop."""
    store = SQLiteStateStore(db_path=temp_db_path)
    store.initialize_db()
    catalog = UserSkillCatalog(skills_dir=skills_dir)
    cap_repo = CapabilityCatalogRepository(store)
    spine_repo = ScaffoldSpineRepository(store)
    gap_repo = CapabilityGapRepository(connection_factory=store._get_connection)
    spine = SelfScaffoldSpine(
        spine_repo=spine_repo,
        capability_repo=cap_repo,
        catalog=catalog,
    )

    app = FastAPI()
    app.state.store = store
    app.state.scaffold_spine = spine
    app.state.capability_catalog_repo = cap_repo
    app.state.capability_gap_repo = gap_repo
    app.include_router(capabilities_router.router)
    client = TestClient(app)

    # 1. Force missing gap via API
    resp_force = client.post(
        "/api/capabilities/smoke/force-gap",
        json={
            "agent_id": "assistant",
            "missing_tool": "weather_radar",
            "user_prompt": "Check incoming storm radar",
        },
    )
    assert resp_force.status_code == 200
    forced = resp_force.json()
    assert forced["success"] is True
    rec_id = forced["record_id"]
    gap_id = forced["gap_id"]
    assert gap_id

    # 2. Reject via API
    resp_rej = client.post(
        f"/api/capabilities/scaffold/{rec_id}/reject",
        json={"reason": "Operator declined weather_radar"},
    )
    assert resp_rej.status_code == 200
    rej = resp_rej.json()
    assert rej["status"] == "rejected"
    assert gap_repo.get_gap(gap_id).status == "dismissed"

    # Verify inventory untouched
    trusted = cap_repo.list_entries(trust_tier=TrustTier.TRUSTED)
    assert not any("weather_radar" in (e.name or "") for e in trusted)

    # 3. Run full smoke loop via API
    resp_smoke = client.post(
        "/api/capabilities/smoke/gap-candidate-loop",
        json={"agent_id": "assistant"},
    )
    assert resp_smoke.status_code == 200
    receipt = resp_smoke.json()
    assert receipt["passed"] is True
    assert receipt["inventory_integrity_verified"] is True
