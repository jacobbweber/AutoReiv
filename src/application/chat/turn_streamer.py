"""
Chat turn streaming, phase-bound ReAct turn execution, verification gating, and deliverable formatting [CARD-713].
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.application.chat.attachments import (
    deduplicate_phase_deliverables,
    format_json_deliverable_to_markdown,
    format_prompt_with_attachments,
)
from src.application.orchestration.chat_job_binding import (
    output_packet_for_phase,
    verify_skip_fact,
)
from src.application.orchestration.external_verifier_policy import (
    apply_phase_complete_verify_gate,
)
from src.application.orchestration.repo_code_grounding import (
    collect_provenanced_repo_paths_from_tool_result,
)
from src.application.orchestration.research_before_plan import (
    format_job_failed_honesty,
)
from src.application.orchestration.standing_job_graph import (
    format_phase_llm_exhausted_reason,
    is_phase_llm_retryable,
    resolve_standing_phase_llm_retries,
    resolve_standing_phase_llm_timeout,
)
from src.application.orchestration.wiki_thin_grounding import (
    collect_provenanced_paths_from_tool_result,
)
from src.domain.kernel.models import KernelEventType
from src.domain.orchestration.errors import InvalidPhaseTransitionError
from src.infrastructure.serialization.json_safe import dumps_jsonable

logger = logging.getLogger(__name__)


def _sse(event: str, payload: Any) -> str:
    return f"event: {event}\ndata: {dumps_jsonable(payload)}\n\n"


async def _background_extract_turn_memory(
    agent_id: str,
    user_text: str,
    assistant_text: str,
    session_id: str,
    llm_service: Any,
    data_dir: Optional[Union[str, Path]] = None,
) -> None:
    """Asynchronously compile durable facts and milestones into agent's cognitive brain [CARD-116, CARD-405]."""
    try:
        from src.application.memory.extractor import MemoryExtractorService, should_skip_extraction
        from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

        if should_skip_extraction(user_text):
            return
        if not llm_service:
            return

        repo = AgentMemoryRepository(agent_id=agent_id, data_dir=data_dir)
        repo.initialize_schema()
        extractor = MemoryExtractorService(repository=repo, llm_service=llm_service)
        results = await extractor.process_turn(user_text=user_text, assistant_text=assistant_text)
        if results:
            logger.info("Cognitive memory extracted for agent '%s': %s facts applied", agent_id, len(results))
    except Exception as exc:
        logger.warning("Background turn memory extraction failed for agent '%s': %s", agent_id, exc)


def maybe_update_first_turn_title(store: Any, session_id: str, content: Optional[str]) -> None:
    """Auto-generate 2-5 word session title on first turn [CARD-150, REQ-CHAT-002]."""
    if not content or not store or not hasattr(store, "get_session") or not hasattr(store, "update_session_title"):
        return
    from src.domain.gateway.models import Role
    from src.infrastructure.memory.repositories.sessions import generate_session_title_from_prompt

    sess = store.get_session(session_id)
    if sess and (sess.title in ("New Conversation", "New Chat", "Agent Chat") or sess.title.endswith(" Chat")):
        messages = store.get_messages(session_id)
        user_msgs = [m for m in messages if getattr(m, "role", None) == Role.USER]
        if len(user_msgs) <= 1:
            new_title = generate_session_title_from_prompt(content)
            if new_title:
                store.update_session_title(session_id, new_title)


