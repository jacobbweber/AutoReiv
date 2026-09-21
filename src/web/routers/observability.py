"""
Observability, KPI Metrics & System Logs Router [REQ-WEB-005, REQ-OBS-001 - REQ-OBS-008].
"""

from dataclasses import asdict
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.domain.observability.models import TelemetryFilter

router = APIRouter(tags=["Observability"])

def _standing_journey_or_404(store: Any, job_id: str) -> Dict[str, Any]:
    """Receipt GET: existing job_id → journey; unknown → real 404 [CARD-266]."""
    from src.application.observability.standing_journey import build_standing_journey

    jid = str(job_id or "").strip()
    if not jid:
        raise HTTPException(
            status_code=404,
            detail={"ok": False, "job_id": "", "error": "job not found"},
        )
    journey = build_standing_journey(store, job_id=jid)
    if not journey.get("ok"):
        raise HTTPException(
            status_code=404,
            detail={"ok": False, "job_id": jid, "error": "job not found"},
        )
    return journey




@router.get("/api/observability/kpi")
async def get_observability_kpis(request: Request, agent_id: Optional[str] = None):
    obs_service = request.app.state.obs_service
    flt = TelemetryFilter(agent_id=agent_id) if agent_id else None
    overview = obs_service.get_overview_kpis(filter=flt)
    agents = obs_service.get_agent_breakdown()
    tools = obs_service.get_tool_reliability()
    timeline = obs_service.get_timeline(limit=24)
    return {
        "overview": overview.model_dump(),
        "agents": [a.model_dump() for a in agents],
        "tools": [t.model_dump() for t in tools],
        "timeline": [t.model_dump() for t in timeline],
    }


@router.get("/api/observability/traces")
async def get_observability_traces(
    request: Request,
    agent_id: Optional[str] = None,
    has_error: Optional[bool] = None,
    limit: int = 50,
):
    obs_service = request.app.state.obs_service
    flt = TelemetryFilter(agent_id=agent_id, has_error=has_error)
    spans = obs_service.get_traces(filter=flt, limit=limit)
    return [s.model_dump(mode="json") for s in spans]


@router.get("/api/observability/logs")
async def get_observability_logs(
    request: Request,
    limit: int = 100,
    level: Optional[str] = None,
    query: Optional[str] = None,
):
    log_buffer = request.app.state.log_buffer
    return log_buffer.get_logs(limit=limit, level=level, query=query)


@router.post("/api/observability/logs/clear")
async def clear_observability_logs(request: Request):
    log_buffer = request.app.state.log_buffer
    log_buffer.clear()
    return {"status": "success", "cleared": True}


@router.get("/api/observability/tool-policy-decisions")
async def get_tool_policy_decisions(
    request: Request,
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    job_id: Optional[str] = None,
    limit: int = 100,
):
    """Observability decision log for tool policy verdicts [CARD-221 / REQ-TOOLPOL-004]."""
    store = request.app.state.store
    lister = getattr(store, "list_tool_policy_decisions", None)
    if not callable(lister):
        return []
    return lister(session_id=session_id, agent_id=agent_id, job_id=job_id, limit=limit)


@router.get("/api/observability/job-phase-memory")
async def get_job_phase_memory(
    request: Request,
    job_id: str,
    agent_id: Optional[str] = None,
    limit: int = 50,
):
    """Checkpoint memory refs + recalled job-scoped facts [CARD-226 / REQ-JPMEM-005]."""
    store = request.app.state.store
    data_dir = getattr(request.app.state, "data_dir", None)
    if data_dir is None:
        paths = getattr(request.app.state, "data_dir_paths", None)
        data_dir = getattr(paths, "root", None) if paths is not None else None

    checkpoint = None
    getter = getattr(store, "get_latest_job_phase_checkpoint", None)
    if callable(getter):
        cp = getter(job_id)
        checkpoint = cp.as_dict() if cp is not None and hasattr(cp, "as_dict") else None

    recalled = []
    if agent_id:
        try:
            from src.application.orchestration.job_phase_memory import JobPhaseMemoryBridge

            bridge = JobPhaseMemoryBridge(agent_id=agent_id, data_dir=data_dir)
            recalled = bridge.recall_job_facts(job_id=job_id, limit=limit)
        except Exception as exc:  # noqa: BLE001
            return {
                "job_id": job_id,
                "agent_id": agent_id,
                "checkpoint": checkpoint,
                "recalled_facts": [],
                "error": str(exc),
            }

    return {
        "job_id": job_id,
        "agent_id": agent_id,
        "checkpoint": checkpoint,
        "memory_fact_ids": (checkpoint or {}).get("memory_fact_ids") or [],
        "recalled_facts": recalled,
    }


