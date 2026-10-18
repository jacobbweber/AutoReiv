"""
Plan review approval resumption, remaining phase continuation on resume, and catalog job minting [CARD-713].
"""

from __future__ import annotations

import logging
from typing import Any, List

from src.application.chat.job_runner import (
    _chat_override,
    _ensure_phase_session,
    execute_goal_job_phases,
    execute_goal_plan_steps,
    profile_for_phase,
    relay_phase_reply_to_parent,
)
from src.application.chat.turn_streamer import _sse, _stream_turn_bound
from src.application.orchestration.chat_job_binding import (
    WAITING_FOR_ANSWER_NOTE,
    latest_open_job_for_session,
    persist_plan_as_job,
)
from src.application.orchestration.job_phase_memory import prior_lines_from_job_memory
from src.application.orchestration.operator_answer import (
    operator_answer_note_for_session,
    prepend_operator_answers,
)
from src.application.orchestration.working_set_context import (
    build_phase_working_set,
    distill_durable_note,
    format_phase_working_set_prompt,
    rebuild_working_set_after_resume,
    resolve_matched_metadata_for_job,
)
from src.domain.gateway.models import ChatMessage, Role
from src.domain.orchestration.models import PhaseStatus
from src.domain.planning.models import ExecutionPlan, PlanStep

GOAL_PLAN_REVIEW_TOOL = "goal_plan_review"

logger = logging.getLogger(__name__)


def last_goal_review_resume(store, session_id: str):
    """Return (status, approval record) when the last TOOL is a plan-review decide row."""
    try:
        msgs = store.get_messages(session_id=session_id)
    except Exception:
        return None
    last_tool = None
    for msg in reversed(list(msgs or [])):
        if getattr(msg, "role", None) == Role.TOOL:
            last_tool = msg
            break
    if not last_tool or getattr(last_tool, "name", None) != GOAL_PLAN_REVIEW_TOOL:
        return None
    tcid = getattr(last_tool, "tool_call_id", None) or ""
    if not str(tcid).startswith("resume_"):
        return None
    record = store.get_approval(str(tcid)[len("resume_") :])
    if not record:
        return None
    return str(record.get("status") or "").lower(), record


def execution_plan_from_approval(record: dict, session_id: str, agent_id: str):
    args = record.get("arguments") or {}
    raw_steps = args.get("steps") or []
    steps = []
    for i, raw in enumerate(raw_steps, 1):
        if not isinstance(raw, dict):
            continue
        steps.append(
            PlanStep(
                id=f"step_{i}",
                title=str(raw.get("title") or f"Step {i}"),
                description=str(raw.get("description") or ""),
            )
        )
    if not steps:
        return None
    plan = ExecutionPlan(
        id=str(args.get("plan_id") or "plan_review"),
        goal=str(args.get("goal") or ""),
        agent_id=agent_id,
        session_id=session_id,
        steps=steps,
    )
    self_verify = bool(args.get("self_verify"))
    approval_mode = str(args.get("approval_mode") or "ask")
    job_id = args.get("job_id")
    verify_checker = args.get("verify_checker")
    return plan, self_verify, approval_mode, job_id, verify_checker


def checkpoint_store_open_jobs(store: Any, session_id: str, default_checkpoint: dict) -> dict:
    """Store-only fallback when aborting a session without JobPhaseOrchestrator [CARD-259]."""
    checkpoint = dict(default_checkpoint)
    if not store or not hasattr(store, "list_jobs_for_session"):
        return checkpoint
    try:
        from src.application.orchestration.kill_resume import (
            OPERATOR_KILL_REASON,
            kill_checkpoint_payload,
        )

        jobs = store.list_jobs_for_session(session_id) or []
        for j in jobs:
            status = j.status.value if hasattr(j.status, "value") else str(j.status)
            if status in ("done", "failed", "cancelled"):
                continue
            phases = store.list_phases_for_job(j.id) if hasattr(store, "list_phases_for_job") else []
            for p in phases:
                pstatus = p.status.value if hasattr(p.status, "value") else str(p.status)
                if pstatus == "running" and hasattr(store, "update_phase_status"):
                    store.update_phase_status(p.id, "queued")
                    checkpoint = kill_checkpoint_payload(
                        job_id=j.id,
                        phase_id=p.id,
                        checkpointed=True,
                        reason=OPERATOR_KILL_REASON,
                    )
                    break
            if checkpoint.get("checkpointed"):
                break
    except Exception as e:
        logger.warning("Failed to leave jobs resumable on abort: %s", e)
    return checkpoint


