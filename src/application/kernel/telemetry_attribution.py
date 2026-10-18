"""Granular Token & Timing Telemetry Attribution [CARD-337 / REQ-TEL-002, REQ-TEL-003].

Isolates prompt components (user input, persona, tool schemas, progressive skills,
episodic memory, compacted history, tool results) and turn timing stages.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence

from src.domain.gateway.models import ChatMessage, Role, ToolDefinition


def estimate_tokens(text: Optional[str]) -> int:
    """Fast, lightweight token count approximation (~4 chars per token)."""
    if not text:
        return 0
    stripped = text.strip()
    if not stripped:
        return 0
    # Floor of 1 token for non-empty text
    return max(1, len(stripped) // 4)


@dataclass(frozen=True)
class TokenBreakdown:
    """Granular token distribution across prompt components and outputs."""

    user_prompt: int = 0
    agent_persona: int = 0
    tool_schemas: int = 0
    progressive_skills: int = 0
    episodic_memory: int = 0
    compacted_history: int = 0
    tool_results_injected: int = 0
    completion: int = 0
    reasoning: int = 0
    total_prompt_tokens: int = 0
    total_tokens: int = 0
    scaffold_tokens: int = 0
    scaffold_ratio: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TimingBreakdown:
    """Turn timing breakdown across preparation, TTFT, generation, and multi-step."""

    harness_prep_ms: float = 0.0
    ttft_ms: Optional[float] = None
    generation_ms: Optional[float] = None
    tokens_per_second: Optional[float] = None
    inter_step_latency_ms: Optional[float] = None
    total_round_trip_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def extract_usage_tokens(usage: Any) -> tuple[int, int]:
    """Extract (prompt_tokens, completion_tokens) from a provider usage dict or object [CARD-696]."""
    if not usage:
        return 0, 0
    if isinstance(usage, dict):
        return int(usage.get("prompt_tokens", 0) or 0), int(usage.get("completion_tokens", 0) or 0)
    return int(getattr(usage, "prompt_tokens", 0) or 0), int(getattr(usage, "completion_tokens", 0) or 0)


def _estimate_tool_calls_tokens(tool_calls: Optional[Sequence[Any]]) -> int:
    if not tool_calls:
        return 0
    tc_payloads = []
    for tc in tool_calls:
        if isinstance(tc, dict):
            tc_payloads.append({"name": tc.get("name", ""), "arguments": tc.get("arguments", {})})
        else:
            tc_payloads.append(
                {
                    "name": getattr(tc, "name", "") or "",
                    "arguments": getattr(tc, "arguments", {}) or {},
                }
            )
    return estimate_tokens(json.dumps(tc_payloads, default=str)) if tc_payloads else 0


def calculate_token_attribution(
    user_prompt: Optional[str] = None,
    agent_persona: Optional[str] = None,
    tool_definitions: Optional[Sequence[ToolDefinition | Dict[str, Any]]] = None,
    progressive_skills: Optional[Sequence[str]] = None,
    episodic_memory: Optional[Sequence[str]] = None,
    compacted_history: Optional[Sequence[ChatMessage]] = None,
    tool_results_injected: Optional[Sequence[str]] = None,
    completion: Optional[str] = None,
    reasoning: Optional[str] = None,
    tool_calls: Optional[Sequence[Any]] = None,
) -> TokenBreakdown:
    """Calculate discrete token attribution for every prompt component."""
    u_tok = estimate_tokens(user_prompt)
    p_tok = estimate_tokens(agent_persona)

    # Tool schemas (serialized parameters)
    t_tok = 0
    if tool_definitions:
        tool_payloads = []
        for t in tool_definitions:
            if isinstance(t, ToolDefinition):
                tool_payloads.append({"name": t.name, "description": t.description, "parameters": t.parameters})
            elif isinstance(t, dict):
                tool_payloads.append(t)
        if tool_payloads:
            t_tok = estimate_tokens(json.dumps(tool_payloads))

    # Progressive skill bodies
    s_tok = sum(estimate_tokens(s) for s in (progressive_skills or []))

    # Episodic memory facts
    m_tok = sum(estimate_tokens(f) for f in (episodic_memory or []))

    # Compacted history (prior turns in context, excluding current user message)
    h_tok = 0
    if compacted_history:
        for msg in compacted_history:
            h_tok += estimate_tokens(getattr(msg, "content", "") or "")
            h_tok += _estimate_tool_calls_tokens(getattr(msg, "tool_calls", None))

    # Injected tool outputs/results
    tr_tok = sum(estimate_tokens(r) for r in (tool_results_injected or []))

    # Outputs (include tool-call payload tokens when a round ends in tool calls [CARD-696])
    c_tok = estimate_tokens(completion) + _estimate_tool_calls_tokens(tool_calls)
    r_tok = estimate_tokens(reasoning)

    total_prompt = u_tok + p_tok + t_tok + s_tok + m_tok + h_tok + tr_tok
    total = total_prompt + c_tok + r_tok
    scaffold = total_prompt - u_tok
    ratio = round(scaffold / max(u_tok, 1), 2)

    return TokenBreakdown(
        user_prompt=u_tok,
        agent_persona=p_tok,
        tool_schemas=t_tok,
        progressive_skills=s_tok,
        episodic_memory=m_tok,
        compacted_history=h_tok,
        tool_results_injected=tr_tok,
        completion=c_tok,
        reasoning=r_tok,
        total_prompt_tokens=total_prompt,
        total_tokens=total,
        scaffold_tokens=scaffold,
        scaffold_ratio=ratio,
    )


def calculate_timing_attribution(
    harness_prep_ms: float = 0.0,
    ttft_ms: Optional[float] = None,
    total_round_trip_ms: float = 0.0,
    completion_tokens: int = 0,
    inter_step_latency_ms: Optional[float] = None,
) -> TimingBreakdown:
    """Calculate latency attribution stages and generation throughput."""
    gen_ms: Optional[float] = None
    tps: Optional[float] = None

    if ttft_ms is not None and total_round_trip_ms >= ttft_ms:
        gen_ms = round(total_round_trip_ms - ttft_ms, 2)
        if gen_ms > 0 and completion_tokens > 0:
            tps = round(completion_tokens / (gen_ms / 1000.0), 2)

    return TimingBreakdown(
        harness_prep_ms=round(harness_prep_ms, 2),
        ttft_ms=round(ttft_ms, 2) if ttft_ms is not None else None,
        generation_ms=gen_ms,
        tokens_per_second=tps,
        inter_step_latency_ms=round(inter_step_latency_ms, 2) if inter_step_latency_ms is not None else None,
        total_round_trip_ms=round(total_round_trip_ms, 2),
    )


def record_step_telemetry(
    kernel: Any,
    *,
    agent: Any,
    session_id: str,
    model_name: str,
    provider_name: Optional[str],
    turn_dur_ms: float,
    harness_prep_ms: float,
    ttft_ms: Optional[float],
    inter_step_latency_ms: Optional[float],
    user_content: Optional[str],
    compacted_messages: List[Any],
    active_tools: List[Any],
    tool_schema_chars: int,
    full_content: str,
    full_reasoning: Optional[str],
    tool_calls: Optional[List[Any]],
    prompt_tokens: Optional[int],
    comp_tokens: Optional[int],
    trace_id: str,
    job_id: Optional[str],
    phase_id: Optional[str],
) -> str:
    """Record a completed step turn span with token and timing attribution [CARD-712]."""
    effective_user_prompt = user_content or next(
        (m.content for m in reversed(compacted_messages) if m.role == Role.USER and m.content), ""
    )
    history_msgs = [
        m for m in compacted_messages if m.role != Role.SYSTEM and m.content != effective_user_prompt
    ]
    tool_results = [m.content for m in compacted_messages if m.role == Role.TOOL and m.content]

    token_breakdown = calculate_token_attribution(
        user_prompt=effective_user_prompt,
        agent_persona=getattr(agent, "system_prompt", ""),
        tool_definitions=active_tools,
        progressive_skills=getattr(kernel, "_last_progressive_skills", None),
        episodic_memory=getattr(kernel, "_last_episodic_memory", None),
        compacted_history=history_msgs,
        tool_results_injected=tool_results,
        completion=full_content,
        reasoning=full_reasoning,
        tool_calls=tool_calls,
    )
    timing_breakdown = calculate_timing_attribution(
        harness_prep_ms=harness_prep_ms,
        ttft_ms=ttft_ms,
        total_round_trip_ms=turn_dur_ms,
        completion_tokens=comp_tokens or token_breakdown.completion,
        inter_step_latency_ms=inter_step_latency_ms,
    )
    turn_span = kernel.telemetry.record_turn_span(
        agent_id=agent.id,
        session_id=session_id,
        model=model_name,
        provider=provider_name,
        duration_ms=turn_dur_ms,
        ttft_ms=ttft_ms,
        prompt_tokens=prompt_tokens or token_breakdown.total_prompt_tokens,
        completion_tokens=comp_tokens or token_breakdown.completion,
        success=True,
        trace_id=trace_id,
        metadata={
            "token_breakdown": token_breakdown.to_dict(),
            "timing_breakdown": timing_breakdown.to_dict(),
            "active_tool_count": len(active_tools),
            "tool_schema_chars": tool_schema_chars,
            "step_context": {
                "job_id": job_id,
                "phase_id": phase_id,
            },
        },
    )
    return turn_span.id


def record_failed_step_telemetry(
    kernel: Any,
    *,
    agent: Any,
    session_id: str,
    model_name: str,
    provider_name: Optional[str],
    turn_dur_ms: float,
    harness_prep_ms: float,
    ttft_ms: Optional[float],
    inter_step_latency_ms: Optional[float],
    error_message: str,
    trace_id: str,
) -> None:
    """Record a failed step turn span with timing attribution [CARD-712]."""
    timing_breakdown = calculate_timing_attribution(
        harness_prep_ms=harness_prep_ms,
        ttft_ms=ttft_ms,
        total_round_trip_ms=turn_dur_ms,
        completion_tokens=0,
        inter_step_latency_ms=inter_step_latency_ms,
    )
    kernel.telemetry.record_turn_span(
        agent_id=agent.id,
        session_id=session_id,
        model=model_name,
        provider=provider_name,
        duration_ms=turn_dur_ms,
        success=False,
        error_message=error_message,
        trace_id=trace_id,
        metadata={"timing_breakdown": timing_breakdown.to_dict()},
    )

