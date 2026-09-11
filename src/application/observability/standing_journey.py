"""Standing journey timeline assembler [CARD-227 / REQ-SJURN-*].

Correlates Job/Phase, catalog matches, verifier statuses, CARD-221 policy
decisions (incl. MCP BLOCKs), A2A child_job_id links, and kill/resume into one
OpenTelemetry-style GenAI agent span tree keyed by job_id.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)


def _status_str(obj: Any) -> str:
    raw = getattr(obj, "status", obj)
    return raw.value if hasattr(raw, "value") else str(raw)


def build_standing_journey(store: Any, *, job_id: str) -> Dict[str, Any]:
    """Assemble one standing journey replay for a job_id [REQ-SJURN-001..004]."""
    jid = str(job_id or "").strip()
    if not jid:
        return {
            "job_id": "",
            "ok": False,
            "error": "job_id required",
            "timeline": [],
            "spans": [],
            "resumed_from_checkpoint": False,
            "child_job_ids": [],
            "policy_decisions": [],
            "catalog_matches": [],
            "verifier_statuses": [],
        }

    job = None
    getter = getattr(store, "get_job", None)
    if callable(getter):
        try:
            job = getter(jid)
        except Exception:
            job = None

    phases: List[Any] = []
    lister = getattr(store, "list_phases_for_job", None)
    if callable(lister):
        try:
            phases = list(lister(jid) or [])
        except Exception:
            phases = []

    checkpoints: List[Any] = []
    cp_list = getattr(store, "list_job_phase_checkpoints", None)
    if callable(cp_list):
        try:
            checkpoints = list(cp_list(jid) or [])
        except Exception:
            checkpoints = []
    if not checkpoints:
        latest = getattr(store, "get_latest_job_phase_checkpoint", None)
        if callable(latest):
            cp = latest(jid)
            if cp is not None:
                checkpoints = [cp]

    catalog_matches: List[str] = []
    for cp in checkpoints:
        ids = list(getattr(cp, "matched_capability_ids", None) or [])
        if isinstance(cp, dict):
            ids = list(cp.get("matched_capability_ids") or [])
        for x in ids:
            sx = str(x)
            if sx and sx not in catalog_matches:
                catalog_matches.append(sx)

    verifier_statuses: List[Dict[str, Any]] = []
    for cp in checkpoints:
        if isinstance(cp, dict):
            verifier_statuses.append(
                {
                    "phase_index": cp.get("phase_index"),
                    "verifier_status": cp.get("verifier_status"),
                    "created_at": cp.get("created_at"),
                }
            )
        else:
            verifier_statuses.append(
                {
                    "phase_index": getattr(cp, "phase_index", None),
                    "verifier_status": getattr(cp, "verifier_status", None),
                    "created_at": _iso(getattr(cp, "created_at", None)),
                }
            )

    # Policy decisions: prefer job_id filter; fall back to session_id.
    policy_decisions: List[Dict[str, Any]] = []
    pol = getattr(store, "list_tool_policy_decisions", None)
    if callable(pol):
        try:
            policy_decisions = list(pol(job_id=jid, limit=200) or [])
        except TypeError:
            # Older signature without job_id
            session_id = getattr(job, "session_id", None) if job else None
            policy_decisions = list(pol(session_id=session_id, limit=200) or []) if session_id else []
            policy_decisions = [
                r for r in policy_decisions if not r.get("job_id") or r.get("job_id") == jid
            ]

    child_job_ids: List[str] = []
    parent_job_id: Optional[str] = None
    link_get = getattr(store, "list_job_a2a_children", None)
    if callable(link_get):
        child_job_ids = [str(x) for x in (link_get(jid) or [])]
    parent_get = getattr(store, "get_job_a2a_parent", None)
    if callable(parent_get):
        parent_job_id = parent_get(jid)

    journey_events: List[Dict[str, Any]] = []
    ev_list = getattr(store, "list_standing_journey_events", None)
    if callable(ev_list):
        try:
            journey_events = list(ev_list(jid) or [])
        except Exception:
            journey_events = []

    resumed = any(
        str(e.get("kind") or "") == "resumed_from_checkpoint" for e in journey_events
    )

    timeline: List[Dict[str, Any]] = []

    if job is not None:
        timeline.append(
            {
                "kind": "job",
                "ts": _iso(getattr(job, "created_at", None)),
                "job_id": jid,
                "goal": getattr(job, "goal", None),
                "status": _status_str(job),
                "session_id": getattr(job, "session_id", None),
                "agent_id": getattr(job, "agent_id", None),
            }
        )

    for p in phases:
        timeline.append(
            {
                "kind": "phase",
                "ts": _iso(getattr(p, "updated_at", None) or getattr(p, "created_at", None)),
                "phase_id": getattr(p, "id", None),
                "phase_index": getattr(p, "index", None),
                "name": getattr(p, "name", None),
                "status": _status_str(p),
                "verify_checker": getattr(p, "verify_checker", None),
                "assigned_agent_id": getattr(p, "assigned_agent_id", None),
            }
        )

    if catalog_matches:
        timeline.append(
            {
                "kind": "catalog_match",
                "ts": _iso(getattr(checkpoints[0], "created_at", None)) if checkpoints else None,
                "matched_capability_ids": list(catalog_matches),
            }
        )

    for vs in verifier_statuses:
        timeline.append(
            {
                "kind": "verifier_status",
                "ts": vs.get("created_at"),
                "phase_index": vs.get("phase_index"),
                "verifier_status": vs.get("verifier_status"),
            }
        )

    for row in policy_decisions:
        timeline.append(
            {
                "kind": "policy_decision",
                "ts": _iso(row.get("created_at")),
                "tool_name": row.get("tool_name"),
                "verdict": row.get("verdict"),
                "reason": row.get("reason"),
                "policy_source": row.get("policy_source"),
                "mcp": str(row.get("tool_name") or "").startswith("mcp_"),
            }
        )

    for cid in child_job_ids:
        timeline.append(
            {
                "kind": "a2a_child",
                "ts": None,
                "parent_job_id": jid,
                "child_job_id": cid,
            }
        )

    for e in journey_events:
        kind = str(e.get("kind") or "event")
        timeline.append(
            {
                "kind": kind,
                "ts": _iso(e.get("created_at")),
                "payload": e.get("payload") or {},
                "resumed_from_checkpoint": kind == "resumed_from_checkpoint",
            }
        )

    # Stable sort: None ts last, then ISO string.
    def _sort_key(item: Dict[str, Any]):
        ts = item.get("ts") or ""
        return (ts == "", str(ts), str(item.get("kind") or ""))

    timeline.sort(key=_sort_key)

    # OTel-style GenAI agent span tree [REQ-SJURN-003]
    root_span_id = f"span_job_{jid}"
    spans: List[Dict[str, Any]] = []
    root_children: List[Dict[str, Any]] = []
    root = {
        "span_id": root_span_id,
        "parent_span_id": None,
        "trace_id": jid,
        "name": "standing.job",
        "kind": "GENAI_AGENT",
        "attributes": {
            "job_id": jid,
            "goal": getattr(job, "goal", None) if job else None,
            "agent_id": getattr(job, "agent_id", None) if job else None,
            "gen_ai.operation.name": "standing_job_phase",
        },
        "children": root_children,
    }
    spans.append(root)

    for p in phases:
        phase_span_id = f"span_phase_{getattr(p, 'id', getattr(p, 'index', 'x'))}"
        phase_span = {
            "span_id": phase_span_id,
            "parent_span_id": root_span_id,
            "trace_id": jid,
            "name": f"standing.phase.{getattr(p, 'name', 'phase')}",
            "kind": "INTERNAL",
            "attributes": {
                "job_id": jid,
                "phase_id": getattr(p, "id", None),
                "phase_index": getattr(p, "index", None),
                "status": _status_str(p),
            },
            "children": [],
        }
        root_children.append(phase_span)
        spans.append(phase_span)

    if catalog_matches:
        cat_span = {
            "span_id": f"span_catalog_{jid}",
            "parent_span_id": root_span_id,
            "trace_id": jid,
            "name": "standing.catalog_match",
            "kind": "INTERNAL",
            "attributes": {"job_id": jid, "matched_capability_ids": catalog_matches},
            "children": [],
        }
        root_children.append(cat_span)
        spans.append(cat_span)

    for i, row in enumerate(policy_decisions):
        pol_span = {
            "span_id": f"span_policy_{row.get('id') or i}",
            "parent_span_id": root_span_id,
            "trace_id": jid,
            "name": f"standing.policy.{row.get('verdict')}",
            "kind": "INTERNAL",
            "attributes": {
                "job_id": jid,
                "tool_name": row.get("tool_name"),
                "verdict": row.get("verdict"),
                "mcp": str(row.get("tool_name") or "").startswith("mcp_"),
            },
            "children": [],
        }
        root_children.append(pol_span)
        spans.append(pol_span)

    for cid in child_job_ids:
        child_span = {
            "span_id": f"span_a2a_{cid}",
            "parent_span_id": root_span_id,
            "trace_id": jid,
            "name": "standing.a2a_child",
            "kind": "CLIENT",
            "attributes": {"job_id": jid, "child_job_id": cid, "parent_job_id": jid},
            "children": [],
        }
        root_children.append(child_span)
        spans.append(child_span)

    # CARD-231 research-before-plan span [REQ-RESEARCH-004]
    research_events = [
        e
        for e in journey_events
        if str(e.get("kind") or "") in {"research", "research_skipped"}
    ]
    for i, e in enumerate(research_events):
        payload = e.get("payload") or {}
        inserted = bool(payload.get("research_inserted", str(e.get("kind")) == "research"))
        research_span = {
            "span_id": f"span_research_{jid}_{i}",
            "parent_span_id": root_span_id,
            "trace_id": jid,
            "name": "standing.research" if inserted else "standing.research_skipped",
            "kind": "INTERNAL",
            "attributes": {
                "job_id": jid,
                "research_inserted": inserted,
                "reason": payload.get("reason"),
                "match_count": payload.get("match_count"),
                "missing_families": payload.get("missing_families") or [],
            },
            "children": [],
        }
        root_children.append(research_span)
        spans.append(research_span)

    # Also surface Research phases as standing.research when journey event missing.
    if not research_events:
        for p in phases:
            if str(getattr(p, "name", "") or "").lower().startswith("research"):
                research_span = {
                    "span_id": f"span_research_phase_{getattr(p, 'id', 'x')}",
                    "parent_span_id": root_span_id,
                    "trace_id": jid,
                    "name": "standing.research",
                    "kind": "INTERNAL",
                    "attributes": {
                        "job_id": jid,
                        "research_inserted": True,
                        "phase_id": getattr(p, "id", None),
                        "phase_index": getattr(p, "index", None),
                    },
                    "children": [],
                }
                root_children.append(research_span)
                spans.append(research_span)

    # CARD-232 bounded auto-replan spans [REQ-REPLAN-004]
    replan_events = [
        e
        for e in journey_events
        if str(e.get("kind") or "") in {"replan", "replan_park"}
    ]
    for i, e in enumerate(replan_events):
        payload = e.get("payload") or {}
        kind = str(e.get("kind") or "replan")
        span_name = "standing.replan" if kind == "replan" else "standing.replan_park"
        replan_span = {
            "span_id": f"span_replan_{jid}_{i}",
            "parent_span_id": root_span_id,
            "trace_id": jid,
            "name": span_name,
            "kind": "INTERNAL",
            "attributes": {
                "job_id": jid,
                "replan_count": payload.get("replan_count"),
                "max_replan_attempts": payload.get("max_replan_attempts"),
                "last_fail_reason": payload.get("last_fail_reason"),
                "replan_exhausted": bool(payload.get("replan_exhausted")),
                "matched_capability_ids": payload.get("matched_capability_ids") or [],
            },
            "children": [],
        }
        root_children.append(replan_span)
        spans.append(replan_span)

    # CARD-233 mid-job self-scaffold spans [REQ-SCAFFOLD-004]
    scaffold_events = [
        e
        for e in journey_events
        if str(e.get("kind") or "")
        in {"scaffold_candidate", "scaffold_hitl", "catalog_reresolve", "re_resolve"}
    ]
    for i, e in enumerate(scaffold_events):
        payload = e.get("payload") or {}
        kind = str(e.get("kind") or "scaffold_candidate")
        if kind == "scaffold_candidate":
            span_name = "standing.scaffold_candidate"
        elif kind in {"scaffold_hitl", "hitl"}:
            span_name = "standing.scaffold_hitl"
        else:
            span_name = "standing.catalog_reresolve"
        sc_span = {
            "span_id": f"span_scaffold_{jid}_{i}",
            "parent_span_id": root_span_id,
            "trace_id": jid,
            "name": span_name,
            "kind": "INTERNAL",
            "attributes": {
                "job_id": jid,
                "record_id": payload.get("record_id"),
                "capability_id": payload.get("capability_id"),
                "trust_tier": payload.get("trust_tier"),
                "action": payload.get("action"),
                "matched_capability_ids": payload.get("matched_capability_ids") or [],
                "forge_queue": bool(payload.get("forge_queue")),
                "trusted_write": bool(payload.get("trusted_write")),
            },
            "children": [],
        }
        root_children.append(sc_span)
        spans.append(sc_span)

    if resumed:
        resume_span = {
            "span_id": f"span_resume_{jid}",
            "parent_span_id": root_span_id,
            "trace_id": jid,
            "name": "standing.resumed_from_checkpoint",
            "kind": "INTERNAL",
            "attributes": {"job_id": jid, "resumed_from_checkpoint": True},
            "children": [],
        }
        root_children.append(resume_span)
        spans.append(resume_span)

    checkpoints_out = []
    for cp in checkpoints:
        if hasattr(cp, "as_dict"):
            checkpoints_out.append(cp.as_dict())
        elif isinstance(cp, dict):
            checkpoints_out.append(cp)
        else:
            checkpoints_out.append(
                {
                    "id": getattr(cp, "id", None),
                    "job_id": getattr(cp, "job_id", None),
                    "phase_index": getattr(cp, "phase_index", None),
                    "verifier_status": getattr(cp, "verifier_status", None),
                    "matched_capability_ids": list(
                        getattr(cp, "matched_capability_ids", None) or []
                    ),
                    "research_inserted": bool(getattr(cp, "research_inserted", False)),
                    "research_reason": getattr(cp, "research_reason", "") or "",
                    "replan_count": int(getattr(cp, "replan_count", 0) or 0),
                    "last_fail_reason": getattr(cp, "last_fail_reason", "") or "",
                }
            )

    return {
        "ok": job is not None,
        "job_id": jid,
        "parent_job_id": parent_job_id,
        "child_job_ids": child_job_ids,
        "job": {
            "id": getattr(job, "id", jid) if job else jid,
            "goal": getattr(job, "goal", None) if job else None,
            "status": _status_str(job) if job else None,
            "session_id": getattr(job, "session_id", None) if job else None,
            "agent_id": getattr(job, "agent_id", None) if job else None,
            "created_at": _iso(getattr(job, "created_at", None)) if job else None,
        },
        "phases": [
            {
                "id": getattr(p, "id", None),
                "index": getattr(p, "index", None),
                "name": getattr(p, "name", None),
                "status": _status_str(p),
                "verify_checker": getattr(p, "verify_checker", None),
            }
            for p in phases
        ],
        "checkpoints": checkpoints_out,
        "catalog_matches": catalog_matches,
        "verifier_statuses": verifier_statuses,
        "policy_decisions": policy_decisions,
        "resumed_from_checkpoint": resumed,
        "timeline": timeline,
        "spans": spans,
        "correlation": {
            "filter": "job_id",
            "trace_id": jid,
            "style": "opentelemetry-genai-agent",
        },
        "assembled_at": datetime.now(timezone.utc).isoformat(),
    }
