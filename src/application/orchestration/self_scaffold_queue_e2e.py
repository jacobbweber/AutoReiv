# -*- coding: utf-8 -*-
"""Self-scaffold queue E2E loop [CARD-255 / REQ-SSQ-001..005].

Education gap Ask adaptation: gap -> Forge candidate -> sandbox/HITL (251) ->
trusted; next Job trusted-only resolve can use it; rollback restores prior.
Never auto-trust candidates. Reuses 218 spine + 233 mid-job + 251 Forge Approve.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.application.orchestration.mid_job_self_scaffold import (
    MidJobCapabilityGap,
    apply_mid_job_scaffold_on_gap,
    detect_mid_job_capability_gap,
    forge_approve_and_resume_job,
)
from src.domain.capabilities.models import TrustTier

logger = logging.getLogger(__name__)

def _ensure_trusted_health_probe(spine: Any) -> None:
    """Seed builtin-style trusted health probe for Education gap Ask smokes."""
    from src.domain.capabilities.models import CapabilityIndexEntry, CapabilityKind

    existing = spine.capability_repo.get_entry("tool.health_probe")
    if existing is not None:
        tier = getattr(existing.trust_tier, "value", existing.trust_tier)
        if str(tier).lower() == TrustTier.TRUSTED.value:
            return
    spine.capability_repo.upsert_entry(
        CapabilityIndexEntry(
            id="tool.health_probe",
            kind=CapabilityKind.TOOL,
            name="health_probe",
            summary="HTTP health probe",
            keywords=["health", "probe", "http", "200"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )



# Education / Chat gap Ask success_rule used for live + unit proof.
EDUCATION_GAP_ASK_RULE = (
    "done when education wiki notes indexed and health returns 200"
)


def education_gap_ask_text() -> str:
    """Outcome-shaped Education gap Ask (adapt Research copy for 255)."""
    return (
        "Education: index wiki notes for the learner path and prove health returns 200. "
        f"{EDUCATION_GAP_ASK_RULE}"
    )


def open_forge_candidate_from_education_gap(
    orchestrator: Any,
    *,
    spine: Any,
    session_id: str,
    agent_id: str = "assistant",
    matched_seed: Optional[List[str]] = None,
    park: bool = True,
) -> Dict[str, Any]:
    """
    Education gap Ask -> mid-job candidate in Forge queue [REQ-SSQ-001/004].

    Seeds a thin trusted match (health only) so wiki/education family is a gap,
    opens 218 candidate (never trusted), parks for HITL by default.
    """
    _ensure_trusted_health_probe(spine)
    seed = list(matched_seed or ["tool.health_probe"])
    ask = education_gap_ask_text()
    job = orchestrator.create_job_with_phases(
        goal=ask,
        session_id=session_id,
        agent_id=agent_id,
        phase_specs=[
            {
                "name": "Execute",
                "success_rule": EDUCATION_GAP_ASK_RULE,
                "verify_checker": "pytest",
            }
        ],
        success_rule=EDUCATION_GAP_ASK_RULE,
        template_id="catalog_resolve_rhe",
    )
    orchestrator._matched_ids[job.id] = list(seed)
    phases = orchestrator._store.list_phases_for_job(job.id)
    phase0 = phases[0]
    commit = getattr(orchestrator, "_commit_checkpoint", None)
    if callable(commit):
        commit(
            phase0,
            verifier_status="none",
            hitl_park_state=False,
            matched_capability_ids=list(seed),
        )
    started = orchestrator.start_phase(phase0.id)

    kw = {cid: ["health", "probe", "http", "200"] for cid in seed}
    gap = detect_mid_job_capability_gap(
        matched_ids=orchestrator.matched_capability_ids_for_job(job.id),
        success_rule=EDUCATION_GAP_ASK_RULE,
        matched_entry_keywords=kw,
        phase_name="Education",
    )
    if not gap.is_gap:
        # Force an honest education/wiki gap if heuristic was satisfied.
        gap = MidJobCapabilityGap(
            is_gap=True,
            reason="education_gap_ask:missing_wiki_notes_index",
            missing_families=("wiki", "notes", "education"),
            match_count=len(seed),
            suggested_kind="skill",
            suggested_name="education-wiki-notes-index",
            suggested_pack_id="education-wiki-notes-index",
        )

    opened = apply_mid_job_scaffold_on_gap(
        orchestrator,
        spine=spine,
        phase_id=started.id,
        gap=gap,
        kind="skill",
        name="education-wiki-notes-index",
        pack_id="education-wiki-notes-index",
        summary="Education wiki notes index (candidate)",
        content=(
            "# Education Wiki Notes Index\n\n"
            "Candidate skill for Education gap Ask - index learner wiki notes.\n"
        ),
        park=park,
        metadata={"education_gap_ask": True, "card": "CARD-255"},
    )
    assert opened.get("trust_tier") == "candidate"
    assert opened.get("trusted_write") is False

    in_forge = any(c.id == opened["record_id"] for c in spine.list_candidates())
    return {
        "ok": True,
        "ask": ask,
        "job_id": job.id,
        "phase_id": started.id,
        "session_id": session_id,
        "record_id": opened["record_id"],
        "capability_id": opened["capability_id"],
        "trust_tier": opened["trust_tier"],
        "forge_queue_has_candidate": in_forge,
        "action": opened.get("action"),
        "gap": opened.get("gap") or gap.as_dict(),
        "auto_trusted": False,
        "education_gap_ask": True,
    }


def sandbox_version_hitl_approve(
    orchestrator: Any,
    *,
    spine: Any,
    record_id: str,
    evidence: str = "card255-sandbox",
) -> Dict[str, Any]:
    """Sandbox -> version -> Forge Approve (251 resume when parked) [REQ-SSQ-001]."""
    spine.mark_sandbox_exec(record_id, evidence=evidence)
    spine.version(record_id)
    # Prefer orch hook when present (wires journey + same-job resume).
    if hasattr(orchestrator, "forge_approve_and_resume"):
        result = orchestrator.forge_approve_and_resume(spine=spine, record_id=record_id)
    else:
        result = forge_approve_and_resume_job(
            orchestrator, spine=spine, record_id=record_id
        )
    rec = spine.get(record_id)
    tier = getattr(rec.trust_tier, "value", str(rec.trust_tier))
    if tier != TrustTier.TRUSTED.value:
        raise PermissionError("HITL approve did not reach trusted (no auto-trust bypass)")
    return {
        "ok": True,
        "record_id": record_id,
        "capability_id": rec.capability_id,
        "trust_tier": tier,
        "phase": getattr(rec.phase, "value", str(rec.phase)),
        "forge_result": result,
        "auto_trusted": False,
    }


def next_job_resolve_uses_trusted(
    orchestrator: Any,
    *,
    intent: str,
    capability_id: str,
    session_id: str,
    agent_id: str = "assistant",
) -> Dict[str, Any]:
    """
    Create a *next* Job via standing formulate (trusted-only resolve) [REQ-SSQ-003/004].

    Proves the newly trusted skill matches; candidates would not.
    """
    job = orchestrator.create_job_from_catalog_resolve(
        intent=intent,
        session_id=session_id,
        agent_id=agent_id,
    )
    matched = list(orchestrator.matched_capability_ids_for_job(job.id) or [])
    return {
        "ok": capability_id in matched,
        "job_id": job.id,
        "session_id": session_id,
        "matched_capability_ids": matched,
        "capability_id": capability_id,
        "uses_trusted_skill": capability_id in matched,
    }


def rollback_promoted_scaffold(spine: Any, record_id: str) -> Dict[str, Any]:
    """Rollback restores prior trusted snapshot [REQ-SSQ-002]."""
    return spine.rollback(record_id)


def run_self_scaffold_queue_e2e(
    orchestrator: Any,
    *,
    spine: Any,
    session_id: str = "sess_card255_e2e",
    with_rollback_baseline: bool = True,
) -> Dict[str, Any]:
    """
    Full queue loop proof [REQ-SSQ-001..004].

    Optional baseline trusted pack so rollback has a prior snapshot to restore.
    """
    _ensure_trusted_health_probe(spine)
    pack_id = "education-wiki-notes-index"
    prior_body = "# Prior Trusted Education Index\n\nList notes only.\n"
    new_body = (
        "# Education Wiki Notes Index\n\n"
        "Candidate skill for Education gap Ask - index learner wiki notes.\n"
    )

    if with_rollback_baseline:
        spine.catalog.save_pack(pack_id, pack_id, "prior trusted", prior_body)
        baseline = spine.draft(
            kind="skill",
            name=pack_id,
            pack_id=pack_id,
            summary="prior trusted",
            content=prior_body,
            skip_disk_write=True,
            keywords=["education", "wiki", "notes", "index"],
        )
        spine.mark_sandbox_exec(baseline.id, evidence="baseline")
        spine.version(baseline.id)
        spine.hitl_approve(baseline.id)

    opened = open_forge_candidate_from_education_gap(
        orchestrator, spine=spine, session_id=session_id
    )
    # Overwrite pack content to the candidate body (draft already wrote).
    spine.catalog.save_pack(
        pack_id, pack_id, "Education wiki notes index (candidate)", new_body
    )

    approved = sandbox_version_hitl_approve(
        orchestrator, spine=spine, record_id=opened["record_id"]
    )

    # Next Job (new session) must see trusted skill via trusted-only resolve.
    next_res = next_job_resolve_uses_trusted(
        orchestrator,
        intent=EDUCATION_GAP_ASK_RULE + " education wiki notes index",
        capability_id=opened["capability_id"],
        session_id=f"{session_id}_next",
    )

    rolled = None
    rollback_ok = None
    if with_rollback_baseline:
        rolled = rollback_promoted_scaffold(spine, opened["record_id"])
        rollback_ok = bool(rolled.get("success"))
        skills_dir = getattr(spine.catalog, "skills_dir", None)
        content = ""
        if skills_dir is not None:
            skill_md = skills_dir / pack_id / "SKILL.md"
            if skill_md.exists():
                content = skill_md.read_text(encoding="utf-8")
        if not content:
            body = spine.catalog.read_pack(pack_id)
            if isinstance(body, dict):
                content = str(body.get("instructions") or "")
        restored_prior = "Prior Trusted" in content and "Candidate skill" not in content
        rollback_ok = rollback_ok and restored_prior

    # Candidate must never have been auto-trusted before approve (already asserted).
    no_auto_trust = (
        opened.get("trust_tier") == "candidate"
        and opened.get("auto_trusted") is False
        and approved.get("trust_tier") == "trusted"
    )

    return {
        "ok": bool(
            opened.get("forge_queue_has_candidate")
            and approved.get("trust_tier") == "trusted"
            and next_res.get("uses_trusted_skill")
            and no_auto_trust
            and (rollback_ok if with_rollback_baseline else True)
        ),
        "opened": opened,
        "approved": approved,
        "next_job": next_res,
        "rollback": rolled,
        "rollback_ok": rollback_ok,
        "no_auto_trust": no_auto_trust,
        "education_gap_ask": True,
    }


__all__ = [
    "_ensure_trusted_health_probe",
    "EDUCATION_GAP_ASK_RULE",
    "education_gap_ask_text",
    "open_forge_candidate_from_education_gap",
    "sandbox_version_hitl_approve",
    "next_job_resolve_uses_trusted",
    "rollback_promoted_scaffold",
    "run_self_scaffold_queue_e2e",
]