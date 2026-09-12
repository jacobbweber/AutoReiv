"""
Observability, KPI Metrics & System Logs Router [REQ-WEB-005, REQ-OBS-001 - REQ-OBS-008].
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

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

