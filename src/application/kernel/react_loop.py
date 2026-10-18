"""
Shared ReAct Execution Loop for AgentKernel.run_turn and stream_turn [REQ-KERNEL-003, REQ-KERNEL-006, CARD-712].
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

from src.application.kernel.context_compactor import ContextCompactor, resolve_max_tool_chars
from src.application.kernel.cycle_detector import CycleDetector
from src.application.kernel.empty_reply import (
    EMPTY_REPLY_MESSAGE,
    chat_note,
    is_empty_reply,
    latest_user_prompt,
    model_history_rows,
    post_tool_empty_fallback,
)
from src.application.kernel.json_safe import dumps_jsonable, dumps_tool_output
from src.application.kernel.repeat_guard import (
    LOOP_FALLBACK_MESSAGE,
    LOOP_FINAL_INSTRUCTION,
    TEXT_LOOP_MESSAGE,
    RepeatGuard,
    rejected_tool_names,
)
from src.application.kernel.reply_limits import (
    ReplyLimitStop,
    reply_token_limit,
    resolve_reply_limits,
    resolve_wiki_lookups,
    time_limit_message,
    token_limit_message,
)
from src.application.kernel.reply_rules import (
    CLARIFICATION_SKIPPED_RESULT,
    MEMORIZE_TOOL,
    ask_developer_ending,
    clarification_question,
    clarification_reply,
    describe_tool_run,
    failed_tool_note,
    is_toolsmith,
    memory_not_done_lines,
    memory_retry_prompt,
    settle_memory_retry,
    track_failure,
)
from src.application.kernel.telemetry_attribution import (
    extract_usage_tokens,
    record_failed_step_telemetry,
    record_step_telemetry,
)
from src.application.kernel.turn_limit import TURN_LIMIT_INSTRUCTION, TURN_LIMIT_REASON, turn_limit_reply
from src.application.kernel.wiki_budget import WikiLookupBudget
from src.application.orchestration.handoff_engine import looks_like_provider_failure
from src.domain.gateway.errors import EmptyModelReplyError, RateLimitError
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    ToolCall,
)
from src.domain.kernel.models import (
    AgentProfile,
    KernelEvent,
    KernelEventType,
)
from src.domain.orchestration.models import ReactState

logger = logging.getLogger(__name__)


def format_tool_error_content(error: Optional[str]) -> str:
    """Format a failed tool result consistently for both run_turn and stream_turn [CARD-712]."""
    err_str = str(error or "Tool execution error")
    return err_str if err_str.startswith("Tool Error:") else f"Tool Error: {err_str}"


async def execute_react_loop(
    kernel: Any,
    *,
    agent: AgentProfile,
    session_id: str,
    user_content: Optional[str] = None,
    save_to_history: bool = True,
    approval_mode: str = "ask",
    resume: bool = False,
    routine_id: Optional[str] = None,
    phase_id: Optional[str] = None,
    job_id: Optional[str] = None,
    parts_request: Optional[str] = None,
    stream: bool = False,
    max_tool_chars_fn: Callable[[int], int] = resolve_max_tool_chars,
    result_box: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[KernelEvent]:
    """Unified ReAct turn loop backing both AgentKernel.run_turn and AgentKernel.stream_turn [CARD-712]."""
    box = result_box if result_box is not None else {}
    kernel._ace_tool_errors = []
    kernel._turn_matched_capability_ids = kernel._matched_capability_ids_for_job(
        job_id=job_id, phase_id=phase_id, agent=agent
    )
    kernel._turn_planning_phase = kernel._is_planning_phase(phase_id)
    if resume:
        user_content = None
    if user_content and save_to_history:
        user_msg = ChatMessage(role=Role.USER, content=user_content)
        kernel.state_store.save_message(session_id=session_id, agent_id=agent.id, message=user_msg)

    react_ctx = {
        "phase_id": phase_id,
        "job_id": job_id,
        "assigned_agent_id": agent.id,
    }
    history = model_history_rows(kernel.state_store.get_messages(session_id=session_id))
    if user_content and not save_to_history:
        history.append(ChatMessage(role=Role.USER, content=user_content))

    notices_sent: set = set()
    if resume and stream:
        replay = kernel._nested_park_replay_events(history)
        if replay:
            parked_ev = kernel._transition_react_state(ReactState.PARKED, 0, **react_ctx)
            if parked_ev:
                yield parked_ev
            for ev in replay:
                yield ev
            return

    active_tools, offered_names, system_msg = kernel._turn_tools_and_system_message(
        agent, user_content, history, session_id=session_id
    )
    tool_schema_chars = (
        sum(
            len(dumps_jsonable(t.model_dump(mode="json") if hasattr(t, "model_dump") else getattr(t, "__dict__", {})))
            for t in active_tools
        )
        if active_tools
        else 0
    )
    kernel._last_turn_tool_stats = {
        "active_tool_count": len(active_tools),
        "tool_schema_chars": tool_schema_chars,
    }
    model_name = kernel._resolve_model(agent)

    cycle_detector = CycleDetector(max_repeats=3)
    repeat_guard = RepeatGuard(rejected_tool_names(history))
    wiki_budget = WikiLookupBudget(resolve_wiki_lookups(kernel.state_store))

    trace_id = session_id or str(uuid.uuid4())
    provider_name = getattr(agent, "provider", None) or (agent.model.split("/")[0] if "/" in agent.model else None)
    turn_span_id = None
    kernel._ensure_agent_provider_adapter(agent)
    last_turn_end = None
    last_failure: Optional[Tuple[str, str]] = None
    tools_ran: List[str] = []
    pending_not_done: Optional[str] = None
    tools_before_retry = 0

    for turn_idx in range(agent.max_turns):
        repeat_guard.next_step()
        thinking_ev = kernel._transition_react_state(ReactState.THINKING, turn_idx, **react_ctx)
        if stream and thinking_ev:
            yield thinking_ev
        turn_start = time.perf_counter()
        inter_step_latency_ms = ((turn_start - last_turn_end) * 1000) if last_turn_end is not None else None
        first_token_time = None
        ttft_ms = None
        context_limit = kernel._resolve_context_limit(agent, model_name)
        scaled_tool_chars = max_tool_chars_fn(context_limit)
        compacted_messages = ContextCompactor.compact(
            [system_msg] + history,
            model_name=model_name,
            max_tokens=max(1000, int(context_limit * 0.75)),
            keep_last_n_turns=4,
            max_tool_chars=scaled_tool_chars,
            preserve_root_intent=True,
        )
        reply_max_tokens, reply_max_seconds = resolve_reply_limits(kernel.state_store)
        reply_max_tokens = reply_token_limit(reply_max_tokens, context_limit)
        req = CompletionRequest(
            model=model_name,
            messages=compacted_messages,
            tools=wiki_budget.offer(active_tools) or None,
            num_ctx=context_limit,
            max_tokens=reply_max_tokens,
            stream=stream,
        )
        prep_end = time.perf_counter()
        harness_prep_ms = (prep_end - turn_start) * 1000

        full_content = ""
        full_reasoning: Optional[str] = None
        collected_tool_calls: List[ToolCall] = []
        prompt_tokens: Optional[int] = None
        comp_tokens: Optional[int] = None
        step_model_name = model_name

        if not stream:
            try:
                resp: CompletionResponse = await kernel.gateway.complete(req)
                turn_dur_ms = (time.perf_counter() - turn_start) * 1000
                prompt_tokens, comp_tokens = extract_usage_tokens(resp.usage)
                step_model_name = resp.model or model_name
                if resp.message:
                    full_content = resp.message.content or ""
                    full_reasoning = getattr(resp.message, "reasoning", None) or getattr(resp, "reasoning_content", None)
                    collected_tool_calls = list(resp.message.tool_calls or [])
                else:
                    full_reasoning = getattr(resp, "reasoning_content", None)
            except Exception as e:
                turn_dur_ms = (time.perf_counter() - turn_start) * 1000
                record_failed_step_telemetry(
                    kernel,
                    agent=agent,
                    session_id=session_id,
                    model_name=model_name,
                    provider_name=provider_name,
                    turn_dur_ms=turn_dur_ms,
                    harness_prep_ms=harness_prep_ms,
                    ttft_ms=None,
                    inter_step_latency_ms=inter_step_latency_ms,
                    error_message=str(e),
                    trace_id=trace_id,
                )
                kernel._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                kernel._ace_flush_failed_turn(
                    session_id=session_id, agent_id=agent.id, failed=True, error_message=str(e)
                )
                if isinstance(e, RateLimitError):
                    rate_limit_text = (
                        f"⚠️ Rate limit reached on {provider_name} ({model_name}): {e.message}. "
                        "Please wait or update provider configuration."
                    )
                    rate_limit_msg = ChatMessage(role=Role.ASSISTANT, content=rate_limit_text)
                    if save_to_history:
                        kernel.state_store.save_message(
                            session_id=session_id, agent_id=agent.id, message=rate_limit_msg
                        )
                    box["message"] = rate_limit_msg
                    return
                raise
        else:
            accumulated_content: List[str] = []
            accumulated_reasoning: List[str] = []
            finish_reason: Optional[str] = None
            stream_gen = None
            try:
                stream_gen = kernel.gateway.stream(req, demux_reasoning=True)
                deadline: Optional[float] = None
                while True:
                    try:
                        if deadline is None:
                            chunk = await stream_gen.__anext__()
                        else:
                            chunk = await asyncio.wait_for(
                                stream_gen.__anext__(), timeout=max(0.0, deadline - time.monotonic())
                            )
                    except StopAsyncIteration:
                        break
                    except asyncio.TimeoutError:
                        raise ReplyLimitStop(time_limit_message(reply_max_seconds)) from None
                    if chunk.notice:
                        note_text = str(chunk.notice.get("message") or "")
                        if note_text and note_text not in notices_sent:
                            notices_sent.add(note_text)
                            try:
                                kernel.state_store.save_message(
                                    session_id=session_id, agent_id=agent.id, message=chat_note(chunk.notice, note_text)
                                )
                            except Exception as exc:
                                logger.warning("chat note not saved: %s", exc)
                            yield KernelEvent(
                                event_type=KernelEventType.NOTICE, content=note_text, notice=dict(chunk.notice)
                            )
                        continue
                    if first_token_time is None and (chunk.content or chunk.reasoning_content or chunk.tool_calls):
                        first_token_time = time.perf_counter()
                        ttft_ms = (first_token_time - turn_start) * 1000
                        deadline = time.monotonic() + reply_max_seconds

                    if chunk.content or chunk.reasoning_content:
                        if chunk.content:
                            accumulated_content.append(chunk.content)
                        if chunk.reasoning_content:
                            accumulated_reasoning.append(chunk.reasoning_content)
                        yield KernelEvent(
                            event_type=KernelEventType.TOKEN,
                            content=chunk.content,
                            reasoning_content=chunk.reasoning_content,
                        )

                    if chunk.tool_calls:
                        collected_tool_calls.extend(chunk.tool_calls)
                    if chunk.finish_reason:
                        finish_reason = chunk.finish_reason
                    if chunk.is_finished:
                        break
                if finish_reason == "length" and not collected_tool_calls:
                    answered = bool("".join(accumulated_content).strip())
                    note = token_limit_message(reply_max_tokens, answered)
                    if not answered:
                        raise ReplyLimitStop(note)
                    accumulated_content.append("\n\n" + note)
                    yield KernelEvent(event_type=KernelEventType.TOKEN, content="\n\n" + note)
            except Exception as e:
                turn_dur_ms = (time.perf_counter() - turn_start) * 1000
                record_failed_step_telemetry(
                    kernel,
                    agent=agent,
                    session_id=session_id,
                    model_name=model_name,
                    provider_name=provider_name,
                    turn_dur_ms=turn_dur_ms,
                    harness_prep_ms=harness_prep_ms,
                    ttft_ms=ttft_ms,
                    inter_step_latency_ms=inter_step_latency_ms,
                    error_message=str(e),
                    trace_id=trace_id,
                )
                failed_ev = kernel._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                if failed_ev:
                    yield failed_ev
                kernel._ace_flush_failed_turn(
                    session_id=session_id, agent_id=agent.id, failed=True, error_message=str(e)
                )
                if isinstance(e, ReplyLimitStop):
                    if save_to_history:
                        kernel.state_store.save_message(
                            session_id=session_id,
                            agent_id=agent.id,
                            message=ChatMessage(role=Role.ASSISTANT, content=e.message),
                        )
                    yield KernelEvent(event_type=KernelEventType.TOKEN, content="\n\n" + e.message)
                    yield KernelEvent(event_type=KernelEventType.ERROR, content=e.message, is_finished=True)
                    return
                if isinstance(e, RateLimitError):
                    rate_limit_text = (
                        f"⚠️ Rate limit reached on {provider_name} ({model_name}): {e.message}. "
                        "Please wait or update provider configuration."
                    )
                    if save_to_history:
                        kernel.state_store.save_message(
                            session_id=session_id,
                            agent_id=agent.id,
                            message=ChatMessage(role=Role.ASSISTANT, content=rate_limit_text),
                        )
                    yield KernelEvent(event_type=KernelEventType.TOKEN, content=rate_limit_text)
                    yield KernelEvent(event_type=KernelEventType.ERROR, content=rate_limit_text, is_finished=True)
                    return
                yield KernelEvent(event_type=KernelEventType.ERROR, content=str(e), is_finished=True)
                return
            finally:
                closer = getattr(stream_gen, "aclose", None)
                if callable(closer):
                    await closer()

            full_content = "".join(accumulated_content)
            full_reasoning = "".join(accumulated_reasoning) if accumulated_reasoning else None
            turn_dur_ms = (time.perf_counter() - turn_start) * 1000

        turn_span_id = record_step_telemetry(
            kernel,
            agent=agent,
            session_id=session_id,
            model_name=step_model_name,
            provider_name=provider_name,
            turn_dur_ms=turn_dur_ms,
            harness_prep_ms=harness_prep_ms,
            ttft_ms=ttft_ms,
            inter_step_latency_ms=inter_step_latency_ms,
            user_content=user_content,
            compacted_messages=compacted_messages,
            active_tools=active_tools,
            tool_schema_chars=tool_schema_chars,
            full_content=full_content,
            full_reasoning=full_reasoning,
            tool_calls=collected_tool_calls or None,
            prompt_tokens=prompt_tokens,
            comp_tokens=comp_tokens,
            trace_id=trace_id,
            job_id=job_id,
            phase_id=phase_id,
        )

        # Text generation repetition loop check [REQ-RESIL-003]
        if full_content and cycle_detector.record_and_check_text(full_content):
            failed_ev = kernel._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
            if stream and failed_ev:
                yield failed_ev
            cycle_msg = ChatMessage(role=Role.ASSISTANT, content=TEXT_LOOP_MESSAGE)
            if save_to_history:
                kernel.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
            kernel._ace_flush_failed_turn(
                session_id=session_id, agent_id=agent.id, failed=True, error_message=cycle_msg.content
            )
            box["message"] = cycle_msg
            if stream:
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=cycle_msg.content, is_finished=True)
            return

        # If no tool calls returned, turn is complete
        if not collected_tool_calls:
            if is_empty_reply(full_content, None):
                fallback_reply = post_tool_empty_fallback(history)
                if fallback_reply:
                    full_content = fallback_reply
                    if stream:
                        yield KernelEvent(event_type=KernelEventType.TOKEN, content=full_content)
                else:
                    failed_ev = kernel._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                    if stream and failed_ev:
                        yield failed_ev
                    kernel._ace_flush_failed_turn(
                        session_id=session_id, agent_id=agent.id, failed=True, error_message=EMPTY_REPLY_MESSAGE
                    )
                    if stream:
                        yield KernelEvent(
                            event_type=KernelEventType.ERROR, content=EMPTY_REPLY_MESSAGE, is_finished=True
                        )
                        return
                    raise EmptyModelReplyError(EMPTY_REPLY_MESSAGE, provider_id=provider_name)

            user_req_text = latest_user_prompt(user_content, history)
            gap = kernel._detect_and_record_capability_gap(
                agent=agent,
                user_req_text=user_req_text,
                assistant_response=full_content,
                history=history,
                session_id=session_id,
                streamed=stream,
            )

            skipped = ""
            if stream:
                if pending_not_done is not None:
                    skipped = settle_memory_retry(pending_not_done, tools_ran[tools_before_retry:])
                elif parts_request and not resume:
                    skipped = await kernel._skipped_parts_note(
                        model_name, parts_request, tools_ran, full_content, context_limit
                    )
                    memory_lines = memory_not_done_lines(skipped)
                    if memory_lines and MEMORIZE_TOOL in offered_names and turn_idx + 2 < agent.max_turns:
                        pending_not_done, tools_before_retry = skipped, len(tools_ran)
                        first_msg = ChatMessage(role=Role.ASSISTANT, content=full_content, reasoning=full_reasoning)
                        if save_to_history:
                            kernel.state_store.save_message(
                                session_id=session_id, agent_id=agent.id, message=first_msg
                            )
                        history.append(first_msg)
                        history.append(ChatMessage(role=Role.USER, content=memory_retry_prompt(memory_lines)))
                        yield KernelEvent(event_type=KernelEventType.TOKEN, content="\n\n")
                        continue

            done_ev = kernel._transition_react_state(ReactState.DONE, turn_idx, **react_ctx)
            if stream and done_ev:
                yield done_ev
            note = "\n".join(x for x in (skipped, failed_tool_note(full_content, last_failure)) if x)
            if note:
                full_content = f"{full_content.rstrip()}\n\n{note}"
                if stream:
                    yield KernelEvent(event_type=KernelEventType.TOKEN, content=f"\n\n{note}")
            ended = ask_developer_ending(
                full_content,
                history,
                gap.missing_capability if gap else None,
                kernel._own_tool_names(agent),
                offer=not is_toolsmith(agent),
            )
            if stream and ended.startswith(full_content.rstrip()) and len(ended) > len(full_content.rstrip()):
                yield KernelEvent(event_type=KernelEventType.TOKEN, content=ended[len(full_content.rstrip()) :])
            full_content = ended
            assistant_msg = ChatMessage(
                role=Role.ASSISTANT,
                content=full_content,
                reasoning=full_reasoning,
            )
            if save_to_history:
                kernel.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
            kernel._ace_flush_failed_turn(session_id=session_id, agent_id=agent.id, failed=False)
            box["message"] = assistant_msg
            if stream:
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=full_content, is_finished=True)
            return

        # Tool call cycle detection [REQ-RESIL-003]
        if cycle_detector.record_and_check(collected_tool_calls):
            final_text = await kernel._final_answer_without_tools(
                model_name, system_msg, history, context_limit, LOOP_FINAL_INSTRUCTION
            )
            end_ev = kernel._transition_react_state(
                ReactState.DONE if final_text else ReactState.FAILED, turn_idx, **react_ctx
            )
            if stream and end_ev:
                yield end_ev
            cycle_text = final_text or LOOP_FALLBACK_MESSAGE
            note = failed_tool_note(cycle_text, last_failure)
            cycle_msg = ChatMessage(role=Role.ASSISTANT, content=f"{cycle_text}\n\n{note}" if note else cycle_text)
            if save_to_history:
                kernel.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
            kernel._ace_flush_failed_turn(
                session_id=session_id,
                agent_id=agent.id,
                failed=not final_text,
                error_message=None if final_text else "repeat_loop",
            )
            box["message"] = cycle_msg
            if stream:
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=cycle_msg.content, is_finished=True)
            return

        # Save assistant message with tool calls
        assistant_msg = ChatMessage(
            role=Role.ASSISTANT,
            content=full_content,
            tool_calls=collected_tool_calls,
            reasoning=full_reasoning,
        )
        if save_to_history:
            kernel.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
        history.append(assistant_msg)

        calling_ev = kernel._transition_react_state(ReactState.CALLING_TOOLS, turn_idx, **react_ctx)
        if stream and calling_ev:
            yield calling_ev

        # Execute tool calls
        clarify_q: Optional[str] = None
        for tc in collected_tool_calls:
            if clarify_q is not None:
                skipped_msg = ChatMessage(
                    role=Role.TOOL, content=CLARIFICATION_SKIPPED_RESULT, tool_call_id=tc.id, name=tc.name
                )
                if save_to_history:
                    kernel.state_store.save_message(session_id=session_id, agent_id=agent.id, message=skipped_msg)
                history.append(skipped_msg)
                continue

            is_handoff_tool = tc.name in ("handoff_to_agent", "hand_off_card")
            if stream and is_handoff_tool:
                args = tc.arguments if isinstance(tc.arguments, dict) else {}
                card_handoff = tc.name == "hand_off_card"
                target_id = (
                    "developer"
                    if card_handoff
                    else (args.get("target_agent") or args.get("target_agent_id") or "specialist")
                )
                directive = (
                    f"Work card {args.get('card_id', '')} to In Review in the active project."
                    if card_handoff
                    else args.get("task_intent") or args.get("task_directive") or ""
                )
                yield KernelEvent(
                    event_type=KernelEventType.HANDOFF_START,
                    handoff={"sender": agent.id, "recipient": target_id, "directive": directive},
                )

            if stream:
                yield KernelEvent(
                    event_type=KernelEventType.TOOL_START,
                    tool_call={"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                )

            gated = (
                wiki_budget.check(tc)
                or repeat_guard.reuse(tc)
                or kernel._gate_tool_call(
                    tc,
                    session_id,
                    agent,
                    approval_mode=approval_mode,
                    routine_id=routine_id,
                    matched_capability_ids=kernel._matched_capability_ids_for_job(react_ctx.get("job_id"), agent=agent),
                    job_id=react_ctx.get("job_id"),
                    planning_phase=kernel._is_planning_phase(react_ctx.get("phase_id")),
                    offered=offered_names,
                )
            )
            if gated is not None:
                tool_res = gated
                if stream and tool_res.error and str(tool_res.error).startswith("approval_required:"):
                    approval_id = str(tool_res.output.get("approval_id") if isinstance(tool_res.output, dict) else "")
                    yield KernelEvent(
                        event_type=KernelEventType.APPROVAL_REQUIRED,
                        content=tool_res.output.get("message", "Approval required")
                        if isinstance(tool_res.output, dict)
                        else "Approval required",
                        approval_id=approval_id or None,
                        tool_call={"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                        tool_result=tool_res,
                    )
            else:
                tool_res = await kernel.execute_and_scrub_tool(
                    tc,
                    agent,
                    session_id=session_id,
                    approval_mode=approval_mode,
                    job_id=react_ctx.get("job_id"),
                    offered=offered_names,
                )
                nested = tool_res.output if isinstance(tool_res.output, dict) else None
                if stream and nested and nested.get("status") == "approval_required" and nested.get("approval_id"):
                    yield KernelEvent(
                        event_type=KernelEventType.APPROVAL_REQUIRED,
                        content=nested.get("message") or "Approval required",
                        approval_id=str(nested.get("approval_id")),
                        tool_call={
                            "id": tc.id,
                            "name": nested.get("tool_name") or tc.name,
                            "arguments": nested.get("arguments") or {},
                        },
                        tool_result=tool_res,
                    )

            repeat_guard.record(tc, tool_res)
            is_direct_park = bool(tool_res.error and str(tool_res.error).startswith("approval_required:"))
            nested_out = tool_res.output if isinstance(tool_res.output, dict) else None
            is_nested_park = bool(
                nested_out and nested_out.get("status") == "approval_required" and nested_out.get("approval_id")
            )
            parked = is_direct_park or is_nested_park

            tool_status = "hitl_paused" if is_direct_park else ("ok" if tool_res.success else "error")
            tool_success = True if is_direct_park else tool_res.success
            raw_payload = dumps_tool_output(tool_res.output) if tool_res.success else (tool_res.error or "")
            payload_bytes = len(raw_payload.encode("utf-8"))
            tc_args = getattr(tc, "arguments", None) or getattr(tc, "args", None) or {}

            kernel.telemetry.record_tool_span(
                agent_id=agent.id,
                session_id=session_id,
                tool_name=tc.name,
                duration_ms=tool_res.duration_ms,
                success=tool_success,
                status=tool_status,
                error_message=tool_res.error,
                trace_id=trace_id,
                parent_span_id=turn_span_id,
                metadata={"payload_bytes": payload_bytes, "arguments": tc_args},
            )
            kernel._ace_note_tool(tc.name, tool_res.success, tool_res.error)

            if stream:
                yield KernelEvent(
                    event_type=KernelEventType.TOOL_END,
                    tool_call={"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                    tool_result=tool_res,
                )

            if stream and is_handoff_tool:
                args = tc.arguments if isinstance(tc.arguments, dict) else {}
                target_id = args.get("target_agent") or args.get("target_agent_id") or "specialist"
                output_blob = dumps_tool_output(tool_res.output)
                if parked:
                    handoff_status = "approval_required"
                elif (
                    (not tool_res.success)
                    or looks_like_provider_failure(output_blob)
                    or looks_like_provider_failure(str(tool_res.error or ""))
                ):
                    handoff_status = "failed"
                else:
                    handoff_status = "completed"
                yield KernelEvent(
                    event_type=KernelEventType.HANDOFF_COMPLETE,
                    handoff={"recipient": target_id, "status": handoff_status, "error": tool_res.error},
                )

            if tool_res.success:
                tool_content = dumps_tool_output(tool_res.output)
            else:
                tool_content = format_tool_error_content(tool_res.error)

            tool_msg = ChatMessage(
                role=Role.TOOL,
                content=tool_content,
                tool_call_id=tc.id,
                name=tc.name,
            )
            if save_to_history:
                kernel.state_store.save_message(session_id=session_id, agent_id=agent.id, message=tool_msg)
            history.append(tool_msg)

            if parked:
                parked_ev = kernel._transition_react_state(ReactState.PARKED, turn_idx, **react_ctx)
                if stream and parked_ev:
                    yield parked_ev
                if not stream:
                    if is_nested_park and isinstance(nested_out, dict):
                        parked_payload = dict(nested_out)
                    else:
                        parked_payload = {
                            "status": "approval_required",
                            "approval_id": tool_res.output.get("approval_id")
                            if isinstance(tool_res.output, dict)
                            else "",
                            "tool_name": tc.name,
                            "arguments": tc.arguments if isinstance(tc.arguments, dict) else {},
                            "message": tool_res.output.get("message")
                            if isinstance(tool_res.output, dict)
                            else "Approval required",
                        }
                    parked_msg = ChatMessage(role=Role.ASSISTANT, content=dumps_jsonable(parked_payload))
                    if save_to_history:
                        kernel.state_store.save_message(session_id=session_id, agent_id=agent.id, message=parked_msg)
                    box["message"] = parked_msg
                    return
                park_text = ""
                if isinstance(tool_res.output, dict):
                    park_text = str(tool_res.output.get("message") or "")
                yield KernelEvent(
                    event_type=KernelEventType.TURN_END,
                    content=park_text,
                    is_finished=True,
                )
                return

            last_failure = track_failure(last_failure, tc.name, tool_res.success, tool_res.error, tool_res.output)
            tools_ran.append(describe_tool_run(tc.name, tc.arguments, not tool_res.success, tool_res.output))
            clarify_q = clarification_question(tc.name, tool_res.success, tool_res.output, tc.arguments)

        if clarify_q is not None:
            done_ev = kernel._transition_react_state(ReactState.DONE, turn_idx, **react_ctx)
            if stream and done_ev:
                yield done_ev
            question = clarification_reply(clarify_q, full_content)
            if stream:
                if question and save_to_history:
                    kernel.state_store.save_message(
                        session_id=session_id,
                        agent_id=agent.id,
                        message=ChatMessage(role=Role.ASSISTANT, content=question),
                    )
                if question:
                    yield KernelEvent(
                        event_type=KernelEventType.TOKEN,
                        content=f"\n\n{question}" if full_content.strip() else question,
                    )
                kernel._ace_flush_failed_turn(session_id=session_id, agent_id=agent.id, failed=False)
                yield KernelEvent(
                    event_type=KernelEventType.TURN_END,
                    content=question or full_content,
                    is_finished=True,
                    react={"clarification": True},
                )
                return
            question_msg = ChatMessage(role=Role.ASSISTANT, content=question or clarify_q)
            if save_to_history:
                kernel.state_store.save_message(session_id=session_id, agent_id=agent.id, message=question_msg)
            kernel._ace_flush_failed_turn(session_id=session_id, agent_id=agent.id, failed=False)
            box["message"] = question_msg
            return

        active_tools, offered_names, system_msg = kernel._turn_tools_and_system_message(
            agent, user_content, history, session_id=session_id
        )
        last_turn_end = time.perf_counter()

    # Turn limit reached [CARD-461]
    summary = await kernel._final_answer_without_tools(
        model_name, system_msg, history, kernel._resolve_context_limit(agent, model_name), TURN_LIMIT_INSTRUCTION
    )
    failed_ev = kernel._transition_react_state(ReactState.FAILED, agent.max_turns, **react_ctx)
    if stream and failed_ev:
        yield failed_ev
    limit_msg = ChatMessage(role=Role.ASSISTANT, content=turn_limit_reply(summary, agent.max_turns))
    kernel._ace_flush_failed_turn(
        session_id=session_id, agent_id=agent.id, failed=True, error_message=TURN_LIMIT_REASON
    )
    if save_to_history:
        kernel.state_store.save_message(session_id=session_id, agent_id=agent.id, message=limit_msg)
    box["message"] = limit_msg
    if stream:
        yield KernelEvent(event_type=KernelEventType.TOKEN, content=limit_msg.content)
        yield KernelEvent(
            event_type=KernelEventType.TURN_END,
            content=limit_msg.content,
            is_finished=True,
        )