@router.get("/api/observability/standing-journey")
async def get_standing_journey(request: Request, job_id: str):
    """Standing Job/Phase journey timeline correlated by job_id [CARD-227 / REQ-SJURN-*].

    CARD-266: unknown job_id is HTTP 404 (never 200-empty theatre).
    """
    return _standing_journey_or_404(request.app.state.store, job_id)


@router.get("/api/observe/jobs/{job_id}")
async def get_observe_job_receipt(request: Request, job_id: str):
    """Canonical Observe receipt — finished/parked/in-flight job opens [CARD-266]."""
    return _standing_journey_or_404(request.app.state.store, job_id)


@router.get("/api/jobs/{job_id}")
async def get_job_receipt_alias(request: Request, job_id: str):
    """Alias of /api/observe/jobs/{job_id} so guessed REST paths are honest [CARD-266]."""
    return _standing_journey_or_404(request.app.state.store, job_id)


class AuditExportRequest(BaseModel):
    session_id: Optional[str] = None
    job_id: Optional[str] = None
    hours: Optional[int] = None
    title: Optional[str] = None


@router.get("/api/observability/sessions")
async def get_observability_sessions(
    request: Request,
    agent_id: Optional[str] = None,
    limit: int = 30,
):
    """List recent sessions for an agent to inspect in Observe Studio [CARD-337]."""
    store = request.app.state.store
    sessions = store.list_sessions(agent_id=agent_id) if hasattr(store, "list_sessions") else []
    return [
        {
            "id": s.id,
            "agent_id": s.agent_id,
            "title": s.title or f"Session {s.id[:8]}",
            "created_at": s.created_at.isoformat() if hasattr(s.created_at, "isoformat") else str(s.created_at),
            "updated_at": s.updated_at.isoformat() if hasattr(s.updated_at, "isoformat") else str(s.updated_at),
        }
        for s in sessions[:limit]
    ]


@router.get("/api/observability/audit")
async def get_observability_audit(
    request: Request,
    session_id: Optional[str] = None,
    job_id: Optional[str] = None,
    hours: Optional[int] = None,
):
    """Deterministic telemetry token attribution and cost audit [CARD-337]."""
    from src.application.observability.audit_service import AuditService

    store = request.app.state.store
    service = AuditService(store=store)

    if session_id:
        report = service.audit_session(session_id)
    elif job_id:
        report = service.audit_job(job_id)
    else:
        report = service.audit_window(hours=hours or 24)

    return {
        "report": asdict(report),
        "markdown": service.format_markdown_report(report),
    }


