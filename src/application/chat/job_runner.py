"""
Standing multi-phase job execution and phase helper utilities [CARD-713].
"""

from __future__ import annotations

import logging
import sys
from typing import Any, List

from src.application.chat.stream_registry import spawn_turn_side_task
from src.application.chat.turn_streamer import (
    _background_extract_turn_memory,
    _sse,
    _stream_turn_bound,
    deduplicate_phase_deliverables,
    format_json_deliverable_to_markdown,
)
from src.application.orchestration.chat_job_binding import (
    WAITING_FOR_ANSWER_NOTE,
    park_note,
    persist_plan_as_job,
)
from src.application.orchestration.job_phase_memory import prior_lines_from_job_memory
from src.application.orchestration.phase_roles import (
    format_planning_phase_block,
    format_planning_repo_note,
    is_planning_phase,
    planning_tools_block_for,
)
from src.application.orchestration.repo_code_grounding import (
    ACTION_REQUIRE_READ as REPO_ACTION_REQUIRE_READ,
)
from src.application.orchestration.repo_code_grounding import (
    apply_standing_repo_code_grounding,
    format_repo_grounding_constraint_block,
    is_repo_code_ask,
)
from src.application.orchestration.repo_code_grounding import (
    grounding_for_job as repo_grounding_for_job,
)
from src.application.orchestration.research_before_plan import (
    auto_complete_prepared_research,
    format_job_failed_honesty,
    is_research_phase,
    research_already_prepared,
)
from src.application.orchestration.wiki_thin_grounding import (
    ACTION_GROUNDED_ONLY,
    ACTION_NEED_SOURCES,
    ACTION_PROCEED_WITH_HITS,
    apply_standing_wiki_thin_grounding,
    format_grounding_constraint_block,
    format_need_sources_park_message,
    format_ungrounded_claim_honesty,
    grounding_for_job,
    is_wiki_related_ask,
    ungrounded_claimed_paths,
)
from src.application.orchestration.working_set_context import (
    build_phase_working_set,
    distill_durable_note,
    format_phase_working_set_prompt,
    resolve_matched_metadata_for_job,
)
from src.domain.gateway.models import ChatMessage, Role
from src.domain.orchestration.models import PhaseStatus
from src.domain.planning.models import ExecutionPlan, StepStatus

logger = logging.getLogger(__name__)


def _chat_override(name: str, default: Any) -> Any:
    """Resolve ``name`` from ``src.web.routers.chat`` if loaded so test monkeypatches take effect."""
    chat_mod = sys.modules.get("src.web.routers.chat")
    if chat_mod is not None and hasattr(chat_mod, name):
        return getattr(chat_mod, name)
    return default


def _plan_step_payload(plan: ExecutionPlan) -> list:
    return [{"title": s.title, "description": s.description} for s in plan.steps]


def profile_for_phase(profile, phase, registry):
    """CARD-544: run a phase as its assigned agent (e.g. a code Execute phase on Developer).

    Falls back to the chat's profile when the phase has no assignment, the agent is unknown, or no registry is given.
    """
    assigned = str(getattr(phase, "assigned_agent_id", "") or "").strip()
    if not assigned or registry is None or assigned == getattr(profile, "id", None):
        return profile
    getter = getattr(registry, "get_profile", None)
    try:
        other = getter(assigned) if callable(getter) else None
    except Exception:
        other = None
    return other or profile


def _ensure_phase_session(store, session_id: str, phase, agent_id: str) -> str:
    phase_session = f"{session_id}::phase::{phase.id}"
    if store.get_session(phase_session) is None:
        store.create_session(agent_id=agent_id, title=phase.name or "Phase", session_id=phase_session)
    return phase_session


def resume_session_for_phase(store, parent_session_id: str, phase) -> str:
    """Session an approved/parked phase resumes in [CARD-548, CARD-554]."""
    phase_session = f"{parent_session_id}::phase::{phase.id}"
    try:
        if store.get_session(phase_session) is not None:
            return phase_session
    except Exception:
        logger.exception("resume_session_for_phase lookup failed for %s", phase_session)
    return parent_session_id


