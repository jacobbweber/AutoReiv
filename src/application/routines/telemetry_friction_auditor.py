"""
Autonomous Telemetry Friction Auditor Task [CARD-354 / REQ-ROUTINE-010].
Audits recent conversation spans for procedural friction and stages runbook optimizations.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Union

from src.domain.observability.friction_analyzer import TelemetryFrictionAnalyzer
from src.domain.observability.friction_dedup import (
    DEFAULT_COOLDOWN_DAYS,
    blocks_new_recommendation,
    friction_key,
    normalize_friction_rec,
    recommendation_status,
)
from src.domain.observability.models import RunbookRecommendation
from src.domain.observability.tool_skill_resolver import ToolSkillResolver
from src.domain.orchestration.models import Proposal, ProposalKind, ProposalStatus

ROUTINE_ID = "telemetry-friction-auditor"
_EXISTING_SCAN_LIMIT = 2000


def blocking_friction_keys(
    store: Any, *, now: Optional[datetime] = None, cooldown_days: float = DEFAULT_COOLDOWN_DAYS
) -> Set[Tuple[str, str, str]]:
    """Keys of staged recommendations that still block a new one [CARD-525].

    Pending and escalated block; dismissed and applied block for ``cooldown_days`` after the decision.
    """
    keys: Set[Tuple[str, str, str]] = set()
    if not store or not hasattr(store, "list_proposals"):
        return keys
    try:
        proposals = store.list_proposals(kind=ProposalKind.SKILL, limit=_EXISTING_SCAN_LIMIT)
    except Exception:
        return keys
    for ep in proposals:
        try:
            data = normalize_friction_rec(json.loads(ep.payload_json))
        except Exception:
            continue
        if not data.get("friction_type"):
            continue  # not a friction recommendation
        status = recommendation_status(ep.status, data.get("status"))
        decided = getattr(ep, "updated_at", None) if status in ("dismissed", "applied") else None
        if blocks_new_recommendation(status, decided, now=now, cooldown_days=cooldown_days):
            keys.add(friction_key(data))
    return keys


def builtin_tool_names(tool_registry: Any) -> Optional[Set[str]]:
    """Tools that are Python in this repo: not runtime-built (native_custom) and not MCP [CARD-527]."""
    names = getattr(tool_registry, "builtin_tool_names", None)
    if not callable(names):
        return None
    try:
        return set(names())
    except Exception:
        return None


def agent_skill_lookup(agent_registry: Any) -> Optional[Callable[[str], Iterable[str]]]:
    """Ticked skills of an agent, so a tool maps to the caller's own skill first [CARD-527]."""
    get_profile = getattr(agent_registry, "get_profile", None)
    if not callable(get_profile):
        return None
    from src.application.agent_skills.allowed_tools import ticked_skills

    def lookup(agent_id: str) -> Iterable[str]:
        try:
            profile = get_profile(agent_id)
        except Exception:
            return []
        return ticked_skills(profile) if profile is not None else []

    return lookup


def run_telemetry_friction_audit(
    store: Any,
    data_dir: Union[str, Path],
    *,
    routine: Any = None,
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    lookback_hours: Optional[int] = None,
    tool_registry: Any = None,
    agent_registry: Any = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Executes telemetry friction audit across recent conversation traces.
    Stages recommendations in SQLite proposals table and user data.
    """
    data_root = Path(data_dir).expanduser().resolve()
    analyzer = TelemetryFrictionAnalyzer(store=store)
    resolver = ToolSkillResolver(data_dir=data_root)

    meta = dict(getattr(routine, "metadata", None) or {})
    hours = lookback_hours or meta.get("lookback_hours", 24)
    auto_apply = bool(meta.get("auto_apply", False))
    try:
        cooldown_days = float(meta.get("dismissed_cooldown_days", DEFAULT_COOLDOWN_DAYS))
    except (TypeError, ValueError):
        cooldown_days = float(DEFAULT_COOLDOWN_DAYS)
    builtin = builtin_tool_names(tool_registry)
    skills_of = agent_skill_lookup(agent_registry)

    incidents = analyzer.scan_recent_sessions(lookback_hours=hours)

    recommendations: List[RunbookRecommendation] = []
    applied_count = 0

    # CARD-525: one per (agent, tool, friction); decided ones block only for the cool-down.
    existing_keys = blocking_friction_keys(store, now=now, cooldown_days=cooldown_days)

    for inc in incidents:
        rec = resolver.synthesize_recommendation(
            inc,
            builtin_tools=builtin,
            agent_skill_ids=list(skills_of(inc.agent_id)) if skills_of else None,
        )
        dedup_key = friction_key(rec.model_dump())
        if dedup_key in existing_keys:
            continue
        existing_keys.add(dedup_key)

        if auto_apply and rec.remedy_kind == "runbook_patch":
            seed_user_skill_copy(data_root, rec.skill_id)
            applied = resolver.apply_recommendation(rec)
            if applied:
                rec.status = "applied"
                applied_count += 1

        recommendations.append(rec)

        # Stage proposal in SQLite proposals table
        if store and hasattr(store, "create_proposal"):
            try:
                store.create_proposal(
                    Proposal(
                        id=rec.id,
                        kind=ProposalKind.SKILL,
                        payload_json=rec.model_dump_json(),
                        status=ProposalStatus.APPROVED if rec.status == "applied" else ProposalStatus.DRAFT,
                        requested_by_job_id=getattr(routine, "id", ROUTINE_ID) or ROUTINE_ID,
                    )
                )
            except Exception:
                pass

    # Save to user-data JSON ledger for file-based inspection
    rec_ledger = data_root / "skills" / "_friction_recommendations.json"
    try:
        existing_recs: List[Dict[str, Any]] = []
        if rec_ledger.is_file():
            try:
                existing_recs = json.loads(rec_ledger.read_text(encoding="utf-8"))
            except Exception:
                existing_recs = []
        existing_ids = {r.get("id") for r in existing_recs}
        for r in recommendations:
            if r.id not in existing_ids:
                existing_recs.append(r.model_dump(mode="json"))
        rec_ledger.parent.mkdir(parents=True, exist_ok=True)
        rec_ledger.write_text(json.dumps(existing_recs, indent=2), encoding="utf-8")
    except Exception:
        pass

    return {
        "success": True,
        "status": "success",
        "incidents_count": len(incidents),
        "recommendations_count": len(recommendations),
        "auto_applied_count": applied_count,
        "recommendations": [r.model_dump(mode="json") for r in recommendations],
        "summary": (
            f"Audited recent telemetry: identified {len(incidents)} friction incidents, "
            f"staged {len(recommendations)} runbook recommendations ({applied_count} auto-applied)."
        ),
    }

def seed_user_skill_copy(data_dir: Union[str, Path], skill_id: Optional[str]) -> bool:
    """Write the user copy of a shipped-only skill so a runbook patch has a file to edit [CARD-527].

    The resolver maps tools to shipped skills too, but patches only edit data-dir user copies
    (``skills/<id>/SKILL.md``); without this a patch on a shipped skill failed with "no longer exists".
    """
    sid = str(skill_id or "").strip()
    if not sid:
        return False
    try:
        from src.infrastructure.content.store import get_store

        content = get_store()
        if content.data_root is None or Path(content.data_root).resolve() != Path(data_dir).resolve():
            return False
        user = content.skills.user_path(sid)
        if user is None or user.is_file():
            return False
        loaded = content.skills.load(sid)
        if loaded is None or loaded.source != "shipped":
            return False
        content.skills.save(sid, dict(loaded.meta), loaded.body)
        return True
    except Exception:
        return False