async def finalize_plain_turn_verification_and_memory(
    *,
    queue,
    profile,
    session_id: str,
    effective_content: str,
    last_plain: str,
    self_verify: bool,
    verify_checker: Optional[str],
    reflexion_engine: Any,
    llm_service: Any,
    data_dir: Any,
    spawn_side_task_fn: Any,
    extract_memory_fn: Any,
) -> None:
    """Run optional plain-turn named checker verification and schedule background memory extraction."""
    if self_verify:
        checker = (verify_checker or "").strip()
        payload: Dict[str, Any] = {"passed": False, "status": "skipped_no_checker"}
        if checker and reflexion_engine is not None:
            result = await reflexion_engine.run_named_checker(
                agent=profile,
                last_output=last_plain,
                verifier_tool_name=checker,
                verifier_args=None,
            )
            payload = {
                "passed": bool(result.get("verification_passed")),
                "status": result.get("status") or "failed",
                "checker": checker,
                "discrepancies": result.get("discrepancies") or [],
            }
            await queue.put(_sse("reflexion_attempt", {"attempt": 1, "max_attempts": 1, "checker": checker}))
            if not payload["passed"]:
                await queue.put(
                    _sse(
                        "reflexion_critique",
                        {
                            "attempt": 1,
                            "critique": "; ".join(payload.get("discrepancies") or []) or "verification failed",
                        },
                    )
                )
        else:
            payload["facts"] = [verify_skip_fact()]
        await queue.put(_sse("reflexion_verified", payload))

    if getattr(profile, "memory_enabled", True) and effective_content and last_plain:
        spawn_side_task_fn(
            session_id,
            extract_memory_fn(
                agent_id=profile.id,
                user_text=effective_content,
                assistant_text=last_plain,
                session_id=session_id,
                llm_service=llm_service,
                data_dir=data_dir,
            ),
        )


__all__ = [
    "PHASE_COMPLETE_REFUSED_REASON",
    "_apply_verify_gate",
    "_background_extract_turn_memory",
    "_forward_kernel_event",
    "_phase_run_token",
    "_plain_question_waits",
    "_sse",
    "_stream_turn_bound",
    "complete_phase_or_fail",
    "deduplicate_phase_deliverables",
    "finalize_plain_turn_verification_and_memory",
    "format_json_deliverable_to_markdown",
    "format_prompt_with_attachments",
    "maybe_update_first_turn_title",
    "tool_output_payload",
]


def tool_output_payload(event) -> dict:
    """CARD-682: a refused or failed call says so and why, instead of an empty result."""
    res = event.tool_result
    call_info = event.tool_call if isinstance(event.tool_call, dict) else {}
    name = call_info.get("name") or (getattr(res, "tool_name", "") if res is not None else "") or ""
    if res is None:
        return {"type": "tool_output", "tool_name": name, "success": True, "result": ""}
    if res.success:
        return {"type": "tool_output", "tool_name": name, "success": True, "result": res.output}
    error = str(res.error or "Tool execution error")
    return {
        "type": "tool_output",
        "tool_name": name,
        "success": False,
        "error": error,
        "result": f"Tool Error: {error}",
    }


async def _forward_kernel_event(queue, event, profile) -> None:
    if event.event_type == KernelEventType.TOKEN:
        if event.reasoning_content:
            await queue.put(_sse("reasoning", {"type": "reasoning", "text": event.reasoning_content}))
        if event.content:
            await queue.put(_sse("token", {"type": "token", "text": event.content}))
    elif event.event_type == KernelEventType.TOOL_START:
        call_info = event.tool_call or {}
        await queue.put(
            _sse(
                "tool_start",
                {
                    "type": "tool_start",
                    "tool_name": call_info.get("name", ""),
                    "arguments": call_info.get("arguments", {}),
                },
            )
        )
    elif event.event_type == KernelEventType.TOOL_END:
        await queue.put(_sse("tool_output", tool_output_payload(event)))
    elif event.event_type == KernelEventType.HANDOFF_START:
        await queue.put(_sse("handoff_start", {"type": "handoff_start", **(event.handoff or {})}))
    elif event.event_type == KernelEventType.HANDOFF_COMPLETE:
        await queue.put(_sse("handoff_complete", {"type": "handoff_complete", **(event.handoff or {})}))
    elif event.event_type == KernelEventType.APPROVAL_REQUIRED:
        await queue.put(
            _sse(
                "approval_required",
                {
                    "type": "approval_required",
                    "approval_id": event.approval_id,
                    "tool_name": (event.tool_call or {}).get("name", ""),
                    "arguments": (event.tool_call or {}).get("arguments", {}),
                    "message": event.content,
                },
            )
        )
    elif event.event_type == KernelEventType.TURN_END:
        await queue.put(_sse("turn_done", {"content": event.content}))
    elif event.event_type == KernelEventType.REACT_STATE:
        payload = dict(event.react or {})
        if not payload.get("assigned_agent_id"):
            payload["assigned_agent_id"] = profile.id
        await queue.put(_sse("react_state", payload))
    elif event.event_type == KernelEventType.NOTICE:
        # CARD-475: e.g. attachment_notice when a text-only model got an image.
        payload = dict(event.notice or {})
        await queue.put(_sse(payload.get("type") or "notice", {"message": event.content, **payload}))
    elif event.event_type == KernelEventType.ERROR:
        await queue.put(_sse("error", {"error": event.content}))


