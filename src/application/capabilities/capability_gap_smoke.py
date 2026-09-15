"""Capability-Gap Smoke Loop [CARD-329].

Tests and verifies the complete anti-theatre loop:
1. Forced missing skill/tool path creates a durable Training Optimization candidate (persisted, restart-safe).
2. Approve registers candidate into trusted Training Optimization / Capability inventory.
3. Reject leaves trusted inventory completely unchanged.
4. Returns durable proof receipt (no toast-only Done).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.domain.capabilities.models import CapabilityKind, TrustTier
from src.domain.capabilities.scaffold import ScaffoldPhase, utc_now_iso


def force_missing_capability_gap(
    *,
    gap_repo: Any,
    spine: Any,
    agent_id: str = "assistant",
    missing_tool: str,
    user_prompt: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Force a missing capability gap and stage a durable candidate in Forge queue [REQ-GAP-SMOKE-001]."""
    clean_tool = (missing_tool or "").strip()
    if not clean_tool:
        raise ValueError("missing_tool is required")

    prompt = (user_prompt or f"Execute command requiring {clean_tool}").strip()

    # 1. Persist durable gap row in agent_capability_gaps
    gap = gap_repo.create_gap(
        agent_id=agent_id,
        turn_text=prompt,
        identified_capability=f"Missing tool capability: {clean_tool}",
        suggested_tool_name=clean_tool,
        session_id=session_id,
    )

    # 2. Stage durable candidate in scaffold spine
    pack_id = f"tool_{clean_tool.lower().replace(' ', '_').replace('-', '_')}"
    record = spine.draft(
        kind=CapabilityKind.TOOL,
        name=clean_tool,
        pack_id=pack_id,
        summary=f"Automated candidate scaffold for {clean_tool}",
        content=f"# Tool: {clean_tool}\n\nCandidate implementation for missing capability gap {gap.id}.\n",
        metadata={
            "gap_id": gap.id,
            "agent_id": agent_id,
            "smoke_card": "CARD-329",
            "forced": True,
        },
    )

    return {
        "success": True,
        "gap_id": gap.id,
        "record_id": record.id,
        "agent_id": agent_id,
        "missing_tool": clean_tool,
        "status": "pending",
        "trust_tier": "candidate",
        "timestamp": utc_now_iso(),
    }


def approve_capability_candidate(
    *,
    gap_repo: Any,
    spine: Any,
    record_id: str,
    gap_id: Optional[str] = None,
    evidence: str = "capability_gap_smoke_exec",
) -> Dict[str, Any]:
    """Approve and promote candidate to trusted inventory [REQ-GAP-SMOKE-002]."""
    # Advance candidate through sandbox_exec and version
    spine.mark_sandbox_exec(record_id, evidence=evidence)
    spine.version(record_id)
    promoted = spine.hitl_approve(record_id)

    # Update gap status to trained
    effective_gap_id = gap_id or promoted.metadata.get("gap_id")
    if effective_gap_id and gap_repo:
        gap_repo.update_gap_status(effective_gap_id, "trained")

    return {
        "success": True,
        "record_id": record_id,
        "gap_id": effective_gap_id,
        "trust_tier": "trusted",
        "phase": ScaffoldPhase.TRUSTED.value,
        "promoted_capability_id": promoted.capability_id,
        "timestamp": utc_now_iso(),
    }


def reject_capability_candidate(
    *,
    gap_repo: Any,
    spine: Any,
    record_id: str,
    gap_id: Optional[str] = None,
    reason: str = "",
) -> Dict[str, Any]:
    """Reject candidate, ensuring trusted inventory remains unchanged [REQ-GAP-SMOKE-003]."""
    rej_reason = reason or "Operator declined capability candidate"
    rejected = spine.hitl_reject(record_id, reason=rej_reason)

    effective_gap_id = gap_id or rejected.metadata.get("gap_id")
    if effective_gap_id and gap_repo:
        gap_repo.update_gap_status(effective_gap_id, "dismissed")

    return {
        "success": True,
        "record_id": record_id,
        "gap_id": effective_gap_id,
        "status": "rejected",
        "trust_tier": "candidate",
        "reason": rej_reason,
        "timestamp": utc_now_iso(),
    }


def run_capability_gap_smoke(
    *,
    gap_repo: Any,
    spine: Any,
    agent_id: str = "assistant",
) -> Dict[str, Any]:
    """Execute end-to-end capability gap smoke proof [REQ-GAP-SMOKE-004]."""
    # Record baseline trusted inventory
    initial_trusted = spine.capability_repo.list_entries(trust_tier=TrustTier.TRUSTED)
    initial_count = len(initial_trusted)

    # Step 1: Force missing tool for rejection test
    forced_rej = force_missing_capability_gap(
        gap_repo=gap_repo,
        spine=spine,
        agent_id=agent_id,
        missing_tool="smoke_test_rejected_tool",
        user_prompt="Run an operation requiring smoke_test_rejected_tool",
    )
    assert forced_rej["success"] is True
    rec_rej_id = forced_rej["record_id"]
    gap_rej_id = forced_rej["gap_id"]

    # Step 2: Reject candidate and assert inventory unchanged
    rej_receipt = reject_capability_candidate(
        gap_repo=gap_repo,
        spine=spine,
        record_id=rec_rej_id,
        gap_id=gap_rej_id,
        reason="Declined during smoke verification",
    )
    assert rej_receipt["status"] == "rejected"

    trusted_after_rej = spine.capability_repo.list_entries(trust_tier=TrustTier.TRUSTED)
    if len(trusted_after_rej) != initial_count:
        raise AssertionError("Inventory changed after candidate rejection!")

    # Step 3: Force missing tool for approval test
    forced_app = force_missing_capability_gap(
        gap_repo=gap_repo,
        spine=spine,
        agent_id=agent_id,
        missing_tool="smoke_test_approved_tool",
        user_prompt="Run an operation requiring smoke_test_approved_tool",
    )
    assert forced_app["success"] is True
    rec_app_id = forced_app["record_id"]
    gap_app_id = forced_app["gap_id"]

    # Step 4: Approve candidate and assert inventory updated
    app_receipt = approve_capability_candidate(
        gap_repo=gap_repo,
        spine=spine,
        record_id=rec_app_id,
        gap_id=gap_app_id,
        evidence="smoke_test_verified_execution",
    )
    assert app_receipt["trust_tier"] == "trusted"

    trusted_after_app = spine.capability_repo.list_entries(trust_tier=TrustTier.TRUSTED)
    if len(trusted_after_app) != initial_count + 1:
        raise AssertionError("Inventory was not updated with approved candidate!")

    return {
        "passed": True,
        "agent_id": agent_id,
        "force_gap_receipt": forced_app,
        "reject_receipt": rej_receipt,
        "approve_receipt": app_receipt,
        "inventory_integrity_verified": True,
        "initial_trusted_count": initial_count,
        "final_trusted_count": len(trusted_after_app),
        "timestamp": utc_now_iso(),
    }
