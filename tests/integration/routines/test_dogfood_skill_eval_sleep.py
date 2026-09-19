"""
End-to-End Dogfooding Integration Test Suite for Overnight Skill Improvement [CARD-372].
Validates the full harvest-to-approval lifecycle:
1. Synthetic failed turns harvesting within lookback window.
2. Gap mining and clustering into bounded insights.
3. Safety checker gates (refusing python src rewrites and missing pack IDs).
4. Uncommitted proposal creation in SQLite with pre-change snapshot.
5. Operator approval and clean SKILL.md update without frontmatter corruption.
6. Bit-for-bit snapshot rollback.
7. Zero writes to checkout src/ or repo root.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from src.application.orchestration.skill_proposals import (
    apply_skill_proposal_decision,
    commit_skill_pack,
)
from src.application.routines.skill_eval_sleep import (
    AGENT_ID,
    MAX_INSIGHT_CHARS,
    ROUTINE_ID,
    harvest_failed_turns,
    harvest_gate,
    mine_pack_gaps,
    run_skill_eval_job,
)
from src.application.skills.linter import CapabilityLinter
from src.application.skills.user_catalog import UserSkillCatalog
from src.domain.orchestration.models import ProposalKind, ProposalStatus
from src.domain.telemetry.models import TelemetrySpan
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

SRC_ROOT = Path(__file__).resolve().parents[3] / "src"


@pytest.fixture
def dogfood_env(tmp_path):
    """Isolated environment with SQLite store, pack directory, and initialized SKILL.md."""
    store = SQLiteStateStore(db_path=tmp_path / "dogfood_state.db")
    store.initialize_db()

    data_dir = tmp_path / "user_data"
    skills_dir = data_dir / "skills"
    skills_dir.mkdir(parents=True)

    catalog = UserSkillCatalog(skills_dir=skills_dir)
    # Seed an active pack with Matt Pocock-compliant runbook
    pack_id = "wiki-curator"
    initial_instructions = """# Wiki Curator Runbook

Inspect and curate wiki notes in the knowledge vault.

## Available Tools
- `wiki_note_read`
- `wiki_note_update`

