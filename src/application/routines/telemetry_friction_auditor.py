"""
Autonomous Telemetry Friction Auditor Task [CARD-354 / REQ-ROUTINE-010].
Audits recent conversation spans for procedural friction and stages runbook optimizations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.domain.observability.friction_analyzer import TelemetryFrictionAnalyzer
from src.domain.observability.models import RunbookRecommendation
from src.domain.observability.tool_skill_resolver import ToolSkillResolver
from src.domain.orchestration.models import Proposal, ProposalKind, ProposalStatus

ROUTINE_ID = "telemetry-friction-auditor"


def run_telemetry_friction_audit(
    store: Any,
    data_dir: Union[str, Path],
    *,
    routine: Any = None,
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    lookback_hours: Optional[int] = None,
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

    incidents = analyzer.scan_recent_sessions(lookback_hours=hours)

    recommendations: List[RunbookRecommendation] = []
    applied_count = 0

    for inc in incidents:
        rec = resolver.synthesize_recommendation(inc)
        if auto_apply and rec.remedy_kind == "runbook_patch":
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