def relay_phase_reply_to_parent(store, parent_session_id: str, phase_session_id: str, agent_id: str) -> str:
    """Copy the resumed phase's last assistant reply into the chat the operator sees [CARD-548]."""
    if not phase_session_id or phase_session_id == parent_session_id:
        return ""
    text = ""
    for pm in reversed(store.get_messages(phase_session_id) or []):
        if getattr(pm, "role", None) == Role.ASSISTANT and pm.content:
            text = str(pm.content)
            break
    if text:
        store.save_message(
            session_id=parent_session_id,
            agent_id=agent_id,
            message=ChatMessage(role=Role.ASSISTANT, content=text),
        )
    return text


def is_plan_awaiting_operator_choice(text: str | None) -> bool:
    """Detect if Formulate output explicitly requests operator choice / route selection [CARD-378, REQ-ORCH-045]."""
    if not text:
        return False
    t = text.lower()
    has_options = ("option a" in t and "option b" in t) or ("route a" in t and "route b" in t)
    has_choice = any(
        k in t
        for k in (
            "pick a route",
            "choose a route",
            "which option",
            "what i need from you to build it",
            "which route",
        )
    )
    return has_options or has_choice


async def execute_goal_job_phases(
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
    data_dir=None,
    wiki_root=None,
    registry=None,
) -> None:
    """Run each persisted phase via its own stream_turn after plan review [REQ-ORCH-039]."""
    phases = store.list_phases_for_job(job.id)
    data_dir = data_dir if data_dir is not None else getattr(orch, "_data_dir", None)
    accumulated: List[str] = list(
        prior_lines_from_job_memory(
            agent_id=getattr(profile, "id", None) or job.agent_id,
            job_id=job.id,
            data_dir=data_dir,
        )
    )
    if accumulated:
        await queue.put(
            _sse(
                "memory_recalled",
                {
                    "job_id": job.id,
                    "agent_id": getattr(profile, "id", None) or job.agent_id,
                    "count": len(accumulated),
                    "facts": accumulated[:20],
                    "source": "agent_memory.db",
                },
            )
        )
    last_content = ""
    durable_notes: List[str] = []
    matched_metadata = resolve_matched_metadata_for_job(orch, job.id)
    provenanced_wiki_paths: List[str] = []
    provenanced_repo_paths: List[str] = []
    wiki_decision = None
    repo_decision = None
    if is_wiki_related_ask(getattr(job, "goal", None) or ""):
        try:
            wiki_decision = apply_standing_wiki_thin_grounding(
                orch,
                job,
                wiki_root=wiki_root,
                intent=getattr(job, "goal", None) or "",
                park=True,
            )
            await queue.put(_sse("wiki_grounding", wiki_decision.as_dict()))
            if wiki_decision.action == ACTION_NEED_SOURCES:
                msg = format_need_sources_park_message(
                    wiki_decision, job_id=getattr(job, "id", None)
                )
                try:
                    store.save_message(
                        session_id=session_id,
                        agent_id=getattr(profile, "id", None) or job.agent_id,
                        message=ChatMessage(role=Role.ASSISTANT, content=msg),
                    )
                except Exception:
                    pass
                await queue.put(
                    _sse(
                        "phase_complete",
                        {
                            "job_id": job.id,
                            "phase_id": None,
                            "status": "waiting_approval",
                            "react_state": "PARKED",
                            "need_sources": True,
                            "wiki_thin_grounding": True,
                        },
                    )
                )
                await queue.put(_sse("token", {"text": msg}))
                await queue.put(
                    _sse(
                        "turn_done",
                        {
                            "content": msg,
                            "need_sources": True,
                            "waiting_approval": True,
                            "job_id": job.id,
                        },
                    )
                )
                return
        except Exception:
            logger.exception("CARD-260 wiki thin grounding soft-fail job=%s", getattr(job, "id", None))
            wiki_decision = None
    repo_ask_fn = _chat_override("is_repo_code_ask", is_repo_code_ask)
    apply_repo_grounding_fn = _chat_override(
        "apply_standing_repo_code_grounding", apply_standing_repo_code_grounding
    )
    if repo_ask_fn(getattr(job, "goal", None) or ""):
        try:
            repo_decision = apply_repo_grounding_fn(
                orch,
                job,
                intent=getattr(job, "goal", None) or "",
            )
            await queue.put(_sse("repo_grounding", repo_decision.as_dict()))
        except Exception:
            logger.exception("CARD-262 repo code grounding soft-fail job=%s", getattr(job, "id", None))
            repo_decision = None
    completed_deliverables: List[str] = []

    for phase in phases:
        current = store.get_phase(phase.id)
        if current.status in {PhaseStatus.DONE, PhaseStatus.FAILED, PhaseStatus.CANCELLED}:
            continue
        if current.status in {PhaseStatus.QUEUED, PhaseStatus.WAITING_APPROVAL}:
            current = orch.start_phase(current.id)
        if is_research_phase(current) and research_already_prepared(orch, job.id):
            auto_complete_prepared_research(orch, current, job)
            refreshed = store.get_phase(current.id)
            durable_notes.append(
                distill_durable_note(
                    phase_name=current.name,
                    phase_index=current.index,
                    raw_output=refreshed.output_packet_json or "",
                )
            )
            last_content = refreshed.output_packet_json or last_content
            await queue.put(
                _sse(
                    "phase_complete",
                    {
                        "job_id": job.id,
                        "phase_id": current.id,
                        "status": "done",
                        "react_state": "DONE",
                        "research_auto_completed": True,
                    },
                )
            )
            continue
        bound_skill_id = None
        bound_skill_body = None
        bind_fn = getattr(orch, "bind_matched_skill_on_phase_start", None)
        if callable(bind_fn):
            for bound in bind_fn(current.id) or []:
                await queue.put(
                    _sse(
                        "skill_bound",
                        {
                            "job_id": job.id,
                            "phase_id": current.id,
                            "phase_name": current.name,
                            "skill_id": bound.get("skill_id"),
                            "runbook_id": bound.get("runbook_id"),
                            "title": bound.get("title"),
                            "body_loaded": bool(bound.get("body_loaded")),
                            "success": bool(bound.get("success")),
                            "body_chars": len(bound.get("body") or "") if bound.get("success") else 0,
                            "progressive": True,
                        },
                    )
                )
                if bound.get("success") and bound.get("body"):
                    bound_skill_id = bound.get("skill_id")
                    bound_skill_body = bound.get("body")
        memory_facts = list(
            prior_lines_from_job_memory(
                agent_id=getattr(profile, "id", None) or job.agent_id,
                job_id=job.id,
                data_dir=data_dir,
            )
        )
        ws = build_phase_working_set(
            job=job,
            phase=current,
            phase_count=len(phases),
            matched_metadata=matched_metadata,
            bound_skill_id=bound_skill_id,
            bound_skill_body=bound_skill_body,
            prior_phase_notes=durable_notes,
            all_memory_facts=memory_facts,
        )
        assignment = format_phase_working_set_prompt(ws)
        if wiki_decision is None:
            wiki_decision = grounding_for_job(orch, job.id)
        if wiki_decision is not None and wiki_decision.action in {
            ACTION_GROUNDED_ONLY,
            ACTION_PROCEED_WITH_HITS,
        }:
            assignment = (
                assignment.rstrip()
                + "\n\n"
                + format_grounding_constraint_block(wiki_decision)
            )
        if repo_decision is None:
            repo_decision = repo_grounding_for_job(orch, job.id)
        planning = is_planning_phase(current)
        if repo_decision is not None and repo_decision.action == REPO_ACTION_REQUIRE_READ:
            block = (
                format_planning_repo_note(getattr(repo_decision, "suggested_paths", ()) or ())
                if planning
                else format_repo_grounding_constraint_block(repo_decision)
            )
            assignment = assignment.rstrip() + "\n\n" + block
        if planning and len(phases) > 1:
            assignment = assignment.rstrip() + "\n\n" + format_planning_phase_block(phases, current)
        run_profile = profile_for_phase(profile, current, registry)
        if planning:
            try:
                ids_fn = getattr(orch, "matched_capability_ids_for_job", None)
                matched_now = list(ids_fn(job.id) or []) if callable(ids_fn) else []
                tools_block = planning_tools_block_for(kernel, run_profile, job.id, current.id, matched_now)
                assignment = assignment.rstrip() + "\n\n" + tools_block
            except Exception:
                logger.exception("CARD-665 planning tools block soft-fail job=%s", getattr(job, "id", None))
        phase_session = _ensure_phase_session(store, session_id, current, run_profile.id)
        stream_bound_fn = _chat_override("_stream_turn_bound", _stream_turn_bound)
        outcome = await stream_bound_fn(
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
            phase=current,
            self_verify=self_verify,
            step_index=current.index,
            emit_step_events=True,
            provenanced_wiki_paths=provenanced_wiki_paths,
            provenanced_repo_paths=provenanced_repo_paths,
        )

        phase_text = ""
        phase_msgs = store.get_messages(phase_session)
        for pm in reversed(phase_msgs):
            if getattr(pm, "role", None) == Role.ASSISTANT and pm.content:
                phase_text = pm.content
                break

        if outcome == "question":
            asked = "\n\n---\n\n".join(
                [*completed_deliverables, phase_text, WAITING_FOR_ANSWER_NOTE]
                if phase_text
                else [*completed_deliverables, WAITING_FOR_ANSWER_NOTE]
            )
            store.save_message(
                session_id=session_id,
                agent_id=getattr(profile, "id", None) or job.agent_id,
                message=ChatMessage(role=Role.ASSISTANT, content=asked),
            )
            await queue.put(_sse("token", {"text": f"\n\n{WAITING_FOR_ANSWER_NOTE}\n"}))
            await queue.put(_sse("turn_done", {"content": asked, "waiting_answer": True, "job_id": job.id}))
            return
        if outcome == "parked":
            park_msg = park_note(job.id, getattr(current, "name", "current phase"))
            composite_park = (
                "\n\n---\n\n".join(completed_deliverables) + f"\n\n---\n\n{park_msg}"
                if completed_deliverables
                else park_msg
            )
            try:
                store.save_message(
                    session_id=session_id,
                    agent_id=getattr(profile, "id", None) or job.agent_id,
                    message=ChatMessage(role=Role.ASSISTANT, content=composite_park),
                )
            except Exception:
                pass
            await queue.put(_sse("token", {"text": f"\n\n{park_msg}\n"}))
            await queue.put(
                _sse(
                    "turn_done",
                    {
                        "content": composite_park,
                        "waiting_approval": True,
                        "job_id": job.id,
                        "phase_id": current.id,
                    },
                )
            )
            return
        if outcome != "done":
            fail_reason = ""
            try:
                failed_phase = store.get_phase(current.id)
                pkt = failed_phase.output_packet_json or ""
                if "phase_llm_timeout" in pkt:
                    fail_reason = "phase_llm_timeout"
                elif pkt:
                    fail_reason = "phase failed"
            except Exception:
                fail_reason = "phase failed"
            msg = format_job_failed_honesty(
                job_id=job.id,
                phase_name=getattr(current, "name", None),
                reason=fail_reason or str(outcome),
            )
            if completed_deliverables:
                composite_msg = (
                    "\n\n---\n\n".join(completed_deliverables)
                    + f"\n\n---\n\n⚠️ **Phase Status**: {msg}"
                )
            else:
                composite_msg = msg
            try:
                store.save_message(
                    session_id=session_id,
                    agent_id=getattr(profile, "id", None) or job.agent_id,
                    message=ChatMessage(role=Role.ASSISTANT, content=composite_msg),
                )
            except Exception:
                pass
            await queue.put(_sse("token", {"text": msg}))
            await queue.put(_sse("turn_done", {"content": composite_msg, "job_failed": True}))
            return

        if phase_text:
            completed_deliverables.append(phase_text)

        if current.index == 0 and len(phases) > 1 and is_plan_awaiting_operator_choice(phase_text):
            park_fn = getattr(orch, "park_phase", None)
            if callable(park_fn):
                park_fn(current.id)
            park_msg = (
                f"{phase_text}\n\n---\n\n"
                f"Job {job.id} is waiting for operator approval / selection. "
                "Approve or reply with your preferred option to continue execution."
            )
            try:
                store.save_message(
                    session_id=session_id,
                    agent_id=getattr(profile, "id", None) or job.agent_id,
                    message=ChatMessage(role=Role.ASSISTANT, content=park_msg),
                )
            except Exception:
                pass
            await queue.put(
                _sse(
                    "turn_done",
                    {
                        "content": park_msg,
                        "waiting_approval": True,
                        "job_id": job.id,
                        "phase_id": current.id,
                    },
                )
            )
            return

        refreshed = store.get_phase(current.id)
        packet_text = refreshed.output_packet_json or ""
        durable_notes.append(
            distill_durable_note(
                phase_name=current.name,
                phase_index=current.index,
                raw_output=packet_text,
            )
        )
        last_content = packet_text

    final_content = format_json_deliverable_to_markdown(last_content) if last_content else ""
    final_content = deduplicate_phase_deliverables(completed_deliverables, final_content)
    if final_content and is_wiki_related_ask(getattr(job, "goal", None) or ""):
        allowed_paths = list(provenanced_wiki_paths)
        if wiki_decision is not None:
            allowed_paths.extend(list(wiki_decision.hit_paths or ()))
            allowed_paths.extend(list(wiki_decision.matched_read_paths or ()))
        bad = ungrounded_claimed_paths(final_content, allowed_paths)
        if bad:
            final_content = format_ungrounded_claim_honesty(
                bad,
                provenanced_wiki_paths,
                job_id=getattr(job, "id", None),
            )
            await queue.put(
                _sse(
                    "wiki_ungrounded_claim",
                    {
                        "job_id": job.id,
                        "ungrounded": bad,
                        "provenanced": list(provenanced_wiki_paths),
                    },
                )
            )
    if final_content:
        store.save_message(
            session_id=session_id,
            agent_id=profile.id,
            message=ChatMessage(role=Role.ASSISTANT, content=final_content),
        )
        await queue.put(_sse("token", {"text": final_content}))
        await queue.put(_sse("turn_done", {"content": final_content}))
        if getattr(profile, "memory_enabled", True) and getattr(job, "goal", None):
            llm_service = (
                getattr(kernel, "gateway", None)
                or getattr(kernel, "llm_service", None)
            )
            extract_fn = _chat_override("_background_extract_turn_memory", _background_extract_turn_memory)
            spawn_turn_side_task(
                session_id,
                extract_fn(
                    agent_id=profile.id,
                    user_text=job.goal,
                    assistant_text=final_content,
                    session_id=session_id,
                    llm_service=llm_service,
                    data_dir=data_dir or getattr(kernel, "data_dir", None),
                ),
            )
    elif not last_content:
        await queue.put(_sse("turn_done", {"content": ""}))