async def resume_goal_review_if_any(
    *,
    queue,
    store,
    kernel,
    orch,
    reflexion_engine,
    profile,
    session_id: str,
    approval_mode: str,
) -> bool:
    """Handle a resumed goal_plan_review approval if present; returns True if handled."""
    review = last_goal_review_resume(store, session_id)
    if not review:
        return False
    status, record = review
    if status in {"rejected", "reject"}:
        args = record.get("arguments") or {}
        if orch is not None and args.get("job_id"):
            try:
                orch.cancel_job(str(args["job_id"]))
            except Exception:
                logger.exception("Failed to cancel rejected goal job")
        msg = "Plan rejected. Steps were not executed. Send a message to revise."
        store.save_message(
            session_id=session_id,
            agent_id=profile.id,
            message=ChatMessage(role=Role.ASSISTANT, content=msg),
        )
        await queue.put(_sse("token", {"text": msg}))
        await queue.put(_sse("turn_done", {"content": msg}))
        return True
    if status in {"approved", "approve"}:
        rebuilt = execution_plan_from_approval(record, session_id, profile.id)
        if rebuilt:
            plan, stored_verify, stored_mode, job_id, stored_checker = rebuilt
            job = None
            if orch is not None and job_id:
                try:
                    job = store.get_job(str(job_id))
                except Exception:
                    job = None
            if orch is not None and job is None:
                job = persist_plan_as_job(
                    orch,
                    plan,
                    verify_checker=stored_checker if stored_verify else None,
                )
            await execute_goal_plan_steps(
                queue=queue,
                store=store,
                kernel=kernel,
                reflexion_engine=reflexion_engine,
                profile=profile,
                plan=plan,
                session_id=session_id,
                self_verify=stored_verify,
                approval_mode=stored_mode or approval_mode or "ask",
                orch=orch,
                job=job,
            )
            return True
    return False