@router.post("/api/observability/audit/export")
async def export_observability_audit(request: Request, payload: AuditExportRequest):
    """Export deterministic performance audit markdown to 00_Inbox [CARD-337 / CARD-412 OC-2]."""
    from src.application.observability.audit_service import AuditService
    from src.web.routers.wiki import _get_wiki_service

    store = request.app.state.store
    service = AuditService(store=store)

    if payload.session_id:
        report = service.audit_session(payload.session_id)
    elif payload.job_id:
        report = service.audit_job(payload.job_id)
    else:
        report = service.audit_window(hours=payload.hours or 24)

    md = (service.format_markdown_report(report) or "").strip()
    # Honesty gate [CARD-412 / OC-2]: never claim success with an empty deliverable body
    if not md or len(md) < 40:
        raise HTTPException(
            status_code=500,
            detail="Audit export produced an empty report body; refusing empty inbox theater",
        )

    default_title = payload.title or f"Performance Audit - {report.target_type.title()} {report.target_id}"

    wiki_service = _get_wiki_service(request)
    filed = wiki_service.create_note(
        title=default_title,
        content=md,
        category="inbox",
        domain="engineering",
        topic="performance",
        document_type="report",
        tags=["telemetry", "audit", "performance"],
        summary=f"Performance and cost audit report for {report.target_type} {report.target_id}",
        status="inbox",
    )
    if not isinstance(filed, dict) or not filed.get("success"):
        raise HTTPException(status_code=500, detail="Failed to file audit report into wiki inbox")

    raw_path = str(filed.get("path") or "")
    # Read-back verification — fail closed if body did not land
    read_back = wiki_service.get_note(raw_path) if raw_path else {"success": False}
    body = (read_back.get("content") or "").strip() if isinstance(read_back, dict) else ""
    if not (isinstance(read_back, dict) and read_back.get("success") and body):
        raise HTTPException(
            status_code=500,
            detail="Audit export wrote an empty or unreadable inbox note (success theater)",
        )

    return {
        "success": True,
        "path": raw_path,
        "title": default_title,
        "filename": raw_path.replace("\\", "/").rsplit("/", 1)[-1],
        "body_chars": len(body),
        "total_tokens": report.total_tokens,
        "total_turns": report.total_turns,
    }


class FrictionAuditRequest(BaseModel):
    lookback_hours: Optional[int] = 24
    auto_apply: Optional[bool] = False


@router.post("/api/observability/friction/audit")
async def post_friction_audit(request: Request, payload: FrictionAuditRequest):
    """Run on-demand telemetry friction audit and stage runbook recommendations [CARD-354]."""
    from src.application.routines.telemetry_friction_auditor import run_telemetry_friction_audit

    store = request.app.state.store
    data_dir = getattr(request.app.state, "data_dir", None)
    if data_dir is None:
        paths = getattr(request.app.state, "data_dir_paths", None)
        data_dir = getattr(paths, "root", None) if paths is not None else None
    if data_dir is None:
        from src.infrastructure.data.resolver import DataDirResolver

        data_dir = str(DataDirResolver().platform_default())

    class DummyRoutine:
        id = "telemetry-friction-auditor"
        metadata = {
            "lookback_hours": payload.lookback_hours or 24,
            "auto_apply": payload.auto_apply or False,
        }

    result = run_telemetry_friction_audit(
        store=store,
        data_dir=data_dir,
        routine=DummyRoutine(),
        lookback_hours=payload.lookback_hours,
    )
    return result


@router.get("/api/observability/friction/recommendations")
async def get_friction_recommendations(
    request: Request,
    status: Optional[str] = None,
    limit: int = 50,
):
    """List staged runbook recommendations [CARD-354]."""
    import json
    from pathlib import Path

    store = request.app.state.store
    recs: list[dict[str, Any]] = []

    if hasattr(store, "list_proposals"):
        proposals = store.list_proposals(kind="skill", limit=limit * 2)
        for p in proposals:
            if (
                p.requested_by_job_id == "telemetry-friction-auditor"
                or "fric_" in p.id
                or "rec_" in p.id
            ):
                try:
                    data = json.loads(p.payload_json)
                    if p.status == "approved":
                        data["status"] = "applied"
                    elif p.status == "rejected":
                        data["status"] = "dismissed"
                    if status and data.get("status") != status:
                        continue
                    recs.append(data)
                except Exception:
                    pass
    if len(recs) >= limit:
        return recs[:limit]

    # Fallback to user data ledger
    data_dir = getattr(request.app.state, "data_dir", None)
    if data_dir is None:
        paths = getattr(request.app.state, "data_dir_paths", None)
        data_dir = getattr(paths, "root", None) if paths is not None else None
    if data_dir is not None:
        ledger = Path(data_dir) / "skills" / "_friction_recommendations.json"
        if ledger.is_file():
            try:
                file_recs = json.loads(ledger.read_text(encoding="utf-8"))
                existing_ids = {r.get("id") for r in recs}
                for fr in file_recs:
                    if fr.get("id") not in existing_ids:
                        if status and fr.get("status") != status:
                            continue
                        recs.append(fr)
            except Exception:
                pass

    return recs[:limit]


