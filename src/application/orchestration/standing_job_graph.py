"""
Standing Job-Graph routing [REQ-JOBGRAPH-001, REQ-JOBGRAPH-001a].

Runtime (not a Chat toggle) decides:
  multi-step outcomes -> JobPhaseOrchestrator formulate/advance/replan
  short tool turns    -> plain AgentKernel ReAct

Do not invent another user-facing or request-flag "mode".
"""

from __future__ import annotations

import re
from enum import Enum

from src.application.orchestration.phase_llm_resilience import (  # noqa: F401
    STANDING_PHASE_LLM_RETRIES,
    STANDING_PHASE_LLM_TIMEOUT_SECONDS,
    await_phase_llm_with_retry,
    format_phase_llm_exhausted_reason,
    is_phase_llm_retryable,
    resolve_standing_phase_llm_retries,
    resolve_standing_phase_llm_timeout,
)

class StandingRoute(str, Enum):
    MULTI_STEP_JOB_GRAPH = "multi_step_job_graph"
    SHORT_REACT = "short_react"


def is_multi_step_outcome(text: str | None) -> bool:
    """Heuristic for durable multi-phase outcomes (mirrors Chat SPA heuristic)."""
    if not text or not isinstance(text, str):
        return False
    trimmed = text.strip()
    if len(trimmed) < 25:
        return False

    numbered = re.findall(r"(?:^|\n)\s*(?:\d+[.)]|\(\d+\))\s+[^\n]+", trimmed)
    if len(numbered) >= 2:
        return True

    step_phase = re.findall(
        r"(?:^|\n|\b)(?:step|phase|milestone|task)\s+[1-9]\b",
        trimmed,
        flags=re.IGNORECASE,
    )
    if len(step_phase) >= 2:
        return True

    has_first = bool(re.search(r"\b(?:first|step\s+one|initially)\b", trimmed, re.I))
    has_then = bool(
        re.search(r"\b(?:then|next|after\s+that|secondly|afterwards)\b", trimmed, re.I)
    )
    has_finally = bool(re.search(r"\b(?:finally|lastly|in\s+the\s+end)\b", trimmed, re.I))
    if has_first and (has_then or has_finally) and len(trimmed) >= 40:
        return True

    return False


def route_standing_chat(text: str | None) -> StandingRoute:
    """Standing decision: outcome-shaped -> Job/Phase graph; else plain ReAct.

    CARD-230: outcome-shaped includes multi-step AND goal/deliverable language.
    Lazy-import avoids circular import with outcome_intake.
    """
    from src.application.orchestration.outcome_intake import is_outcome_shaped

    if is_outcome_shaped(text) or is_multi_step_outcome(text):
        return StandingRoute.MULTI_STEP_JOB_GRAPH
    return StandingRoute.SHORT_REACT
