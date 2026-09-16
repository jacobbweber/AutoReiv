"""Granular Token & Timing Telemetry Attribution [CARD-337 / REQ-TEL-002, REQ-TEL-003].

Isolates prompt components (user input, persona, tool schemas, progressive skills,
episodic memory, compacted history, tool results) and turn timing stages.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Sequence

from src.domain.gateway.models import ChatMessage, ToolDefinition


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

    # Injected tool outputs/results
    tr_tok = sum(estimate_tokens(r) for r in (tool_results_injected or []))

    # Outputs
    c_tok = estimate_tokens(completion)
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
