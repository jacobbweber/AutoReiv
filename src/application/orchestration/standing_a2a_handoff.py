"""Standing A2A handoff inherits Job/Phase path [CARD-224 / CARD-254 / CARD-265].

CARD-224: linked child_job_id reuses parent matched capability IDs (no cold
re-resolve), CARD-221 fail-closed (no tool widen).

CARD-265: specialist path binds/resumes the **same** job_id tree (parent park
→ specialist work → parent continues). Privilege never escalates beyond the
parent matched subset (skip allowlist union on handoff).
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from src.domain.orchestration.models import Job


def matched_ids_for_parent(orch: Any, parent_job_id: str) -> list[str]:
    """Read matched capability IDs from parent checkpoint / orch cache."""
    ids_fn = getattr(orch, "matched_capability_ids_for_job", None)
    if callable(ids_fn):
        ids = list(ids_fn(parent_job_id) or [])
        if ids:
            return [str(x) for x in ids]
    cp_fn = getattr(orch, "get_latest_checkpoint", None)
    if callable(cp_fn):
        cp = cp_fn(parent_job_id)
        if cp is not None and getattr(cp, "matched_capability_ids", None):
            return [str(x) for x in cp.matched_capability_ids]
    return []


def child_ids_do_not_widen(parent_ids: Sequence[str], child_ids: Sequence[str]) -> bool:
    """True iff child matched set is a subset of parent (no widen)."""
    parent = {str(x) for x in parent_ids}
    child = {str(x) for x in child_ids}
    return child.issubset(parent)


def create_standing_child_job(
    orch: Any,
    *,
    parent_job_id: str,
    intent: str,
    session_id: str,
    agent_id: str,
    role: Optional[str] = None,
    verify_checker: Optional[str] = None,
) -> Job:
    """
    Create linked child catalog R/H/E job inheriting parent matched IDs [CARD-224].

    Prefer create_job_from_catalog_resolve with reused matched_capability_ids so
    child does not cold re-resolve (and cannot silently widen the subset).
    """
    parent_ids = matched_ids_for_parent(orch, parent_job_id)
    if not hasattr(orch, "create_job_from_catalog_resolve"):
        raise RuntimeError("orchestrator missing create_job_from_catalog_resolve")
    child = orch.create_job_from_catalog_resolve(
        intent=intent,
        session_id=session_id,
        agent_id=agent_id,
        role=role or agent_id,
        matched_capability_ids=list(parent_ids),
        verify_checker=verify_checker,
    )
    # Link maps (in-memory; durable proof is parent_job_id on child checkpoint facts via goal)
    links = getattr(orch, "_a2a_child_links", None)
    if not isinstance(links, dict):
        links = {}
        setattr(orch, "_a2a_child_links", links)
    parents = getattr(orch, "_a2a_parent_of", None)
    if not isinstance(parents, dict):
        parents = {}
        setattr(orch, "_a2a_parent_of", parents)
    links.setdefault(parent_job_id, [])
    if child.id not in links[parent_job_id]:
        links[parent_job_id].append(child.id)
    parents[child.id] = parent_job_id

    # Durable A2A link for Observability standing journey [CARD-227]
    store = getattr(orch, "_store", None)
    saver = getattr(store, "save_job_a2a_link", None) if store is not None else None
    if callable(saver):
        try:
            saver(parent_job_id=parent_job_id, child_job_id=child.id)
        except Exception:
            pass

    child_ids = matched_ids_for_parent(orch, child.id)
    if not child_ids_do_not_widen(parent_ids, child_ids):
        # Fail closed: cancel child rather than allow widen.
        cancel = getattr(orch, "cancel_job", None)
        if callable(cancel):
            cancel(child.id)
        raise RuntimeError(
            f"child matched IDs widened beyond parent: parent={parent_ids} child={child_ids}"
        )
    return child


def linked_child_job_ids(orch: Any, parent_job_id: str) -> list[str]:
    links = getattr(orch, "_a2a_child_links", None) or {}
    return list(links.get(parent_job_id) or [])


def effective_matched_ids_no_escalate(
    parent_ids: Sequence[str],
    *,
    specialist_tool_names: Optional[Sequence[str]] = None,
) -> list[str]:
    """Return parent matched IDs only — never union specialist allowlist [CARD-265].

    specialist_tool_names is accepted for call-site clarity but intentionally
    ignored so handoff cannot privilege-escalate.
    """
    _ = specialist_tool_names  # skip escalation by design
    return [str(x) for x in parent_ids]


def bind_specialist_same_job(
    orch: Any,
    *,
    job_id: str,
    specialist_agent_id: str,
    specialty: Optional[str] = None,
    park: bool = True,
    phase_id: Optional[str] = None,
) -> dict[str, Any]:
    """Bind specialist work onto the existing standing job_id [CARD-265].

    Does not mint a child Job. Optionally parks the current/running phase so
    parent → specialist → parent continue shares one Observe tree.
    """
    jid = str(job_id or "").strip()
    if not jid:
        raise ValueError("job_id required for same-job specialist handoff")
    store = getattr(orch, "_store", None)
    getter = getattr(store, "get_job", None) if store is not None else None
    job = getter(jid) if callable(getter) else None
    if job is None:
        raise RuntimeError(f"standing job not found for same-job handoff: {jid}")

    parent_ids = matched_ids_for_parent(orch, jid)
    effective = effective_matched_ids_no_escalate(parent_ids)
    if not child_ids_do_not_widen(parent_ids, effective):
        raise RuntimeError("same-job handoff privilege widened — fail closed")

    parked_phase_id = None
    if park:
        pid = phase_id
        if not pid:
            lister = getattr(store, "list_phases_for_job", None) if store is not None else None
            phases = list(lister(jid) or []) if callable(lister) else []
            # Prefer running, else current_phase_id, else last phase
            running = [p for p in phases if str(getattr(p, "status", "")).lower() in {"running", "phasestatus.running"}]
            if running:
                pid = running[0].id
            elif getattr(job, "current_phase_id", None):
                pid = job.current_phase_id
            elif phases:
                pid = phases[-1].id
        if pid:
            try:
                orch.park_phase(pid, verifier_status="none")
                parked_phase_id = pid
            except Exception:
                parked_phase_id = None

    payload = {
        "ok": True,
        "action": "handoff",
        "job_id": jid,
        "same_job_id": jid,
        "parent_job_id": jid,
        "child_job_id": jid,  # one tree — Observe strip may show link as self
        "specialist_agent_id": str(specialist_agent_id or "").strip() or None,
        "specialty": specialty or "",
        "matched_capability_ids": list(parent_ids),
        "effective_matched_capability_ids": list(effective),
        "parked_phase_id": parked_phase_id,
        "privilege_escalated": False,
        "linked_child_job": False,
    }

    # In-memory same-job bind map (mirrors 224 link maps without new ids)
    binds = getattr(orch, "_a2a_same_job_binds", None)
    if not isinstance(binds, dict):
        binds = {}
        setattr(orch, "_a2a_same_job_binds", binds)
    binds.setdefault(jid, [])
    binds[jid].append(
        {
            "specialist_agent_id": payload["specialist_agent_id"],
            "specialty": payload["specialty"],
        }
    )

    save_ev = getattr(store, "save_standing_journey_event", None) if store is not None else None
    if callable(save_ev):
        try:
            save_ev(job_id=jid, kind="a2a_same_job_handoff", payload=dict(payload))
        except Exception:
            pass

    return payload


def handoff_must_not_replan(
    *,
    replan_count_before: int,
    replan_count_after: int,
    journey_kinds: list | None = None,
) -> bool:
    """Handoff != replan [CARD-254 / REQ-VRH-003].

    Returns True when child handoff did not bump replan_count and did not emit
    standing.replan / replan_park kinds.
    """
    if int(replan_count_after) != int(replan_count_before):
        return False
    kinds = [str(k) for k in (journey_kinds or [])]
    forbidden = {"replan", "replan_park", "standing.replan", "standing.replan_park"}
    if any(k in forbidden for k in kinds):
        return False
    return True