async def continue_remaining_resumed_phases(
    *,
    queue,
    store,
    kernel,
    orch,
    reflexion_engine,
    profile,
    registry,
    job,
    finished_phase,
    resume_session: str,
    parent_session_id: str,
    approval_mode: str,
    effective_content: str,
    answer_job: Any = None,
) -> None:
    """Continue any remaining QUEUED phases after a resumed phase finishes [CARD-226, CARD-253, CARD-548]."""
    last_phase_session = resume_session
    remaining = [
        p
        for p in store.list_phases_for_job(job.id)
        if p.status == PhaseStatus.QUEUED
    ]
    answer_notes: List[str] = []
    if answer_job is not None and (effective_content or "").strip():
        note = operator_answer_note_for_session(store, resume_session, effective_content)
        if note:
            answer_notes.append(note)
    memory_facts = list(
        prior_lines_from_job_memory(
            agent_id=profile.id,
            job_id=job.id,
            data_dir=getattr(orch, "_data_dir", None),
        )
    )
    if memory_facts:
        await queue.put(
            _sse(
                "memory_recalled",
                {
                    "job_id": job.id,
                    "agent_id": profile.id,
                    "count": len(memory_facts),
                    "facts": memory_facts[:20],
                    "source": "agent_memory.db",
                    "resumed": True,
                },
            )
        )
    matched_metadata = resolve_matched_metadata_for_job(orch, job.id)
    durable_notes: List[str] = prepend_operator_answers([], *answer_notes)
    if answer_notes:
        refreshed_answered = store.get_phase(finished_phase.id)
        durable_notes.append(
            distill_durable_note(
                phase_name=finished_phase.name,
                phase_index=finished_phase.index,
                raw_output=refreshed_answered.output_packet_json or "",
            )
        )
    stream_bound_fn = _chat_override("_stream_turn_bound", _stream_turn_bound)
    for nxt in remaining:
        started = orch.start_phase(nxt.id)
        bound_skill_id = None
        bound_skill_body = None
        bind_fn = getattr(orch, "bind_matched_skill_on_phase_start", None)
        if callable(bind_fn):
            for bound in bind_fn(started.id) or []:
                await queue.put(
                    _sse(
                        "skill_bound",
                        {
                            "job_id": job.id,
                            "phase_id": started.id,
                            "phase_name": started.name,
                            "skill_id": bound.get("skill_id"),
                            "runbook_id": bound.get("runbook_id"),
                            "title": bound.get("title"),
                            "body_loaded": bool(bound.get("body_loaded")),
                            "success": bool(bound.get("success")),
                            "body_chars": len(bound.get("body") or "")
                            if bound.get("success")
                            else 0,
                            "progressive": True,
                            "resumed": True,
                        },
                    )
                )
                if bound.get("success") and bound.get("body"):
                    bound_skill_id = bound.get("skill_id")
                    bound_skill_body = bound.get("body")
        memory_facts = list(
            prior_lines_from_job_memory(
                agent_id=profile.id,
                job_id=job.id,
                data_dir=getattr(orch, "_data_dir", None),
            )
        )
        if not durable_notes:
            ws = rebuild_working_set_after_resume(
                job=job,
                phase=started,
                phase_count=len(store.list_phases_for_job(job.id)),
                all_memory_facts=memory_facts,
                matched_metadata=matched_metadata,
                bound_skill_id=bound_skill_id,
                bound_skill_body=bound_skill_body,
                session_transcript=None,
            )
        else:
            ws = build_phase_working_set(
                job=job,
                phase=started,
                phase_count=len(store.list_phases_for_job(job.id)),
                matched_metadata=matched_metadata,
                bound_skill_id=bound_skill_id,
                bound_skill_body=bound_skill_body,
                prior_phase_notes=durable_notes,
                all_memory_facts=memory_facts,
            )
        assignment = format_phase_working_set_prompt(ws)
        run_profile = profile_for_phase(profile, started, registry)
        phase_session = _ensure_phase_session(store, parent_session_id, started, run_profile.id)
        nxt_outcome = await stream_bound_fn(
            queue=queue,
            kernel=kernel,
            orch=orch,
            store=store,
            reflexion_engine=reflexion_engine,
            profile=run_profile,
            session_id=phase_session,
            user_content=assignment,
            approval_mode=approval_mode or "ask",
            resume=False,
            job=job,
            phase=started,
            self_verify=bool(started.verify_checker),
            step_index=started.index,
            emit_step_events=True,
        )
        if nxt_outcome == "question":
            shown = [
                relay_phase_reply_to_parent(store, parent_session_id, s, profile.id)
                for s in (last_phase_session, phase_session)
            ]
            text = "\n\n".join(t for t in shown if t)
            await queue.put(_sse("token", {"text": f"{text}\n\n{WAITING_FOR_ANSWER_NOTE}\n"}))
            await queue.put(_sse("turn_done", {"waiting_answer": True, "job_id": job.id}))
        if nxt_outcome != "done":
            last_phase_session = ""
            break
        last_phase_session = phase_session
        refreshed = store.get_phase(started.id)
        durable_notes.append(
            distill_durable_note(
                phase_name=started.name,
                phase_index=started.index,
                raw_output=refreshed.output_packet_json or "",
            )
        )
    relayed = relay_phase_reply_to_parent(store, parent_session_id, last_phase_session, profile.id)
    if relayed:
        await queue.put(_sse("token", {"text": relayed}))
        await queue.put(_sse("turn_done", {"content": relayed}))


async def check_job_mint_preconditions(
    *,
    queue,
    store,
    orch,
    profile,
    session_id: str,
    effective_content: str,
) -> bool:
    """
    Validate that no parked HITL job owns ``session_id`` [CARD-251] and that ``orch`` can mint a standing job [CARD-236].
    Returns True if preconditions pass; emits SSE error + turn_done and returns False otherwise.
    """
    open_parked = latest_open_job_for_session(store, session_id) if store else None
    if open_parked is not None:
        st = getattr(getattr(open_parked, "status", None), "value", str(getattr(open_parked, "status", "")))
        if st == "waiting_approval":
            msg = (
                f"Job {open_parked.id} is waiting_approval on this origin session. "
                "Approve it (in Chat or Agents) to resume the same job_id — "
                "refusing to mint an orphan Job [CARD-251 / REQ-FORGE-RESUME-004]."
            )
            logger.warning("orphan_prevented session=%s job_id=%s", session_id, open_parked.id)
            store.save_message(
                session_id=session_id,
                agent_id=profile.id,
                message=ChatMessage(role=Role.USER, content=effective_content),
            )
            store.save_message(
                session_id=session_id,
                agent_id=profile.id,
                message=ChatMessage(role=Role.ASSISTANT, content=msg),
            )
            await queue.put(
                _sse(
                    "error",
                    {
                        "error": msg,
                        "job_id": open_parked.id,
                        "session_id": session_id,
                        "orphan_prevented": True,
                        "waiting_approval": True,
                        "FORGE_RESUME": True,
                    },
                )
            )
            await queue.put(_sse("turn_done", {"content": msg, "orphan_prevented": True}))
            return False

    if orch is None or not hasattr(orch, "create_job_from_catalog_resolve"):
        msg = (
            "Standing outcome ask cannot mint standing Job "
            "(job orchestrator unavailable) [CARD-236 fail-closed]."
        )
        logger.error("fail_closed_outcome_mint session=%s", session_id)
        store.save_message(
            session_id=session_id,
            agent_id=profile.id,
            message=ChatMessage(role=Role.USER, content=effective_content),
        )
        store.save_message(
            session_id=session_id,
            agent_id=profile.id,
            message=ChatMessage(role=Role.ASSISTANT, content=msg),
        )
        await queue.put(
            _sse(
                "error",
                {
                    "error": msg,
                    "fail_closed_outcome_mint": True,
                    "JOBMINT": True,
                },
            )
        )
        await queue.put(_sse("turn_done", {"content": msg}))
        return False

    user_msg = ChatMessage(role=Role.USER, content=effective_content)
    store.save_message(session_id=session_id, agent_id=profile.id, message=user_msg)
    return True


