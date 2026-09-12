"""Mid-job self-scaffold via 218 spine [CARD-233 / REQ-SCAFFOLD-001..005].

When a running Job hits a capability gap (tool/skill missing for success_rule /
phase), standing runtime opens a **candidate** draft via SelfScaffoldSpine —
never writes trusted from a live phase.

Path: draft -> sandbox -> version -> HITL approve -> trusted -> catalog re-resolve
(update matched IDs on checkpoint). Until HITL promotes: park OR continue with
remaining matched capabilities only — no silent candidate-as-trusted.
Forge candidate queue remains the operator path.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.application.capabilities.scaffold_spine import (
    UnscopedTrustedWriteError,
)
from src.application.orchestration.research_before_plan import assess_catalog_match
from src.domain.capabilities.models import TrustTier
from src.domain.capabilities.scaffold import ScaffoldPhase

logger = logging.getLogger(__name__)

_PACK_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class MidJobCapabilityGap:
    """Detected mid-job capability gap for success_rule / phase."""

    is_gap: bool
    reason: str
    missing_families: tuple[str, ...] = field(default_factory=tuple)
    match_count: int = 0
    suggested_kind: str = "skill"
    suggested_name: str = ""
    suggested_pack_id: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "is_gap": self.is_gap,
            "reason": self.reason,
            "missing_families": list(self.missing_families),
            "match_count": self.match_count,
            "suggested_kind": self.suggested_kind,
            "suggested_name": self.suggested_name,
            "suggested_pack_id": self.suggested_pack_id,
        }


def _slug(text: str) -> str:
    s = _PACK_SLUG_RE.sub("-", (text or "").strip().lower()).strip("-")
    return (s or "scaffold-candidate")[:48]


def detect_mid_job_capability_gap(
    matched_ids: Sequence[str] | None,
    success_rule: str | None,
    *,
    matched_entry_keywords: Optional[Mapping[str, Sequence[str]]] = None,
    phase_name: str | None = None,
) -> MidJobCapabilityGap:
    """Reuse 231 thin/gap heuristic for a *running* job [REQ-SCAFFOLD-001]."""
    assessment = assess_catalog_match(
        matched_ids,
        success_rule,
        matched_entry_keywords=matched_entry_keywords,
    )
    if assessment.sufficient:
        return MidJobCapabilityGap(
            is_gap=False,
            reason=assessment.reason,
            missing_families=tuple(assessment.missing_families),
            match_count=assessment.match_count,
        )

    missing = tuple(f for f in assessment.missing_families if f and f != "all")
    hint = missing[0] if missing else "capability"
    name = f"{hint}-scaffold"
    if phase_name:
        name = f"{_slug(phase_name)}-{hint}"
    pack = _slug(name)
    kind = "tool" if hint in {"health", "verify", "execute"} else "skill"
    return MidJobCapabilityGap(
        is_gap=True,
        reason=assessment.reason,
        missing_families=tuple(assessment.missing_families),
        match_count=assessment.match_count,
        suggested_kind=kind,
        suggested_name=name,
        suggested_pack_id=pack,
    )


def _emit_journey(
    orchestrator: Any,
    *,
    job_id: str,
    kind: str,
    payload: Dict[str, Any],
) -> None:
    save_ev = getattr(getattr(orchestrator, "_store", None), "save_standing_journey_event", None)
    if not callable(save_ev):
        return
    try:
        save_ev(job_id=job_id, kind=kind, payload=payload)
    except Exception as exc:  # noqa: BLE001
        logger.debug("mid-job scaffold journey soft-fail: %s", exc)


def reject_unscoped_trusted_write_mid_phase(spine: Any, **kwargs: Any) -> None:
    """Explicit reject path — never write trusted mid-phase [REQ-SCAFFOLD-002/005]."""
    writer = getattr(spine, "write_trusted_unscoped", None)
    if callable(writer):
        writer(**kwargs)
        return
    raise UnscopedTrustedWriteError(
        "unscoped write to trusted rejected; use draft->sandbox->version->HITL spine"
    )


def assert_candidate_not_trusted(spine: Any, record_id: str) -> Dict[str, Any]:
    """Fail closed if caller tries to treat candidate as trusted [REQ-SCAFFOLD-003]."""
    rec = spine.get(record_id)
    tier = getattr(rec.trust_tier, "value", rec.trust_tier)
    phase = getattr(rec.phase, "value", rec.phase)
    if tier == TrustTier.TRUSTED.value and phase == ScaffoldPhase.TRUSTED.value:
        return {"ok": True, "record_id": rec.id, "trust_tier": tier, "phase": phase}
    raise PermissionError(
        "candidate cannot be used as trusted until HITL promote via 218 spine"
    )


def apply_mid_job_scaffold_on_gap(
    orchestrator: Any,
    *,
    spine: Any,
    phase_id: str,
    gap: MidJobCapabilityGap,
    kind: str | None = None,
    name: str | None = None,
    pack_id: str | None = None,
    summary: str = "",
    content: str = "",
    park: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Open candidate via 218 spine for a mid-job gap [REQ-SCAFFOLD-001..003].

    Never writes trusted. Parks (default) or continues with matched-only.
    """
    if not gap.is_gap:
        return {
            "ok": False,
            "action": "none",
            "reason": "no_gap",
            "trusted_write": False,
        }

    phase = orchestrator._store.get_phase(phase_id)
    job = orchestrator._store.get_job(phase.job_id)
    matched = list(orchestrator.matched_capability_ids_for_job(phase.job_id) or [])

    k = (kind or gap.suggested_kind or "skill").strip().lower()
    nm = (name or gap.suggested_name or "scaffold-candidate").strip()
    pid = (pack_id or gap.suggested_pack_id or _slug(nm)).strip()
    summ = (summary or f"Mid-job candidate for gap: {gap.reason}").strip()
    body = content or f"# {nm}\n\nCandidate scaffold for: {gap.reason}\n"

    meta = {
        "mid_job_scaffold": True,
        "job_id": phase.job_id,
        "phase_id": phase_id,
        "gap_reason": gap.reason,
        "missing_families": list(gap.missing_families),
        "matched_capability_ids_at_gap": list(matched),
        **dict(metadata or {}),
    }

    # Always candidate — spine.draft never trusted [REQ-SCAFFOLD-001]
    rec = spine.draft(
        kind=k,
        name=nm,
        pack_id=pid,
        summary=summ,
        content=body,
        keywords=[nm, pid, "scaffold", "candidate", "mid_job", *list(gap.missing_families)],
        metadata=meta,
    )

    _emit_journey(
        orchestrator,
        job_id=phase.job_id,
        kind="scaffold_candidate",
        payload={
            "record_id": rec.id,
            "capability_id": rec.capability_id,
            "trust_tier": getattr(rec.trust_tier, "value", str(rec.trust_tier)),
            "phase": getattr(rec.phase, "value", str(rec.phase)),
            "gap": gap.as_dict(),
            "matched_capability_ids": list(matched),
            "forge_queue": True,
            "trusted_write": False,
        },
    )

    action = "park" if park else "continue_matched_only"
    if park:
        park_fn = getattr(orchestrator, "park_phase", None)
        if callable(park_fn):
            try:
                park_fn(phase_id, verifier_status="none")
            except TypeError:
                park_fn(phase_id)
        # Re-stamp checkpoint: keep matched IDs (no candidate), HITL park.
        commit = getattr(orchestrator, "_commit_checkpoint", None)
        if callable(commit):
            refreshed = orchestrator._store.get_phase(phase_id)
            commit(
                refreshed,
                verifier_status="none",
                hitl_park_state=True,
                matched_capability_ids=matched,
            )
        _emit_journey(
            orchestrator,
            job_id=phase.job_id,
            kind="scaffold_hitl",
            payload={
                "record_id": rec.id,
                "capability_id": rec.capability_id,
                "action": "park_awaiting_hitl",
                "phase_id": phase_id,
                "job_id": phase.job_id,
                "trusted_write": False,
            },
        )
    else:
        # Continue with remaining matched only — candidate NOT added to matched IDs.
        commit = getattr(orchestrator, "_commit_checkpoint", None)
        if callable(commit):
            commit(
                phase,
                verifier_status="none",
                hitl_park_state=False,
                matched_capability_ids=matched,
            )
        _emit_journey(
            orchestrator,
            job_id=phase.job_id,
            kind="scaffold_hitl",
            payload={
                "record_id": rec.id,
                "capability_id": rec.capability_id,
                "action": "continue_matched_only_awaiting_hitl",
                "phase_id": phase_id,
                "job_id": phase.job_id,
                "matched_capability_ids": list(matched),
                "trusted_write": False,
            },
        )

    logger.info(
        "Mid-job scaffold candidate job=%s record=%s action=%s gap=%s",
        phase.job_id,
        rec.id,
        action,
        gap.reason,
    )
    return {
        "ok": True,
        "action": action,
        "record_id": rec.id,
        "capability_id": rec.capability_id,
        "trust_tier": getattr(rec.trust_tier, "value", str(rec.trust_tier)),
        "phase": getattr(rec.phase, "value", str(rec.phase)),
        "trusted_write": False,
        "matched_capability_ids": list(matched),
        "gap": gap.as_dict(),
        "job_id": phase.job_id,
        "phase_id": phase_id,
        "success_rule": getattr(job, "success_rule", "") or "",
        "forge_queue": True,
    }


