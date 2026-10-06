"""Education Learning OS — Construction & Application Labs with Graded Pressure [CARD-324].

Grades a lab submission against the criteria of a grounded lab (each criterion needs real
coverage of its key terms, CARD-649), issues verification receipts and formats the lab note.
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
    "from", "after", "before", "when", "then", "into", "onto", "not",
})


_WORD = re.compile(r"[a-z][a-z0-9\-]{2,}")
_MIN_OWN_WORDS = 3  # distinct words of the learner's own beyond the criteria's terms


def _stem(word: str) -> str:
    return word[:5]


def _key_terms(text: str) -> List[str]:
    """Distinct significant words of a criterion, in order."""
    from src.application.education.grounded import words

    seen: List[str] = []
    for w in words(text):
        if w in _STOP_WORDS or w in seen:
            continue
        seen.append(w)
    return seen


def _stems(text: str) -> set:
    from src.application.education.grounded import words

    return {_stem(w) for w in words(text) if w not in _STOP_WORDS}


def _needed(term_count: int) -> int:
    """Generous but not trivial: half the terms, rounded up, and at least two when there are two."""
    return max(min(2, term_count), (term_count + 1) // 2)


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

    # CARD-649: a criterion needs meaningful coverage, not one shared word. About half of its key terms
    # (at least two when it has two or more) must appear in the submission, matched across word forms.
    sub_stems = _stems(sub)
    passed_invariants: List[str] = []
    failed_invariants: List[str] = []
    missing_terms: Dict[str, List[str]] = {}

    for inv in invariants:
        terms = _key_terms(inv)
        if not terms:
            failed_invariants.append(inv)
            missing_terms[inv] = []
            continue
        hit = [w for w in terms if _stem(w) in sub_stems]
        if len(hit) >= _needed(len(terms)):
            passed_invariants.append(inv)
        else:
            failed_invariants.append(inv)
            missing_terms[inv] = [w for w in terms if w not in hit]

    criteria_stems = set().union(*(_stems(i) for i in invariants))
    own_words = sub_stems - criteria_stems
    if len(own_words) < _MIN_OWN_WORDS:
        return {
            "passed": False,
            "score": 0.0,
            "passed_invariants": [],
            "failed_invariants": list(invariants),
            "feedback": "This repeats the criteria instead of describing what you built. "
            "Explain your lab in your own words.",
            "receipt": {
                "status": "Failed",
                "score": 0.0,
                "timestamp": stamp,
                "step": step_clean,
                "topic": topic_clean,
            },
        }

    # Graded pressure threshold: must pass all invariants and have substance
    passed = len(failed_invariants) == 0 and len(sub) >= 40
    score = 1.0 if passed else 0.0
    feedback = (
        "All criteria covered. Graded 1.0."
        if passed
        else "Not every criterion is covered yet. "
        + " ".join(
            f"\"{inv}\"" + (f" (mention: {', '.join(missing_terms.get(inv) or [])})" if missing_terms.get(inv) else "")
            for inv in failed_invariants
        )
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
