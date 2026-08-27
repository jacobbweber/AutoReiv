"""
Autonomous Routine Engine & Schedule Execution Router [REQ-WEB-006, REQ-ROUT-001 - REQ-ROUT-003].
"""

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.domain.routines.models import Routine, RoutineStatus, ScheduleType


class RoutinePayload(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    agent_id: str
    schedule_type: Optional[str] = "cron"
    cron_expr: Optional[str] = "0 * * * *"
    interval_seconds: Optional[int] = 3600
    prompt_template: str
    enabled: Optional[bool] = True


router = APIRouter(tags=["Routines"])


@router.get("/api/routines")
async def list_routines(request: Request, agent_id: Optional[str] = None):
    from src.application.routines.humanizer import compute_next_run_eta, cron_to_human

    store = request.app.state.store
    routines = store.list_routines(agent_id=agent_id)
    result = []
    for r in routines:
        if r.cron_expression:
            human_sched = cron_to_human(r.cron_expression)
            _, next_eta = compute_next_run_eta(r.cron_expression)
        else:
            human_sched = f"Every {r.interval_seconds}s"
            next_eta = f"in {r.interval_seconds // 60}m" if r.interval_seconds else "hourly"

        result.append(
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "agent_id": r.agent_id,
                "prompt": r.prompt,
                "schedule_type": r.schedule_type.value if hasattr(r.schedule_type, "value") else str(r.schedule_type),
                "interval_seconds": r.interval_seconds,
                "cron_expression": r.cron_expression,
                "human_schedule": human_sched,
                "next_run_eta": next_eta,
                "enabled": r.enabled,
                "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
                "next_run_at": r.next_run_at.isoformat() if r.next_run_at else None,
                "last_status": r.last_status.value if hasattr(r.last_status, "value") else str(r.last_status),
            }
        )
    return result


@router.post("/api/routines")
async def create_routine(request: Request, payload: RoutinePayload):
    store = request.app.state.store
    routine_id = payload.id.strip() if payload.id else re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")

    sched_type = (
        ScheduleType(payload.schedule_type)
        if payload.schedule_type in [s.value for s in ScheduleType]
        else ScheduleType.CRON
    )

    routine = Routine(
        id=routine_id,
        name=payload.name,
        description=payload.description or "",
        agent_id=payload.agent_id,
        prompt=payload.prompt_template,
        schedule_type=sched_type,
        interval_seconds=payload.interval_seconds or 3600,
        cron_expression=payload.cron_expr or "0 * * * *",
        enabled=payload.enabled if payload.enabled is not None else True,
        last_status=RoutineStatus.IDLE,
    )

    store.save_routine(routine)
    return {"status": "created", "routine": routine.model_dump(mode="json")}


@router.put("/api/routines/{routine_id}")
async def update_routine(request: Request, routine_id: str, payload: RoutinePayload):
    store = request.app.state.store
    existing = store.get_routine(routine_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Routine '{routine_id}' not found")

    sched_type = (
        ScheduleType(payload.schedule_type)
        if payload.schedule_type in [s.value for s in ScheduleType]
        else existing.schedule_type
    )

    routine = Routine(
        id=routine_id,
        name=payload.name or existing.name,
        description=payload.description if payload.description is not None else existing.description,
        agent_id=payload.agent_id or existing.agent_id,
        prompt=payload.prompt_template or existing.prompt,
        schedule_type=sched_type,
        interval_seconds=payload.interval_seconds or existing.interval_seconds,
        cron_expression=payload.cron_expr or existing.cron_expression,
        enabled=payload.enabled if payload.enabled is not None else existing.enabled,
        last_run_at=existing.last_run_at,
        next_run_at=existing.next_run_at,
        last_status=existing.last_status,
    )

    store.save_routine(routine)
    return {"status": "updated", "routine": routine.model_dump(mode="json")}


@router.post("/api/routines/{routine_id}/toggle")
async def toggle_routine(request: Request, routine_id: str):
    store = request.app.state.store
    new_state = store.toggle_routine(routine_id)
    if new_state is None:
        raise HTTPException(status_code=404, detail=f"Routine '{routine_id}' not found")
    return {"status": "toggled", "id": routine_id, "enabled": new_state}


@router.delete("/api/routines/{routine_id}")
async def delete_routine(request: Request, routine_id: str):
    store = request.app.state.store
    deleted = store.delete_routine(routine_id)
    if not deleted:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete routine '{routine_id}' (protected or not found).",
        )
    return {"status": "deleted", "id": routine_id}


@router.post("/api/routines/{routine_id}/trigger")
@router.post("/api/routines/{routine_id}/run")
async def trigger_routine(request: Request, routine_id: str):
    store = request.app.state.store
    routine_executor = request.app.state.routine_executor

    routine = store.get_routine(routine_id)
    if not routine:
        raise HTTPException(status_code=404, detail=f"Routine '{routine_id}' not found")
    run = await routine_executor.execute_routine(routine)
    return {
        "id": run.id,
        "routine_id": run.routine_id,
        "status": run.status.value,
        "output": run.output,
        "error_message": run.error_message,
        "duration_ms": run.duration_ms,
        "created_at": run.created_at.isoformat(),
    }