## Done-when
- Wiki note is reviewed and updated.
"""
    catalog.save_pack(
        pack_id=pack_id,
        name="Wiki Curator",
        description="Curates and refines wiki notes in the vault.",
        instructions=initial_instructions,
    )
    skill_path = skills_dir / pack_id / "SKILL.md"

    # Track src file mtimes to ensure no core code is touched
    src_mtimes = {p: p.stat().st_mtime_ns for p in SRC_ROOT.rglob("*.py") if "pycache" not in str(p)}

    return {
        "store": store,
        "data_dir": data_dir,
        "skills_dir": skills_dir,
        "catalog": catalog,
        "pack_id": pack_id,
        "skill_path": skill_path,
        "skill_before": skill_path.read_bytes(),
        "src_mtimes": src_mtimes,
    }


def _assert_src_untouched(dogfood_env):
    current_mtimes = {p: p.stat().st_mtime_ns for p in SRC_ROOT.rglob("*.py") if "pycache" not in str(p)}
    for p, orig_mtime in dogfood_env["src_mtimes"].items():
        assert current_mtimes.get(p) == orig_mtime, f"Source file {p} was unexpectedly modified!"


def test_harvest_and_mine_clusters_synthetic_failures(dogfood_env):
    """Verify synthetic failure turns in SQLite are harvested within lookback and mined into bounded gaps [CARD-372]."""
    store = dogfood_env["store"]
    pack_id = dogfood_env["pack_id"]
    now = datetime.now(timezone.utc)

    # 1. Seed 3 in-window failures for wiki_note_update
    for i in range(3):
        store.save_telemetry_span(
            TelemetrySpan(
                id=f"span_in_window_{i}",
                session_id=f"sess_{i}",
                agent_id="assistant",
                span_type="turn",
                name="turn",
                success=False,
                error_message="wiki_note_update failed: target path locked by concurrent session",
                metadata={"pack_id": pack_id, "tool_name": "wiki_note_update"},
                created_at=now - timedelta(hours=i * 2),
            )
        )

    # 2. Seed 1 out-of-window failure (96 hours ago > default 72h lookback)
    store.save_telemetry_span(
        TelemetrySpan(
            id="span_out_of_window",
            session_id="sess_old",
            agent_id="assistant",
            span_type="turn",
            name="turn",
            success=False,
            error_message="wiki_note_update failed: stale error",
            metadata={"pack_id": pack_id, "tool_name": "wiki_note_update"},
            created_at=now - timedelta(hours=96),
        )
    )

    # Harvest with 72h lookback
    harvested = harvest_failed_turns(store, lookback_hours=72, now=now)
    assert len(harvested) == 3
    span_ids = {h["span_id"] for h in harvested}
    assert "span_out_of_window" not in span_ids
    assert "span_in_window_0" in span_ids

    # Mine gaps
    candidates = mine_pack_gaps(harvested)
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand["pack_id"] == pack_id
    assert cand["tool_name"] == "wiki_note_update"
    assert cand["count"] == 3
    assert len(cand["insight"]) <= MAX_INSIGHT_CHARS
    assert "wiki_note_update" in cand["insight"] or "locked" in cand["insight"]


def test_harvest_gate_safety_blocks_python_src_and_missing_pack(dogfood_env):
    """Verify safety gate strictly fails closed on python src rewrites and missing pack IDs [CARD-372]."""
    # Case 1: Missing pack_id
    bad_candidate_1 = [
        {
            "pack_id": "",
            "tool_name": "cli_exec",
            "insight": "Fix error handling",
            "evidence": "Error in turn",
        }
    ]
    gate_res_1 = harvest_gate(bad_candidate_1)
    assert gate_res_1["passed"] is False
    assert gate_res_1["status"] == "fail"
    assert gate_res_1["reason"] == "missing pack_id"

    # Case 2: Attempting python src rewrite
    bad_candidate_2 = [
        {
            "pack_id": "core-pack",
            "tool_name": "code_tool",
            "insight": "Modify src/application/skills/wiki_tools.py to ignore file locks",
            "evidence": "src/application/kernel.py crashed",
        }
    ]
    gate_res_2 = harvest_gate(bad_candidate_2)
    assert gate_res_2["passed"] is False
    assert gate_res_2["status"] == "fail"
    assert gate_res_2["reason"] == "python src rewrite"

    # Case 3: Compliant operational runbook candidate
    good_candidate = [
        {
            "pack_id": dogfood_env["pack_id"],
            "tool_name": "wiki_note_update",
            "insight": "Retry with backoff when wiki_note_update indicates file contention",
            "evidence": "Lock contention observed across 3 turns",
        }
    ]
    gate_res_3 = harvest_gate(good_candidate)
    assert gate_res_3["passed"] is True
    assert gate_res_3["status"] == "pass"


def test_full_lifecycle_harvest_draft_approve_commit_rollback(dogfood_env):
    """Full end-to-end dogfooding: harvest -> draft -> approve -> commit -> verify -> rollback [CARD-372]."""
    store = dogfood_env["store"]
    data_dir = dogfood_env["data_dir"]
    catalog = dogfood_env["catalog"]
    pack_id = dogfood_env["pack_id"]
    skill_path = dogfood_env["skill_path"]
    skill_before = dogfood_env["skill_before"]
    now = datetime.now(timezone.utc)

    # 1. Seed synthetic failures
    for i in range(2):
        store.save_telemetry_span(
            TelemetrySpan(
                id=f"span_turn_{i}",
                session_id=f"sess_prod_{i}",
                agent_id="assistant",
                span_type="turn",
                name="turn",
                success=False,
                error_message="wiki_note_update returned lock collision on 01_Notes/index.md",
                metadata={"pack_id": pack_id, "tool_name": "wiki_note_update"},
                created_at=now - timedelta(minutes=15 * (i + 1)),
            )
        )

    # 2. Run the overnight skill-eval routine job
    result = run_skill_eval_job(
        store,
        data_dir,
        catalog=catalog,
        session_id="sess_nightly_dogfood",
        agent_id=AGENT_ID,
        now=now,
    )

    # Assert harvest results
    assert result["status"] == "success"
    assert result["harvested"] == 2
    assert result["skill_md_written"] is False
    assert result["disk_written"] is False
    assert result["src_written"] is False
    assert result["auto_commit"] is False
    assert result["proposal_id"] is not None
    assert result["snapshot_id"] is not None

    # Disk must be completely untouched at draft phase
    assert skill_path.read_bytes() == skill_before

    # Verify uncommitted proposal in SQLite
    proposal = store.get_proposal(result["proposal_id"])
    assert proposal is not None
    assert proposal.status == ProposalStatus.DRAFT
    assert proposal.kind == ProposalKind.SKILL
    payload = json.loads(proposal.payload_json)
    assert payload.get("routine_id") == ROUTINE_ID
    assert payload.get("ace_delta") is True
    assert payload.get("snapshot_id") == result["snapshot_id"]

    # 3. Operator Approves the Proposal
    decision_res = apply_skill_proposal_decision(
        store,
        proposal_id=result["proposal_id"],
        decision="approved",
        reason="Operator verified insight is actionable and safe.",
    )
    assert decision_res["status"] == "approved"
    approved_prop = store.get_proposal(result["proposal_id"])
    assert approved_prop.status == ProposalStatus.APPROVED
    # Disk still untouched on approval alone
    assert skill_path.read_bytes() == skill_before

    # 4. Commit Approved Proposal to Disk
    commit_res = commit_skill_pack(
        store,
        proposal_id=result["proposal_id"],
        data_dir=data_dir,
        catalog=catalog,
        overwrite=True,
    )
    assert commit_res["success"] is True
    assert commit_res["disk_written"] is True
    assert commit_res["src_written"] is False

    # 5. Verify Updated SKILL.md
    updated_bytes = skill_path.read_bytes()
    assert updated_bytes != skill_before
    updated_text = updated_bytes.decode("utf-8")

    # Verify frontmatter is clean and parseable
    frontmatter_dict = yaml.safe_load(updated_text.split("---")[1])
    assert frontmatter_dict["name"] == "Wiki Curator"
    assert "Curates and refines wiki notes" in frontmatter_dict["description"]

    # Verify existing instructions and appended operational learning
    assert "Inspect and curate wiki notes in the knowledge vault" in updated_text
    assert "## Operational Learnings" in updated_text
    assert "- " in updated_text

    # Verify CapabilityLinter passes with zero errors on updated SKILL.md
    linter = CapabilityLinter()
    contract, violations = linter.lint_file(skill_path)
    errors = [v for v in violations if v.severity.value == "error"]
    assert len(errors) == 0, f"Updated SKILL.md failed linting: {[v.message for v in errors]}"

    # 6. Revert / Rollback Proposal
    rolled = catalog.rollback_pack(pack_id, snapshot_id=result["snapshot_id"])
    assert rolled["success"] is True

    # Assert bit-for-bit restoration
    restored_bytes = skill_path.read_bytes()
    assert restored_bytes == skill_before

    # Restored SKILL.md must also pass linter
    contract_restored, violations_restored = linter.lint_file(skill_path)
    errors_restored = [v for v in violations_restored if v.severity.value == "error"]
    assert len(errors_restored) == 0

    # 7. Verify zero core source file modifications
    _assert_src_untouched(dogfood_env)
