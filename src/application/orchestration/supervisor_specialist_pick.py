"""Supervisor specialist pick from matched catalog IDs [CARD-234 / REQ-SUPER-001..005].

When a phase needs a specialist, pick the handoff target **only** from matched
catalog agent/pack IDs in the working set — never free-form role theatre.

Handoff reuses standing_a2a_handoff: CARD-265 same job_id by default (never-widen); optional linked child_job_id remains CARD-224.
No match => park / scaffold (233) / fail-closed — never invent out-of-catalog agents.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.application.orchestration.standing_a2a_handoff import (
    bind_specialist_same_job,
    child_ids_do_not_widen,
)

logger = logging.getLogger(__name__)

_SPECIALIST_PREFIXES = ("agent.", "pack.")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


class OutOfCatalogHandoffError(PermissionError):
    """Raised when handoff target is outside matched catalog agent/pack IDs."""


@dataclass(frozen=True)
class SpecialistPick:
    """Result of matching a needed specialty against matched catalog IDs."""

    ok: bool
    specialty: str
    matched_catalog_ids: tuple[str, ...] = field(default_factory=tuple)
    candidate_ids: tuple[str, ...] = field(default_factory=tuple)
    picked_catalog_id: Optional[str] = None
    picked_agent_id: Optional[str] = None
    reason: str = ""
    invented: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "specialty": self.specialty,
            "matched_catalog_ids": list(self.matched_catalog_ids),
            "candidate_ids": list(self.candidate_ids),
            "picked_catalog_id": self.picked_catalog_id,
            "picked_agent_id": self.picked_agent_id,
            "reason": self.reason,
            "invented": self.invented,
        }


def catalog_specialist_ids(matched_ids: Sequence[str] | None) -> List[str]:
    """Return matched IDs that are agents or packs (handoff targets only)."""
    out: List[str] = []
    for cid in matched_ids or []:
        s = str(cid or "").strip()
        if not s:
            continue
        low = s.lower()
        if low.startswith(_SPECIALIST_PREFIXES) or low.startswith("agent/") or low.startswith("pack/"):
            out.append(s)
            continue
        # Also accept bare ids when entry_meta later confirms kind — keep prefix filter primary.
    return out


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _agent_id_from_catalog_id(catalog_id: str, meta: Mapping[str, Any] | None) -> str:
    """Map catalog id / pack metadata to a handoff agent_id (no invent)."""
    meta = meta or {}
    mid = meta.get("metadata") if isinstance(meta.get("metadata"), dict) else {}
    for key in ("agent_id", "target_agent_id", "owner_agent_id"):
        val = (mid or {}).get(key) or meta.get(key)
        if val:
            return str(val).strip()
    cid = str(catalog_id or "").strip()
    low = cid.lower()
    if low.startswith("agent."):
        return cid.split(".", 1)[1]
    if low.startswith("pack."):
        # Pack without explicit agent_id: use pack slug as agent id (still in-catalog).
        return cid.split(".", 1)[1]
    return cid


def match_specialty_candidates(
    *,
    matched_ids: Sequence[str],
    specialty: str,
    entry_meta: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> List[str]:
    """Rank matched agent/pack IDs by specialty keyword overlap (highest first)."""
    meta = entry_meta or {}
    specialists = catalog_specialist_ids(matched_ids)
    # Filter by entry kind when meta present (tools wrongly prefixed never happen; safety).
    filtered: List[str] = []
    for cid in specialists:
        info = meta.get(cid) or {}
        kind = str(info.get("kind") or "").lower()
        if kind and kind not in {"agent", "pack", ""}:
            continue
        if not kind:
            # prefix-only acceptance when meta missing
            pass
        filtered.append(cid)
    if not filtered:
        return []

    need = _tokens(specialty)
    if not need:
        return list(filtered)

    scored: List[tuple[int, str]] = []
    for cid in filtered:
        info = meta.get(cid) or {}
        hay = _tokens(cid) | _tokens(str(info.get("name") or ""))
        hay |= _tokens(" ".join(str(x) for x in (info.get("keywords") or [])))
        hay |= _tokens(" ".join(str(x) for x in (info.get("roles") or [])))
        score = len(need & hay)
        if score > 0:
            scored.append((score, cid))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [cid for _, cid in scored]


def pick_specialist_from_matched(
    *,
    matched_ids: Sequence[str],
    specialty: str,
    entry_meta: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> SpecialistPick:
    """Pick one specialist from matched catalog agent/pack IDs only [REQ-SUPER-001]."""
    ids = [str(x) for x in (matched_ids or [])]
    meta = entry_meta or {}
    candidates = match_specialty_candidates(
        matched_ids=ids,
        specialty=specialty,
        entry_meta=meta,
    )
    if not candidates:
        return SpecialistPick(
            ok=False,
            specialty=specialty or "",
            matched_catalog_ids=tuple(ids),
            candidate_ids=tuple(),
            picked_catalog_id=None,
            picked_agent_id=None,
            reason="no_matched_specialist_for_specialty",
            invented=False,
        )
    picked = candidates[0]
    agent_id = _agent_id_from_catalog_id(picked, meta.get(picked) or {})
    return SpecialistPick(
        ok=True,
        specialty=specialty or "",
        matched_catalog_ids=tuple(ids),
        candidate_ids=tuple(candidates),
        picked_catalog_id=picked,
        picked_agent_id=agent_id,
        reason=f"matched_catalog:{picked}",
        invented=False,
    )


def _specialist_agent_ids(
    matched_ids: Sequence[str],
    entry_meta: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> set[str]:
    """Allowed handoff agent ids derived from matched agent/pack catalog IDs."""
    meta = entry_meta or {}
    allowed: set[str] = set()
    for cid in catalog_specialist_ids(matched_ids):
        info = meta.get(cid) or {}
        agent_id = _agent_id_from_catalog_id(cid, info)
        if agent_id:
            allowed.add(agent_id)
            allowed.add(agent_id.lower())
        allowed.add(cid)
        allowed.add(cid.lower())
        # bare suffix
        if "." in cid:
            allowed.add(cid.split(".", 1)[1])
            allowed.add(cid.split(".", 1)[1].lower())
    return allowed


def reject_out_of_catalog_handoff(
    *,
    target_agent_id: str,
    matched_ids: Sequence[str],
    entry_meta: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> None:
    """Fail closed if target is not in matched catalog agent/pack set [REQ-SUPER-003]."""
    target = (target_agent_id or "").strip()
    if not target:
        raise OutOfCatalogHandoffError("empty handoff target rejected")
    allowed = _specialist_agent_ids(matched_ids, entry_meta)
    if target in allowed or target.lower() in allowed:
        return
    # Also accept full catalog id form agent.X when X is target
    for cid in catalog_specialist_ids(matched_ids):
        if cid == target or cid.endswith("." + target) or cid.lower().endswith("." + target.lower()):
            return
    raise OutOfCatalogHandoffError(
        f"out-of-catalog handoff rejected: {target!r} not in matched agent/pack IDs"
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
        logger.debug("supervisor_pick journey soft-fail: %s", exc)


def _resolve_entry_meta(
    orchestrator: Any,
    matched_ids: Sequence[str],
    entry_meta: Optional[Mapping[str, Mapping[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    if entry_meta:
        return {str(k): dict(v) for k, v in entry_meta.items()}
    out: Dict[str, Dict[str, Any]] = {}
    resolver = getattr(orchestrator, "_capability_resolver", None)
    store = getattr(resolver, "_store", None) if resolver is not None else None
    getter = getattr(store, "get_entry", None) if store is not None else None
    if not callable(getter):
        return out
    for cid in matched_ids:
        try:
            entry = getter(cid)
        except Exception:
            entry = None
        if entry is None:
            continue
        kind = getattr(entry.kind, "value", entry.kind)
        out[cid] = {
            "kind": str(kind),
            "name": getattr(entry, "name", "") or "",
            "keywords": list(getattr(entry, "keywords", None) or []),
            "roles": list(getattr(entry, "roles", None) or []),
            "metadata": dict(getattr(entry, "metadata", None) or {}),
        }
    return out


def supervisor_specialist_handoff(
    orchestrator: Any,
    *,
    phase_id: str,
    specialty: str,
    entry_meta: Optional[Mapping[str, Mapping[str, Any]]] = None,
    session_id: Optional[str] = None,
    requested_agent_id: Optional[str] = None,
    on_no_match: str = "park",
    intent: Optional[str] = None,
    verify_checker: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Pick specialist from matched catalog and create standing child [REQ-SUPER-001..003].

    on_no_match: park | scaffold | fail_closed
    """
    phase = orchestrator._store.get_phase(phase_id)
    job = orchestrator._store.get_job(phase.job_id)
    parent_ids = list(orchestrator.matched_capability_ids_for_job(phase.job_id))
    meta = _resolve_entry_meta(orchestrator, parent_ids, entry_meta)

    # Explicit out-of-catalog request => reject (never invent) [REQ-SUPER-003]
    if requested_agent_id:
        try:
            reject_out_of_catalog_handoff(
                target_agent_id=requested_agent_id,
                matched_ids=parent_ids,
                entry_meta=meta,
            )
        except OutOfCatalogHandoffError as exc:
            payload = {
                "ok": False,
                "action": "rejected",
                "reason": str(exc),
                "specialty": specialty,
                "requested_agent_id": requested_agent_id,
                "parent_job_id": job.id,
                "child_job_id": None,
                "matched_capability_ids": list(parent_ids),
                "invented": False,
            }
            _emit_journey(
                orchestrator,
                job_id=job.id,
                kind="supervisor_pick",
                payload=payload,
            )
            return payload

    pick = pick_specialist_from_matched(
        matched_ids=parent_ids,
        specialty=specialty,
        entry_meta=meta,
    )

    if requested_agent_id and pick.ok:
        # Prefer explicit in-catalog request when it matches a candidate
        req = requested_agent_id.strip()
        for cand in pick.candidate_ids:
            agent_id = _agent_id_from_catalog_id(cand, meta.get(cand) or {})
            if req in {cand, agent_id, cand.split(".")[-1]} or req.lower() in {
                cand.lower(),
                agent_id.lower(),
                cand.split(".")[-1].lower(),
            }:
                pick = SpecialistPick(
                    ok=True,
                    specialty=specialty,
                    matched_catalog_ids=pick.matched_catalog_ids,
                    candidate_ids=pick.candidate_ids,
                    picked_catalog_id=cand,
                    picked_agent_id=agent_id,
                    reason=f"requested_in_catalog:{cand}",
                    invented=False,
                )
                break

    if not pick.ok:
        action = (on_no_match or "park").strip().lower()
        if action not in {"park", "scaffold", "fail_closed"}:
            action = "fail_closed"
        if action == "park":
            try:
                orchestrator.park_phase(phase_id, verifier_status="none")
            except Exception as exc:  # noqa: BLE001
                logger.warning("supervisor no-match park failed: %s", exc)
        elif action == "scaffold":
            # Defer to CARD-233 hook when available; still fail-closed on invent.
            handler = getattr(orchestrator, "handle_mid_job_capability_gap", None)
            if callable(handler):
                try:
                    handler(phase_id, spine=None, park=True)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("supervisor scaffold defer soft-fail: %s", exc)
                    action = "fail_closed"
            else:
                action = "fail_closed"
                try:
                    orchestrator.park_phase(phase_id, verifier_status="none")
                    action = "park"
                except Exception:
                    action = "fail_closed"
        payload = {
            "ok": False,
            "action": action,
            "reason": pick.reason or "no_matched_specialist",
            "specialty": specialty,
            "parent_job_id": job.id,
            "child_job_id": None,
            "picked_catalog_id": None,
            "picked_agent_id": None,
            "matched_capability_ids": list(parent_ids),
            "candidate_ids": list(pick.candidate_ids),
            "invented": False,
        }
        _emit_journey(orchestrator, job_id=job.id, kind="supervisor_pick", payload=payload)
        return payload

    # CARD-265: bind specialist onto the same job_id tree (never-widen).
    # Opt-in linked_child_job via intent kw is not exposed here — callers that need
    # 224 child create should call create_standing_child_job directly.
    _ = (session_id, verify_checker, intent)  # retained for API compat / journey facts
    try:
        bound = bind_specialist_same_job(
            orchestrator,
            job_id=job.id,
            specialist_agent_id=pick.picked_agent_id or "assistant",
            specialty=specialty,
            park=True,
            phase_id=phase_id,
        )
    except Exception as exc:  # noqa: BLE001
        payload = {
            "ok": False,
            "action": "fail_closed",
            "reason": f"same_job_bind_failed:{exc}",
            "specialty": specialty,
            "parent_job_id": job.id,
            "child_job_id": None,
            "same_job_id": None,
            "picked_catalog_id": pick.picked_catalog_id,
            "picked_agent_id": pick.picked_agent_id,
            "matched_capability_ids": list(parent_ids),
            "invented": False,
        }
        _emit_journey(orchestrator, job_id=job.id, kind="supervisor_pick", payload=payload)
        return payload

    eff = list(bound.get("effective_matched_capability_ids") or bound.get("matched_capability_ids") or parent_ids)
    if not child_ids_do_not_widen(parent_ids, eff):
        payload = {
            "ok": False,
            "action": "fail_closed",
            "reason": "same_job_matched_ids_widened",
            "specialty": specialty,
            "parent_job_id": job.id,
            "child_job_id": None,
            "same_job_id": None,
            "picked_catalog_id": pick.picked_catalog_id,
            "picked_agent_id": pick.picked_agent_id,
            "matched_capability_ids": list(parent_ids),
            "invented": False,
        }
        _emit_journey(orchestrator, job_id=job.id, kind="supervisor_pick", payload=payload)
        return payload

    payload = {
        "ok": True,
        "action": "handoff",
        "reason": pick.reason,
        "specialty": specialty,
        "parent_job_id": job.id,
        "child_job_id": job.id,  # same tree
        "same_job_id": job.id,
        "picked_catalog_id": pick.picked_catalog_id,
        "picked_agent_id": pick.picked_agent_id,
        "matched_capability_ids": list(parent_ids),
        "effective_matched_capability_ids": list(eff),
        "child_matched_capability_ids": list(eff),
        "candidate_ids": list(pick.candidate_ids),
        "invented": False,
        "privilege_escalated": False,
        "linked_child_job": False,
        "parked_phase_id": bound.get("parked_phase_id"),
    }
    _emit_journey(orchestrator, job_id=job.id, kind="supervisor_pick", payload=payload)
    logger.info(
        "Supervisor pick job=%s specialty=%s catalog=%s agent=%s same_job=%s",
        job.id,
        specialty,
        pick.picked_catalog_id,
        pick.picked_agent_id,
        job.id,
    )
    return payload


__all__ = [
    "OutOfCatalogHandoffError",
    "SpecialistPick",
    "catalog_specialist_ids",
    "match_specialty_candidates",
    "pick_specialist_from_matched",
    "reject_out_of_catalog_handoff",
    "supervisor_specialist_handoff",
]