async def _apply_verify_gate(
    *,
    queue,
    reflexion_engine,
    profile,
    phase,
    last_output: str,
    self_verify: bool,
    step_index: Optional[int] = None,
) -> Dict[str, Any]:
    """Named checker gate. Missing checker is an honest skip [REQ-ORCH-041]."""
    if not self_verify:
        return {"status": "not_requested", "verification_passed": False, "skipped": True, "facts": []}
    checker = (getattr(phase, "verify_checker", None) or "").strip()
    payload: Dict[str, Any] = {"phase_id": phase.id}
    if step_index is not None:
        payload["step_index"] = step_index
    if not checker or reflexion_engine is None:
        payload.update({"passed": False, "status": "skipped_no_checker"})
        await queue.put(_sse("reflexion_verified", payload))
        return {
            "status": "skipped_no_checker",
            "verification_passed": False,
            "skipped": True,
            "facts": [verify_skip_fact()],
        }
    # Emit attempt event to surface critic inspection in real time [CARD-179, REQ-REF-002]
    attempt_payload = dict(payload)
    attempt_payload.update({"attempt": 1, "max_attempts": 1, "checker": checker})
    await queue.put(_sse("reflexion_attempt", attempt_payload))

    result = await reflexion_engine.run_named_checker(
        agent=profile,
        last_output=last_output,
        verifier_tool_name=checker,
    )
    passed = bool(result.get("verification_passed"))
    discrepancies = result.get("discrepancies") or []

    # If verification failed or returned discrepancies, emit critique event [CARD-179, REQ-REF-002]
    if not passed and discrepancies:
        critique_payload = dict(payload)
        critique_payload.update(
            {
                "attempt": 1,
                "checker": checker,
                "critique": f"Checker '{checker}' found: {'; '.join(str(d) for d in discrepancies)}",
                "discrepancies": discrepancies,
            }
        )
        await queue.put(_sse("reflexion_critique", critique_payload))

    payload.update(
        {
            "passed": passed,
            "status": result.get("status"),
            "discrepancies": discrepancies,
            "checker": checker,
        }
    )
    await queue.put(_sse("reflexion_verified", payload))
    return {
        "status": result.get("status"),
        "verification_passed": passed,
        "skipped": False,
        "facts": [f"verify_checker: {checker}"],
        "discrepancies": discrepancies,
    }


def _phase_run_token(orch, phase_id: str):
    fn = getattr(orch, "phase_run_token", None)
    try:
        return fn(phase_id) if callable(fn) else None
    except Exception:  # noqa: BLE001
        return None


PHASE_COMPLETE_REFUSED_REASON = (
    "Another run of this job changed this step while it was finishing, so it could not be recorded. "
    "The job was stopped so it does not hang; send the request again to re-run it."
)


async def complete_phase_or_fail(*, orch, queue, job, phase, output_packet) -> bool:
    """Complete ``phase``; if the state machine refuses, fail phase and job honestly [CARD-530 REQ-530-005]."""
    try:
        orch.complete_phase(phase.id, output_packet)
        return True
    except InvalidPhaseTransitionError as exc:
        logger.warning("complete_phase refused job=%s phase=%s: %s [CARD-530]", job.id, phase.id, exc)
        orch.fail_phase(phase.id, PHASE_COMPLETE_REFUSED_REASON)
        await queue.put(
            _sse(
                "phase_complete",
                {
                    "job_id": job.id,
                    "phase_id": phase.id,
                    "status": "failed",
                    "react_state": "FAILED",
                    "reason": PHASE_COMPLETE_REFUSED_REASON,
                },
            )
        )
        honesty = format_job_failed_honesty(
            job_id=job.id,
            phase_name=getattr(phase, "name", None),
            reason=PHASE_COMPLETE_REFUSED_REASON,
        )
        await queue.put(_sse("token", {"text": honesty}))
        await queue.put(
            _sse("turn_done", {"content": honesty, "job_failed": True, "reason": PHASE_COMPLETE_REFUSED_REASON})
        )
        return False


