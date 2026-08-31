"""
Observability, KPI Metrics & System Logs Router [REQ-WEB-005, REQ-OBS-001 - REQ-OBS-008].
"""

from typing import Optional

from fastapi import APIRouter, Request

from src.domain.observability.models import TelemetryFilter

router = APIRouter(tags=["Observability"])


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
