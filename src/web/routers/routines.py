"""
Autonomous Routine Engine & Schedule Execution Router [REQ-WEB-006, REQ-ROUT-001 - REQ-ROUT-003].
CARD-310: structured schedule_rule + preview.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.application.routines.matcher import ScheduleMatcher
from src.domain.routines.models import Routine, RoutineStatus, ScheduleType
from src.domain.routines.schedule_rule import (
    get_schedule_rule,
    normalize_schedule_rule,
    preview_structured,
    rule_to_cron,
    rule_to_human,
    set_schedule_rule_on_metadata,
)


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
    approval_mode: Optional[str] = "ask"
    schedule_rule: Optional[Dict[str, Any]] = None


class SchedulePreviewPayload(BaseModel):
    schedule_rule: Optional[Dict[str, Any]] = None
    cron_expr: Optional[str] = None
    schedule_type: Optional[str] = None
    from_time: Optional[str] = None


router = APIRouter(tags=["Routines"])


def _serialize_routine(r: Routine, builtin_ids: set) -> Dict[str, Any]:
    from src.application.routines.humanizer import compute_next_run_eta, cron_to_human

    rule = get_schedule_rule(r)
    if rule is not None:
        human_sched = rule_to_human(rule)
        if r.next_run_at:
            next_eta = r.next_run_at.isoformat()
        else:
            prev = preview_structured(rule)
            next_eta = prev.get("next_run_at") or "scheduled"
    elif r.cron_expression:
        human_sched = cron_to_human(r.cron_expression)
        _, next_eta = compute_next_run_eta(r.cron_expression)
    else:
        human_sched = f"Every {r.interval_seconds}s"
        next_eta = f"in {r.interval_seconds // 60}m" if r.interval_seconds else "hourly"

    return {
        "id": r.id,
        "name": r.name,
        "description": r.description,
        "agent_id": r.agent_id,
        "prompt": r.prompt,
        "schedule_type": r.schedule_type.value if hasattr(r.schedule_type, "value") else str(r.schedule_type),
        "interval_seconds": r.interval_seconds,
        "cron_expression": r.cron_expression,
        "schedule_rule": rule,
        "human_schedule": human_sched,
        "next_run_eta": next_eta,
        "enabled": r.enabled,
        "is_builtin": r.id in builtin_ids,
        "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
        "next_run_at": r.next_run_at.isoformat() if r.next_run_at else None,
        "last_status": r.last_status.value if hasattr(r.last_status, "value") else str(r.last_status),
        "approval_mode": "run" if str((r.metadata or {}).get("approval_mode") or "").strip().lower() == "run" else "ask",
    }


def _build_routine_from_payload(payload: RoutinePayload, *, routine_id: str, existing: Optional[Routine] = None) -> Routine:
    has_rule = payload.schedule_rule is not None
    if has_rule:
        sched_type = ScheduleType.STRUCTURED
        rule = normalize_schedule_rule(payload.schedule_rule)
        cron = rule_to_cron(rule)
    else:
        sched_type = (
            ScheduleType(payload.schedule_type)
            if payload.schedule_type in [s.value for s in ScheduleType]
            else (existing.schedule_type if existing else ScheduleType.CRON)
        )
        if sched_type == ScheduleType.STRUCTURED and existing:
            rule = get_schedule_rule(existing)
            cron = rule_to_cron(rule) if rule else (payload.cron_expr or existing.cron_expression)
        else:
            rule = None
            cron = payload.cron_expr or (existing.cron_expression if existing else "0 * * * *")

    base_meta = dict(existing.metadata or {}) if existing else {}
    base_meta["approval_mode"] = "run" if str(payload.approval_mode or "").strip().lower() == "run" else "ask"
    if has_rule:
        base_meta = set_schedule_rule_on_metadata(base_meta, rule)
    elif existing and get_schedule_rule(existing) and sched_type != ScheduleType.STRUCTURED:
        if payload.schedule_type in ("cron", "interval"):
            base_meta = set_schedule_rule_on_metadata(base_meta, None)

    kwargs = dict(
        id=routine_id,
        name=payload.name or (existing.name if existing else ""),
        description=payload.description if payload.description is not None else (existing.description if existing else ""),
        agent_id=payload.agent_id or (existing.agent_id if existing else ""),
        prompt=payload.prompt_template or (existing.prompt if existing else ""),
        schedule_type=sched_type,
        interval_seconds=payload.interval_seconds or (existing.interval_seconds if existing else 3600),
        cron_expression=cron,
        enabled=payload.enabled if payload.enabled is not None else (existing.enabled if existing else True),
        last_run_at=existing.last_run_at if existing else None,
        next_run_at=existing.next_run_at if existing else None,
        last_status=existing.last_status if existing else RoutineStatus.IDLE,
        metadata=base_meta,
    )
    if existing is not None:
        kwargs["created_at"] = existing.created_at
    routine = Routine(**kwargs)
    routine.next_run_at = ScheduleMatcher.compute_next_run(routine)
    return routine


@router.get("/api/routines")
async def list_routines(request: Request, agent_id: Optional[str] = None):
    from src.domain.routines.manifests import BUILTIN_ROUTINES

    builtin_ids = {r.id for r in BUILTIN_ROUTINES}
    store = request.app.state.store
    routines = store.list_routines(agent_id=agent_id)
    return [_serialize_routine(r, builtin_ids) for r in routines]


@router.post("/api/routines/preview-schedule")
async def preview_schedule(payload: SchedulePreviewPayload):
    """CARD-310: thin next-fire + cron preview for structured (or cron) rules."""
    from src.application.routines.humanizer import compute_next_run_eta, cron_to_human

    from_time = None
    if payload.from_time:
        try:
            from_time = datetime.fromisoformat(payload.from_time.replace("Z", "+00:00"))
        except ValueError:
            from_time = None

    if payload.schedule_rule is not None:
        result = preview_structured(payload.schedule_rule, base_time=from_time)
        return result

    cron = (payload.cron_expr or "").strip()
    if cron:
        nxt, eta = compute_next_run_eta(cron, from_time=from_time)
        return {
            "next_run_at": nxt.isoformat(),
            "cron_expression": cron,
            "cron_representable": True,
            "human": cron_to_human(cron),
            "next_run_eta": eta,
        }

    raise HTTPException(status_code=400, detail="Provide schedule_rule or cron_expr")


@router.post("/api/routines")
async def create_routine(request: Request, payload: RoutinePayload):
    store = request.app.state.store
    routine_id = payload.id.strip() if payload.id else re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")
    routine = _build_routine_from_payload(payload, routine_id=routine_id, existing=None)
    store.save_routine(routine)
    return {"status": "created", "routine": routine.model_dump(mode="json")}


@router.put("/api/routines/{routine_id}")
async def update_routine(request: Request, routine_id: str, payload: RoutinePayload):
    store = request.app.state.store
    existing = store.get_routine(routine_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Routine '{routine_id}' not found")

    routine = _build_routine_from_payload(payload, routine_id=routine_id, existing=existing)
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
    refreshed = store.get_routine(routine_id)
    meta_job = (refreshed.metadata or {}).get("last_standing_job_id") if refreshed else None
    return {
        "id": run.id,
        "routine_id": run.routine_id,
        "status": run.status.value,
        "output": run.output,
        "error_message": run.error_message,
        "duration_ms": run.duration_ms,
        "created_at": run.created_at.isoformat(),
        "job_id": getattr(run, "job_id", None) or meta_job,
    }