async def _plain_question_waits(kernel, profile, job, reply: str) -> bool:
    """CARD-616: same model, no tools, only for a final reply whose last line ends with '?'."""
    from src.application.orchestration.plain_question import ends_with_question, reply_needs_answer

    if not ends_with_question(reply):
        return False
    gateway = getattr(kernel, "gateway", None)
    resolve = getattr(kernel, "_resolve_model", None)
    try:
        model = resolve(profile) if callable(resolve) else None
    except Exception:  # noqa: BLE001
        model = None
    return await reply_needs_answer(
        gateway, model if isinstance(model, str) else None, reply, getattr(job, "goal", "") or ""
    )


async def _stream_turn_bound(
    *,
    queue,
    kernel,
    orch,
    store,
    reflexion_engine,
    profile,
    session_id: str,
    user_content: Optional[str],
    approval_mode: str,
    resume: bool,
    job,
    phase,
    self_verify: bool,
    step_index: Optional[int] = None,
    emit_step_events: bool = False,
    provenanced_wiki_paths: Optional[List[str]] = None,
    provenanced_repo_paths: Optional[List[str]] = None,
) -> str:
    """
    stream_turn one phase, then complete/fail/park.
    Returns done|parked|failed.
    """
    run_token = _phase_run_token(orch, phase.id)  # CARD-530 D3
    await queue.put(
        _sse(
            "phase_start",
            {
                "job_id": job.id,
                "phase_id": phase.id,
                "phase_name": phase.name,
                "index": phase.index,
                "assigned_agent_id": phase.assigned_agent_id or profile.id,
            },
        )
    )
    if emit_step_events:
        await queue.put(
            _sse(
                "step_start",
                {
                    "step_index": phase.index if step_index is None else step_index,
                    "title": phase.name,
                    "description": phase.success_rule,
                    "phase_id": phase.id,
                    "job_id": job.id,
                },
            )
        )

    outcome = "done"
    last_content = ""
    error_text = ""
    timeout_s = resolve_standing_phase_llm_timeout()
    retries = resolve_standing_phase_llm_retries()
    attempts = 1 + max(0, retries)
    last_fail_kind = "timeout"
    last_fail_detail = ""

    async def _consume_stream() -> None:
        nonlocal outcome, last_content, error_text
        async for event in kernel.stream_turn(
            profile,
            session_id,
            user_content,
            approval_mode=approval_mode or "ask",
            resume=resume,
            job_id=job.id,
            phase_id=phase.id,
        ):
            await _forward_kernel_event(queue, event, profile)
            if event.event_type == KernelEventType.TOOL_END:
                call_info = event.tool_call or {}
                tool_name = call_info.get("name", "") if isinstance(call_info, dict) else ""
                if not tool_name and event.tool_result is not None:
                    tool_name = getattr(event.tool_result, "tool_name", "") or ""
                out_text = event.tool_result.output if event.tool_result else ""
                if provenanced_wiki_paths is not None:
                    for p in collect_provenanced_paths_from_tool_result(tool_name, out_text):
                        if p not in provenanced_wiki_paths:
                            provenanced_wiki_paths.append(p)
                if provenanced_repo_paths is not None:
                    for p in collect_provenanced_repo_paths_from_tool_result(tool_name, out_text):
                        if p not in provenanced_repo_paths:
                            provenanced_repo_paths.append(p)
            if event.event_type == KernelEventType.REACT_STATE:
                state = (event.react or {}).get("react_state")
                if state == "PARKED":
                    outcome = "parked"
                elif state == "FAILED":
                    outcome = "failed"
            elif event.event_type == KernelEventType.APPROVAL_REQUIRED:
                outcome = "parked"
            elif event.event_type == KernelEventType.ERROR:
                outcome = "failed"
                error_text = event.content or "stream error"
            elif event.event_type == KernelEventType.TURN_END:
                last_content = event.content or last_content
                if (event.react or {}).get("clarification") and outcome == "done":
                    outcome = "question"  # CARD-613

    # CARD-258: longer budget + 1-2 retries on timeout / connection stall.
    for attempt in range(1, attempts + 1):
        outcome = "done"
        last_content = ""
        error_text = ""
        try:
            await asyncio.wait_for(_consume_stream(), timeout=timeout_s)
            break
        except asyncio.CancelledError:
            # CARD-259: operator kill / worker cancel is a checkpoint, not fail_phase.
            # Abort already stops this worker; leave the same job_id resumable.
            # CARD-530: pass this run's token so a newer run's phase is never re-queued.
            ck = getattr(orch, "checkpoint_mid_llm_kill_phase", None)
            if callable(ck):
                try:
                    ck(phase.id, run_token=run_token)
                except TypeError:
                    ck(phase.id)
            raise
        except asyncio.TimeoutError:
            last_fail_kind = "timeout"
            last_fail_detail = f"phase_llm_timeout after {timeout_s}s"
            if attempt < attempts:
                await queue.put(
                    _sse(
                        "phase_llm_retry",
                        {
                            "job_id": job.id,
                            "phase_id": phase.id,
                            "phase_name": getattr(phase, "name", None),
                            "attempt": attempt,
                            "attempts": attempts,
                            "reason": "timeout",
                            "timeout_s": timeout_s,
                        },
                    )
                )
                continue
            timeout_reason = format_phase_llm_exhausted_reason(
                kind="timeout",
                timeout_s=timeout_s,
                attempt=attempt,
                attempts=attempts,
            )
            orch.fail_phase(phase.id, timeout_reason)
            await queue.put(
                _sse(
                    "phase_complete",
                    {
                        "job_id": job.id,
                        "phase_id": phase.id,
                        "status": "failed",
                        "react_state": "FAILED",
                    },
                )
            )
            honesty = format_job_failed_honesty(
                job_id=job.id,
                phase_name=getattr(phase, "name", None),
                reason=timeout_reason,
            )
            await queue.put(_sse("token", {"text": honesty}))
            await queue.put(_sse("turn_done", {"content": honesty, "job_failed": True}))
            return "failed"
        except Exception as exc:  # noqa: BLE001
            if is_phase_llm_retryable(exc) and attempt < attempts:
                last_fail_kind = "connection_stall"
                last_fail_detail = str(exc)
                await queue.put(
                    _sse(
                        "phase_llm_retry",
                        {
                            "job_id": job.id,
                            "phase_id": phase.id,
                            "phase_name": getattr(phase, "name", None),
                            "attempt": attempt,
                            "attempts": attempts,
                            "reason": "connection_stall",
                            "detail": str(exc)[:240],
                        },
                    )
                )
                continue
            if is_phase_llm_retryable(exc):
                stall_reason = format_phase_llm_exhausted_reason(
                    kind="connection_stall",
                    timeout_s=timeout_s,
                    attempt=attempt,
                    attempts=attempts,
                    detail=str(exc)[:200],
                )
                orch.fail_phase(phase.id, stall_reason)
                await queue.put(
                    _sse(
                        "phase_complete",
                        {
                            "job_id": job.id,
                            "phase_id": phase.id,
                            "status": "failed",
                            "react_state": "FAILED",
                        },
                    )
                )
                honesty = format_job_failed_honesty(
                    job_id=job.id,
                    phase_name=getattr(phase, "name", None),
                    reason=stall_reason,
                )
                await queue.put(_sse("token", {"text": honesty}))
                await queue.put(_sse("turn_done", {"content": honesty, "job_failed": True}))
                return "failed"
            orch.fail_phase(phase.id, f"phase_llm_error: {exc}")
            await queue.put(
                _sse(
                    "phase_complete",
                    {
                        "job_id": job.id,
                        "phase_id": phase.id,
                        "status": "failed",
                        "react_state": "FAILED",
                    },
                )
            )
            return "failed"
    else:
        timeout_reason = format_phase_llm_exhausted_reason(
            kind=last_fail_kind,
            timeout_s=timeout_s,
            attempt=attempts,
            attempts=attempts,
            detail=last_fail_detail,
        )
        orch.fail_phase(phase.id, timeout_reason)
        honesty = format_job_failed_honesty(
            job_id=job.id,
            phase_name=getattr(phase, "name", None),
            reason=timeout_reason,
        )
        await queue.put(_sse("token", {"text": honesty}))
        await queue.put(_sse("turn_done", {"content": honesty, "job_failed": True}))
        return "failed"

    if outcome == "done" and await _plain_question_waits(kernel, profile, job, last_content):
        outcome = "question"  # CARD-616: asked in plain text instead of ask_clarification
    if outcome == "question":
        # CARD-613: a step that asks Jacob a question is not done; it waits for his answer in the chat.
        orch.wait_for_answer(phase.id)
        await queue.put(
            _sse(
                "phase_complete",
                {"job_id": job.id, "phase_id": phase.id, "status": "waiting_for_answer", "react_state": "STOPPED"},
            )
        )
        return "question"
    if outcome == "parked":
        orch.park_phase(phase.id)
        await queue.put(
            _sse(
                "phase_complete",
                {
                    "job_id": job.id,
                    "phase_id": phase.id,
                    "status": "waiting_approval",
                    "react_state": "PARKED",
                },
            )
        )
        return "parked"
    if outcome == "failed":
        fail_detail = error_text or last_content or "phase failed"
        orch.fail_phase(phase.id, fail_detail)
        await queue.put(
            _sse(
                "phase_complete",
                {
                    "job_id": job.id,
                    "phase_id": phase.id,
                    "status": "failed",
                    "react_state": "FAILED",
                },
            )
        )
        honesty = format_job_failed_honesty(
            job_id=job.id,
            phase_name=getattr(phase, "name", None),
            reason=str(fail_detail)[:400],
        )
        await queue.put(_sse("token", {"text": honesty}))
        await queue.put(_sse("turn_done", {"content": honesty, "job_failed": True}))
        return "failed"

    gate = await _apply_verify_gate(
        queue=queue,
        reflexion_engine=reflexion_engine,
        profile=profile,
        phase=phase,
        last_output=last_content,
        self_verify=self_verify,
        step_index=step_index,
    )
    if self_verify and not gate.get("skipped") and not gate.get("verification_passed"):
        # CARD-254 / REQ-VRH-004: binary external fail -> 232 replan/park (never fail_phase dead-end).
        detail = "; ".join(gate.get("discrepancies") or ["checker failed"])
        standing = apply_phase_complete_verify_gate(
            orch,
            phase_id=phase.id,
            output_packet=output_packet_for_phase(
                phase,
                last_content,
                extra_facts=list(gate.get("facts") or []) + [detail],
            ),
            checker_passed=False,
        )
        action = str(standing.get("action") or "park")
        if action == "replan":
            await queue.put(
                _sse(
                    "phase_complete",
                    {
                        "job_id": job.id,
                        "phase_id": phase.id,
                        "status": "failed",
                        "react_state": "FAILED",
                        "action": "replan",
                        "needs_replan": True,
                        "replan_count": standing.get("replan_count"),
                        "last_fail_reason": standing.get("last_fail_reason") or detail,
                        "binary_external": True,
                    },
                )
            )
            return "replan"
        # park / exhausted / fallback — HITL park, never silent advance or infinite loop
        await queue.put(
            _sse(
                "phase_complete",
                {
                    "job_id": job.id,
                    "phase_id": phase.id,
                    "status": "waiting_approval",
                    "react_state": "PARKED",
                    "action": "park",
                    "replan_exhausted": bool(standing.get("replan_exhausted")),
                    "replan_count": standing.get("replan_count"),
                    "last_fail_reason": standing.get("last_fail_reason") or detail,
                    "binary_external": True,
                },
            )
        )
        return "parked"

    completed = await complete_phase_or_fail(
        orch=orch,
        queue=queue,
        job=job,
        phase=phase,
        output_packet=output_packet_for_phase(phase, last_content, extra_facts=gate.get("facts") or []),
    )
    if not completed:
        return "failed"
    await queue.put(
        _sse(
            "phase_complete",
            {
                "job_id": job.id,
                "phase_id": phase.id,
                "status": "done",
                "react_state": "DONE",
            },
        )
    )
    if emit_step_events:
        await queue.put(
            _sse(
                "step_complete",
                {
                    "step_index": phase.index if step_index is None else step_index,
                    "status": "completed",
                    "phase_id": phase.id,
                    "job_id": job.id,
                },
            )
        )
    return "done"
