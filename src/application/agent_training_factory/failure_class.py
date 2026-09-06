"""Domain-agnostic failure classification for Agent Training Factory rinses (CARD-172).

implementation -> inner rinse (Author)
sop_how        -> outer rinse (Intent Distill + Ground with Reflexion lessons)
"""

from __future__ import annotations

from typing import Iterable, List, Optional

FAILURE_IMPLEMENTATION = "implementation"
FAILURE_SOP_HOW = "sop_how"

# Keywords / phrases that signal how/SOP / medium misunderstanding (not product names).
_SOP_HOW_MARKERS = (
    "missing sop",
    "sop missing",
    "unknown procedure",
    "procedure missing",
    "medium misunderstanding",
    "wrong medium",
    "misunderstood medium",
    "misunderstanding",
    "operating manual",
    "official guidance",
    "professional sop",
    "runbook missing",
    "missing runbook",
    "wiki incomplete",
    "intent unclear",
    "how-to missing",
    "how to missing",
    "grounding gap",
    "not grounded",
    "scenario not grounded",
    "capability misunderstanding",
    "role misunderstanding",
)


def classify_failure(
    text: str,
    *,
    scenario_misses: Optional[Iterable[str]] = None,
) -> str:
    """Return FAILURE_SOP_HOW or FAILURE_IMPLEMENTATION from critic notes / misses."""
    blob = (text or "").strip().lower()
    misses: List[str] = [str(m).strip() for m in (scenario_misses or []) if str(m).strip()]
    if misses:
        miss_blob = " ".join(misses).lower()
        blob = f"{blob} {miss_blob}".strip()
        # Coverage gaps on procedural / SOP-shaped scenarios are how-class by default.
        procedural_hints = (
            "sop",
            "procedure",
            "medium",
            "professional",
            "guidance",
            "runbook",
            "unknown",
            "ground",
        )
        if any(h in miss_blob for h in procedural_hints):
            return FAILURE_SOP_HOW
    if not blob:
        return FAILURE_IMPLEMENTATION
    for marker in _SOP_HOW_MARKERS:
        if marker in blob:
            return FAILURE_SOP_HOW
    return FAILURE_IMPLEMENTATION


def decide_rinse_outcome(
    *,
    failure_class: str,
    verify_rinse_count: int,
    max_verify_rinses: int,
    outer_rinse_count: int,
    max_outer_rinses: int,
) -> str:
    """Map failure class + caps to registry outcomes: fail | outer | exhausted."""
    if failure_class == FAILURE_SOP_HOW:
        next_outer = int(outer_rinse_count or 0) + 1
        if next_outer >= int(max_outer_rinses or 2):
            return "exhausted"
        return "outer"
    next_inner = int(verify_rinse_count or 0) + 1
    if next_inner >= int(max_verify_rinses or 3):
        return "exhausted"
    return "fail"