@router.post("/api/observability/friction/recommendations/{rec_id}/apply")
async def apply_friction_recommendation(request: Request, rec_id: str):
    """Apply a staged runbook recommendation directly to SKILL.md under user data [CARD-354]."""
    import json
    from pathlib import Path

    from src.domain.observability.models import RunbookRecommendation
    from src.domain.observability.tool_skill_resolver import ToolSkillResolver

    store = request.app.state.store
    data_dir = getattr(request.app.state, "data_dir", None)
    if data_dir is None:
        paths = getattr(request.app.state, "data_dir_paths", None)
        data_dir = getattr(paths, "root", None) if paths is not None else None
    if data_dir is None:
        from src.infrastructure.data.resolver import DataDirResolver

        data_dir = str(DataDirResolver().platform_default())

    resolver = ToolSkillResolver(data_dir=data_dir)
    target_rec: Optional[RunbookRecommendation] = None

    if hasattr(store, "get_proposal"):
        try:
            prop = store.get_proposal(rec_id)
            data = json.loads(prop.payload_json)
            target_rec = RunbookRecommendation(**data)
        except Exception:
            target_rec = None

    if target_rec is None:
        ledger = Path(data_dir) / "skills" / "_friction_recommendations.json"
        if ledger.is_file():
            try:
                file_recs = json.loads(ledger.read_text(encoding="utf-8"))
                for fr in file_recs:
                    if fr.get("id") == rec_id:
                        target_rec = RunbookRecommendation(**fr)
                        break
            except Exception:
                pass

    if target_rec is None:
        raise HTTPException(status_code=404, detail=f"Recommendation '{rec_id}' not found.")

    applied = resolver.apply_recommendation(target_rec)
    if not applied:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply recommendation to '{target_rec.skill_path}'.",
        )

    if hasattr(store, "update_proposal_status"):
        try:
            store.update_proposal_status(rec_id, "approved")
        except Exception:
            pass

    # Synchronize file ledger if present
    ledger = Path(data_dir) / "skills" / "_friction_recommendations.json"
    if ledger.is_file():
        try:
            file_recs = json.loads(ledger.read_text(encoding="utf-8"))
            for fr in file_recs:
                if fr.get("id") == rec_id:
                    fr["status"] = "applied"
            ledger.write_text(json.dumps(file_recs, indent=2), encoding="utf-8")
        except Exception:
            pass

    return {"success": True, "applied": True, "recommendation_id": rec_id}


@router.post("/api/observability/friction/recommendations/{rec_id}/dismiss")
async def dismiss_friction_recommendation(request: Request, rec_id: str):
    """Dismiss a staged runbook recommendation without altering files [CARD-354]."""
    import json
    from pathlib import Path

    store = request.app.state.store
    if hasattr(store, "update_proposal_status"):
        try:
            store.update_proposal_status(rec_id, "rejected")
        except Exception:
            pass

    data_dir = getattr(request.app.state, "data_dir", None)
    if data_dir is None:
        paths = getattr(request.app.state, "data_dir_paths", None)
        data_dir = getattr(paths, "root", None) if paths is not None else None
    if data_dir is not None:
        ledger = Path(data_dir) / "skills" / "_friction_recommendations.json"
        if ledger.is_file():
            try:
                file_recs = json.loads(ledger.read_text(encoding="utf-8"))
                for fr in file_recs:
                    if fr.get("id") == rec_id:
                        fr["status"] = "dismissed"
                ledger.write_text(json.dumps(file_recs, indent=2), encoding="utf-8")
            except Exception:
                pass

    return {"success": True, "dismissed": True, "recommendation_id": rec_id}


class ArchitecturalScanRequest(BaseModel):
    lookback_hours: int = 24
    session_limit: int = 50
    span_limit: int = 500