def promote_scaffold_and_reresolve(
    orchestrator: Any,
    *,
    spine: Any,
    job_id: str,
    record_id: str,
    intent: str | None = None,
) -> Dict[str, Any]:
    """
    HITL promote via 218 then catalog re-resolve; update matched IDs [REQ-SCAFFOLD-002].

    Caller must have completed sandbox + version (or hitl_approve will enforce).
    """
    job = orchestrator._store.get_job(job_id)
    prior = list(orchestrator.matched_capability_ids_for_job(job_id) or [])

    # HITL approve -> trusted (218 spine only)
    rec = spine.hitl_approve(record_id)
    tier = getattr(rec.trust_tier, "value", str(rec.trust_tier))
    if tier != TrustTier.TRUSTED.value:
        raise PermissionError("HITL approve did not reach trusted")

    _emit_journey(
        orchestrator,
        job_id=job_id,
        kind="scaffold_hitl",
        payload={
            "record_id": rec.id,
            "capability_id": rec.capability_id,
            "action": "hitl_approved",
            "trust_tier": tier,
            "phase": getattr(rec.phase, "value", str(rec.phase)),
        },
    )

    # Catalog re-resolve against success_rule / intent; merge prior + new trusted id.
    query = (intent or getattr(job, "success_rule", None) or getattr(job, "goal", "") or "").strip()
    new_ids: List[str] = list(prior)
    if rec.capability_id not in new_ids:
        new_ids.append(rec.capability_id)

    resolver = getattr(orchestrator, "_capability_resolver", None)
    resolved_ids: List[str] = []
    if resolver is not None and query:
        try:
            result = resolver.resolve(query, trusted_only=True)
            resolved_ids = [e.id for e in (result.matched or ())]
        except Exception as exc:  # noqa: BLE001
            logger.debug("catalog re-resolve soft-fail: %s", exc)
            resolved_ids = []

    # Merge: prior matched + newly trusted + freshly resolved (dedupe, preserve order)
    merged: List[str] = []
    for cid in list(prior) + [rec.capability_id] + list(resolved_ids):
        s = str(cid).strip()
        if s and s not in merged:
            merged.append(s)

    # Stamp checkpoint matched IDs
    phases = orchestrator._store.list_phases_for_job(job_id)
    stamp_phase = None
    for p in phases:
        st = getattr(getattr(p, "status", None), "value", str(getattr(p, "status", "")))
        if st in {"running", "waiting_approval", "queued"}:
            stamp_phase = p
            break
    if stamp_phase is None and phases:
        stamp_phase = phases[-1]

    commit = getattr(orchestrator, "_commit_checkpoint", None)
    if callable(commit) and stamp_phase is not None:
        commit(
            stamp_phase,
            verifier_status="none",
            hitl_park_state=False,
            matched_capability_ids=merged,
        )
    else:
        orchestrator._matched_ids[job_id] = list(merged)

    _emit_journey(
        orchestrator,
        job_id=job_id,
        kind="catalog_reresolve",
        payload={
            "record_id": rec.id,
            "capability_id": rec.capability_id,
            "prior_matched_capability_ids": list(prior),
            "resolved_ids": list(resolved_ids),
            "matched_capability_ids": list(merged),
            "intent": query[:240],
        },
    )

    logger.info(
        "Scaffold promoted + re-resolve job=%s cap=%s matched=%s",
        job_id,
        rec.capability_id,
        merged,
    )
    return {
        "ok": True,
        "record_id": rec.id,
        "capability_id": rec.capability_id,
        "trust_tier": tier,
        "phase": getattr(rec.phase, "value", str(rec.phase)),
        "matched_capability_ids": list(merged),
        "prior_matched_capability_ids": list(prior),
        "action": "promoted_reresolve",
    }




