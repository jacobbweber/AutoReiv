"""Education Learning OS — Construction & Application Labs with Graded Pressure [CARD-324].

Provides lab specification generation, objective invariant-based grading,
verification receipts, and Wiki artifact formatting using the education-lab template.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by", "of",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "shall", "will", "should", "would", "may", "might", "must", "can", "could",
    "it", "its", "this", "that", "these", "those", "we", "you", "they", "i", "he", "she",
    "1", "2", "3", "4", "5", "invariant", "task", "step", "must", "only", "all", "each",
})


def grade_lab_submission(
    *,
    topic: str,
    step: str = "construction",
    submission: str,
    expected_invariants: Optional[Sequence[str]] = None,
    verification_criteria: Optional[Sequence[str]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Evaluate learner lab submission with graded pressure (no LLM self-score theatre)."""
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    stamp = base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sub = (submission or "").strip()
    topic_clean = (topic or "").strip()
    step_clean = (step or "construction").strip().lower()

    # Empty or trivial text rejects immediately
    trivial_patterns = [
        r"^i\s+don'?t\s+know",
        r"^todo",
        r"^tbd",
        r"^\?+",
        r"^na$",
        r"^none$",
    ]
    is_trivial = any(re.search(pat, sub, re.IGNORECASE) for pat in trivial_patterns)
    invariants = [str(i) for i in (expected_invariants or verification_criteria or []) if str(i).strip()]
    if not sub or len(sub) < 30 or is_trivial or not invariants:
        invars = list(invariants)
        feedback = (
            "There are no criteria from your notes to grade this lab against, so it is not graded."
            if not invariants
            else "Submission is incomplete or lacks substantive verification evidence. "
            "All required criteria must be addressed."
        )
        return {
            "passed": False,
            "score": 0.0,
            "passed_invariants": [],
            "failed_invariants": invars,
            "feedback": feedback,
            "receipt": {
                "status": "Failed",
                "score": 0.0,
                "timestamp": stamp,
                "step": step_clean,
                "topic": topic_clean,
            },
        }

    sub_lower = sub.lower()
    passed_invariants: List[str] = []
    failed_invariants: List[str] = []

    for inv in invariants:
        # Extract meaningful concept keywords from invariant
        words = [
            w.lower()
            for w in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", inv)
            if w.lower() not in _STOP_WORDS
        ]
        # An invariant passes if at least 1 significant key phrase/concept from it appears in the submission
        matched = any(w in sub_lower for w in words)

        if matched:
            passed_invariants.append(inv)
        else:
            failed_invariants.append(inv)

    # Graded pressure threshold: must pass all invariants and have substance
    passed = len(failed_invariants) == 0 and len(sub) >= 40
    score = 1.0 if passed else 0.0
    feedback = (
        "All verification criteria and invariants satisfied. Graded 1.0."
        if passed
        else f"Verification failed. Missing required invariants: {'; '.join(failed_invariants)}."
    )

    return {
        "passed": passed,
        "score": score,
        "passed_invariants": passed_invariants,
        "failed_invariants": failed_invariants,
        "feedback": feedback,
        "receipt": {
            "status": "Passed" if passed else "Failed",
            "score": score,
            "timestamp": stamp,
            "step": step_clean,
            "topic": topic_clean,
        },
    }


def _wikilink(path: str) -> str:
    p = str(path or "").strip()
    return p[:-3] if p.endswith(".md") else p


def build_lab_note_content(
    *,
    topic: str,
    step: str = "construction",
    lab_spec: Optional[Dict[str, Any]] = None,
    submission: Optional[str] = None,
    grade_result: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> str:
    """Lab note from a lab grounded in the learner's notes and/or the learner's own submission [CARD-643].

    `lab_spec` comes from `grounded_steps.compose_step_content(..., "construction"|"application")`.
    There is no template lab: without a grounded spec the note holds only the learner's submission.
    """
    topic_clean = (topic or "").strip()
    step_clean = (step or "construction").strip().lower()
    parts: List[str] = [f"# Lab: {step_clean.title()} — {topic_clean}", ""]
    spec = lab_spec if (lab_spec or {}).get("ok") else None
    if spec:
        parts += ["## Objective", str(spec.get("objective") or ""), ""]
        parts += ["## Tasks", *(f"{i}. {t}" for i, t in enumerate(spec.get("tasks") or [], start=1)), ""]
        parts += ["## What a correct submission covers", *(f"- {c}" for c in spec.get("criteria") or []), ""]
        sources = [x for x in (spec.get("sources") or []) if isinstance(x, dict) and x.get("path")]
        if sources:
            parts += ["## Sources", *(f"- [[{_wikilink(x['path'])}]] {x.get('title') or ''}".rstrip() for x in sources), ""]
        parts += ["## Quiz", f"Q: {spec['question']}", f"A: {spec['answer']}", ""]
    sub = (submission or "").strip()
    if sub:
        parts += ["## Your submission", "```text", sub, "```", ""]
    if grade_result:
        base = now or datetime.now(timezone.utc)
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)
        stamp = base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        status = "Passed" if grade_result.get("passed") else "Failed"
        parts += [
            "## Result",
            f"- **Status:** {status}",
            f"- **Score:** {grade_result.get('score', 0.0)}",
            f"- **Graded At:** {stamp}",
            f"- **Feedback:** {grade_result.get('feedback', '')}",
            "",
        ]
    elif sub:
        parts += ["Not graded: there were no criteria from your notes to grade it against.", ""]
    return "\n".join(parts)