async def emit_and_execute_catalog_job(
    *,
    queue,
    store,
    kernel,
    orch,
    reflexion_engine,
    profile,
    job,
    session_id: str,
    self_verify: bool,
    approval_mode: str,
    capability_catalog: Any = None,
    wiki_root: Any = None,
    registry: Any = None,
) -> None:
    """Emit job_created, catalog_resolved, and plan_formulated SSE events, then run all job phases."""
    phases = store.list_phases_for_job(job.id)
    matched_ids = []
    ids_fn = getattr(orch, "matched_capability_ids_for_job", None)
    if callable(ids_fn):
        matched_ids = list(ids_fn(job.id) or [])
    await queue.put(
        _sse(
            "job_created",
            {
                "job_id": job.id,
                "phase_count": len(phases),
                "goal": job.goal,
                "agent_id": job.agent_id,
                "session_id": job.session_id,
                "status": job.status.value if hasattr(job.status, "value") else str(job.status),
                "template_id": getattr(job, "template_id", None),
                "matched_capability_ids": matched_ids,
                "success_rule": getattr(job, "success_rule", "") or "",
                "catalog_resolve": True,
                "outcome_intake": True,
            },
        )
    )
    skill_meta = []
    if capability_catalog is not None and matched_ids:
        from src.application.capabilities.progressive_skills import skill_metadata_view

        store_cap = getattr(capability_catalog, "_store", None)
        get_entry = getattr(store_cap, "get_entry", None) if store_cap else None
        for mid in matched_ids:
            if not str(mid).startswith("skill."):
                continue
            entry = get_entry(mid) if callable(get_entry) else None
            if entry is not None:
                skill_meta.append(skill_metadata_view(entry))
            else:
                skill_meta.append(
                    {
                        "id": mid,
                        "title": mid.split(".", 1)[-1],
                        "kind": "skill",
                        "risk": "medium",
                        "requires_hitl": False,
                        "body_loaded": False,
                        "metadata_only": True,
                    }
                )
    await queue.put(
        _sse(
            "catalog_resolved",
            {
                "job_id": job.id,
                "matched_capability_ids": matched_ids,
                "skill_metadata": skill_meta,
                "skill_bodies_omitted": True,
                "phases": [{"id": p.id, "name": p.name, "index": p.index} for p in phases],
                "standing": True,
                "template_id": getattr(job, "template_id", None),
            },
        )
    )
    await queue.put(
        _sse(
            "plan_formulated",
            {
                "plan_id": f"catalog:{job.id}",
                "goal": job.goal,
                "steps": [
                    {
                        "title": p.name,
                        "description": p.success_rule or p.name,
                    }
                    for p in phases
                ],
                "job_id": job.id,
                "standing": True,
                "catalog_resolve": True,
                "matched_capability_ids": matched_ids,
            },
        )
    )
    await execute_goal_job_phases(
        queue=queue,
        store=store,
        kernel=kernel,
        orch=orch,
        reflexion_engine=reflexion_engine,
        profile=profile,
        job=job,
        session_id=session_id,
        self_verify=self_verify,
        approval_mode=approval_mode or "ask",
        wiki_root=wiki_root,
        registry=registry,
    )