@router.post("/api/observability/architectural/scan")
async def post_architectural_scan(
    request: Request,
    payload: Optional[ArchitecturalScanRequest] = None,
):
    """[REQ-ARCH-006] Execute on-demand scan of telemetry spans and transcripts against God-Agent thresholds."""
    from src.application.observability.architectural_evaluator import ArchitecturalEvaluatorService

    store = getattr(request.app.state, "store", None)
    data_dir = getattr(request.app.state, "data_dir", None)
    if data_dir is None:
        paths = getattr(request.app.state, "data_dir_paths", None)
        data_dir = getattr(paths, "root", None) if paths is not None else None

    service = getattr(request.app.state, "architectural_evaluator", None)
    if service is None:
        service = ArchitecturalEvaluatorService(store=store, data_dir=data_dir)
        request.app.state.architectural_evaluator = service

    hours = payload.lookback_hours if payload else 24
    sess_limit = payload.session_limit if payload else 50
    span_limit = payload.span_limit if payload else 500

    report = service.scan_history(lookback_hours=hours, session_limit=sess_limit, span_limit=span_limit)
    return report.model_dump(mode="json")


@router.get("/api/observability/architectural/alerts")
async def get_architectural_alerts(
    request: Request,
    threshold_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
):
    """[REQ-ARCH-006] Retrieve active architectural alerts with optional threshold and severity filtering."""
    from src.application.observability.architectural_evaluator import ArchitecturalEvaluatorService

    store = getattr(request.app.state, "store", None)
    data_dir = getattr(request.app.state, "data_dir", None)
    if data_dir is None:
        paths = getattr(request.app.state, "data_dir_paths", None)
        data_dir = getattr(paths, "root", None) if paths is not None else None

    service = getattr(request.app.state, "architectural_evaluator", None)
    if service is None:
        service = ArchitecturalEvaluatorService(store=store, data_dir=data_dir)
        request.app.state.architectural_evaluator = service

    alerts = service.list_alerts(threshold_type=threshold_type, severity=severity, limit=limit)
    return {"alerts": [a.model_dump(mode="json") for a in alerts]}


def _get_architectural_proposal_service(request: Request):
    store = getattr(request.app.state, "store", None)
    data_dir = getattr(request.app.state, "data_dir", None)
    if data_dir is None:
        paths = getattr(request.app.state, "data_dir_paths", None)
        data_dir = getattr(paths, "root", None) if paths is not None else None

    service = getattr(request.app.state, "architectural_proposals", None)
    if service is None:
        from src.application.observability.architectural_proposals import ArchitecturalProposalService

        service = ArchitecturalProposalService(store=store, data_dir=data_dir)
        request.app.state.architectural_proposals = service
    return service


@router.get("/api/observability/architectural/proposals")
async def get_architectural_proposals(
    request: Request,
    status: Optional[str] = "pending",
    agent_id: Optional[str] = None,
    proposal_type: Optional[str] = None,
    limit: int = 50,
):
    """[REQ-ARCH-012] Retrieve architectural proposals with status and agent filtering."""
    service = _get_architectural_proposal_service(request)
    proposals = service.list_proposals(
        status=status,
        agent_id=agent_id,
        proposal_type=proposal_type,
        limit=limit,
    )
    return {"proposals": [p.model_dump(mode="json") for p in proposals]}


@router.post("/api/observability/architectural/proposals/generate")
async def post_generate_proposals(
    request: Request,
):
    """[REQ-ARCH-012] Trigger proposal synthesis from current architectural threshold alerts."""
    service = _get_architectural_proposal_service(request)
    new_proposals = service.generate_from_alerts()
    return {
        "success": True,
        "generated_count": len(new_proposals),
        "proposals": [p.model_dump(mode="json") for p in new_proposals],
    }


@router.post("/api/observability/architectural/proposals/{proposal_id}/apply")
async def post_apply_proposal(
    request: Request,
    proposal_id: str,
):
    """[REQ-ARCH-012] Execute one-click remedy for an architectural proposal."""
    service = _get_architectural_proposal_service(request)
    result = service.apply_proposal(proposal_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to apply proposal"))
    return result


@router.post("/api/observability/architectural/proposals/{proposal_id}/dismiss")
async def post_dismiss_proposal(
    request: Request,
    proposal_id: str,
):
    """[REQ-ARCH-012] Dismiss an architectural proposal."""
    service = _get_architectural_proposal_service(request)
    result = service.dismiss_proposal(proposal_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to dismiss proposal"))
    return result