def parked_job_id_from_scaffold(record: Any) -> str:
    """Origin job_id stamped on mid-job scaffold metadata [CARD-251]."""
    meta = getattr(record, "metadata", None) or {}
    if not isinstance(meta, Mapping):
        return ""
    return str(meta.get("job_id") or "").strip()


def parked_phase_id_from_scaffold(record: Any) -> str:
    meta = getattr(record, "metadata", None) or {}
    if not isinstance(meta, Mapping):
        return ""
    return str(meta.get("phase_id") or "").strip()


def forge_approve_and_resume_job(
    orchestrator: Any,
    *,
    spine: Any,
    record_id: str,
    intent: str | None = None,
) -> Dict[str, Any]:
    """
    Forge Studio Approve for a parked mid-job scaffold [CARD-251 / REQ-FORGE-RESUME-001..002].

    - Same ``job_id`` / origin session (metadata correlation) — never mint a new Job.
    - Promote via 218 HITL + catalog re-resolve, then ``start_phase`` unpark so Execute can continue.
    - Never soft-delete / cancel the parked Job.
    """
    rec = spine.get(record_id)
    job_id = parked_job_id_from_scaffold(rec)
    phase_id_meta = parked_phase_id_from_scaffold(rec)

    if not job_id:
        # Standalone Forge candidate (no mid-job park) — promote only.
        approved = spine.hitl_approve(record_id)
        return {
            "ok": True,
            "action": "promote_only",
            "record_id": approved.id,
            "capability_id": approved.capability_id,
            "trust_tier": getattr(approved.trust_tier, "value", str(approved.trust_tier)),
            "phase": getattr(approved.phase, "value", str(approved.phase)),
            "job_id": None,
            "session_id": None,
            "phase_id": None,
            "resumed": False,
            "same_job": False,
            "orphan": False,
            "soft_deleted": False,
        }

    job = orchestrator._store.get_job(job_id)
    session_id = str(getattr(job, "session_id", "") or "").strip() or None
    status_before = getattr(getattr(job, "status", None), "value", str(getattr(job, "status", "")))

    # Explicit: never soft-delete / cancel parked Jobs on Forge Approve
    # (do not call cancel_job / delete — asserted by tests via status preservation).

    promoted = promote_scaffold_and_reresolve(
        orchestrator,
        spine=spine,
        job_id=job_id,
        record_id=record_id,
        intent=intent or getattr(job, "success_rule", None) or getattr(job, "goal", None),
    )

    # Unpark waiting phase on the SAME job.
    phases = orchestrator._store.list_phases_for_job(job_id)
    target = None
    if phase_id_meta:
        for p in phases:
            if p.id == phase_id_meta:
                target = p
                break
    if target is None:
        for p in phases:
            st = getattr(getattr(p, "status", None), "value", str(getattr(p, "status", "")))
            if st == "waiting_approval":
                target = p
                break
    if target is None:
        for p in phases:
            st = getattr(getattr(p, "status", None), "value", str(getattr(p, "status", "")))
            if st in {"queued", "running"}:
                target = p
                break
    if target is None and phases:
        target = phases[-1]

    resumed_phase = None
    if target is not None:
        st = getattr(getattr(target, "status", None), "value", str(getattr(target, "status", "")))
        if st in {"waiting_approval", "queued"}:
            resumed_phase = orchestrator.start_phase(target.id)
        else:
            resumed_phase = target

    job_after = orchestrator._store.get_job(job_id)
    status_after = getattr(
        getattr(job_after, "status", None), "value", str(getattr(job_after, "status", ""))
    )

    _emit_journey(
        orchestrator,
        job_id=job_id,
        kind="forge_approve_resume",
        payload={
            "record_id": record_id,
            "capability_id": promoted.get("capability_id"),
            "action": "forge_approve_same_job",
            "job_id": job_id,
            "session_id": session_id,
            "phase_id": getattr(resumed_phase, "id", None) or phase_id_meta,
            "status_before": status_before,
            "status_after": status_after,
            "same_job": True,
            "orphan": False,
            "soft_deleted": False,
            "resumed": True,
        },
    )

    logger.info(
        "Forge Approve resumed same job_id=%s session=%s phase=%s status=%s->%s",
        job_id,
        session_id,
        getattr(resumed_phase, "id", None),
        status_before,
        status_after,
    )
    return {
        "ok": True,
        "action": "forge_approve_resume",
        "record_id": record_id,
        "capability_id": promoted.get("capability_id"),
        "trust_tier": promoted.get("trust_tier"),
        "phase": promoted.get("phase"),
        "matched_capability_ids": list(promoted.get("matched_capability_ids") or []),
        "job_id": job_id,
        "session_id": session_id,
        "phase_id": getattr(resumed_phase, "id", None) or phase_id_meta,
        "resumed": True,
        "same_job": True,
        "orphan": False,
        "soft_deleted": False,
        "status_before": status_before,
        "status_after": status_after,
        "origin_session": True,
    }


__all__ = [
    "MidJobCapabilityGap",
    "detect_mid_job_capability_gap",
    "apply_mid_job_scaffold_on_gap",
    "promote_scaffold_and_reresolve",
    "forge_approve_and_resume_job",
    "parked_job_id_from_scaffold",
    "parked_phase_id_from_scaffold",
    "assert_candidate_not_trusted",
    "reject_unscoped_trusted_write_mid_phase",
]
