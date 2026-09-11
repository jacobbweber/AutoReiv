"""Standing A2A handoff inherits Job/Phase path [CARD-224].

Child jobs reuse parent matched capability IDs (no cold re-resolve), keep
CARD-221 policy fail-closed (no tool widen), and prefer a linked child_job_id.
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