async def execute_goal_plan_steps(
    *,
    queue,
    store,
    kernel,
    reflexion_engine,
    profile,
    plan: ExecutionPlan,
    session_id: str,
    self_verify: bool,
    approval_mode: str,
    orch=None,
    job=None,
) -> None:
    """DTO adapter: persist if needed, then stream_turn each phase."""
    if orch is not None and job is None:
        job = persist_plan_as_job(orch, plan, verify_checker=None)
    if orch is not None and job is not None:
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
            approval_mode=approval_mode,
            wiki_root=None,
        )
        return
    accumulated_context: List[str] = []
    for i, step in enumerate(plan.steps):
        step.status = StepStatus.IN_PROGRESS
        await queue.put(
            _sse("step_start", {"step_index": i, "title": step.title, "description": step.description})
        )
        step_prompt = (
            f"You are executing Step {i + 1}/{len(plan.steps)} of the goal: '{plan.goal}'.\n"
            f"STEP: {step.title} - {step.description}\n"
            f"PRIOR CONTEXT:\n" + "\n".join(accumulated_context)
        )
        reply = await kernel.run_turn(
            agent=profile,
            session_id=session_id,
            user_content=step_prompt,
            save_to_history=False,
            approval_mode=approval_mode or "ask",
        )
        step.status = StepStatus.COMPLETED
        step.result_summary = reply.content
        accumulated_context.append(f"Step {i + 1} ({step.title}): {reply.content}")
        await queue.put(_sse("step_complete", {"step_index": i, "status": "completed"}))
    synth_prompt = (
        f"Synthesize the final deliverable for the goal: '{plan.goal}' based on completed steps:\n"
        + "\n".join(accumulated_context)
    )
    final_reply = await kernel.run_turn(
        agent=profile,
        session_id=session_id,
        user_content=synth_prompt,
        save_to_history=False,
        approval_mode=approval_mode or "ask",
    )
    final_content = format_json_deliverable_to_markdown(final_reply.content)
    store.save_message(
        session_id=session_id,
        agent_id=profile.id,
        message=ChatMessage(role=Role.ASSISTANT, content=final_content),
    )
    await queue.put(_sse("token", {"text": final_content}))
    await queue.put(_sse("turn_done", {"content": final_content}))
