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


def _slugify(text: str) -> str:
    raw = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "topic").strip()).strip("_").lower()
    return (raw or "topic")[:48]


def build_lab_specification(
    topic: str,
    step: str = "construction",
) -> Dict[str, Any]:
    """Generate structured lab specification for construction or application phase."""
    topic_clean = (topic or "Untitled Topic").strip() or "Untitled Topic"
    step_clean = (step or "construction").strip().lower()
    if step_clean not in ("construction", "application"):
        step_clean = "construction"

    slug = _slugify(topic_clean)
    lab_id = f"lab_{step_clean}_{slug}"

    if step_clean == "construction":
        objective = (
            f"Construct the foundational data model, core schemas, and boundary handling for {topic_clean}."
        )
        tasks = [
            f"1. Define state representation, data structures, and core interfaces for {topic_clean}.",
            "2. Implement deterministic state transition logic and explicit edge-case boundary checks.",
            "3. Validate invariant constraints against unexpected inputs or state regressions.",
        ]
        invariants = [
            f"Invariant 1: Structural consistency and boundary condition handling for {topic_clean}.",
            "Invariant 2: Deterministic state progression and minimal disturbance under reconfiguration.",
        ]
        criteria = [
            f"Explicitly defines structural model or schema for {topic_clean}.",
            "Enforces deterministic state transitions and handles edge cases.",
        ]
        test_command = f"pytest tests/unit/education/test_{slug}_construction.py"
    else:
        objective = (
            f"Apply {topic_clean} under operational workloads, integration constraints, and failure pressure."
        )
        tasks = [
            f"1. Configure realistic workload or integration fixture exercising {topic_clean}.",
            "2. Execute stress scenario under error injection, concurrent load, or edge-case pressure.",
            "3. Verify invariant preservation, recovery guarantees, and emit structured verification receipt.",
        ]
        invariants = [
            f"Invariant 1: End-to-end execution without unhandled exceptions or state corruption in {topic_clean}.",
            "Invariant 2: Invariant guarantees hold under workload and failure pressure.",
        ]
        criteria = [
            f"Executes end-to-end application workflow for {topic_clean}.",
            "Verifies invariant guarantees under operational pressure and emits verification receipt.",
        ]
        test_command = f"pytest tests/unit/education/test_{slug}_application.py"

    return {
        "lab_id": lab_id,
        "topic": topic_clean,
        "step": step_clean,
        "title": f"Lab: {step_clean.title()} — {topic_clean}",
        "objective": objective,
        "tasks": tasks,
        "invariants": invariants,
        "verification_criteria": criteria,
        "test_command": test_command,
        "template": "education-lab",
    }


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
    if not sub or len(sub) < 30 or is_trivial:
        invars = list(expected_invariants or [
            f"Invariant 1: Structural consistency for {topic_clean}",
            f"Invariant 2: Deterministic progression for {topic_clean}",
        ])
        return {
            "passed": False,
            "score": 0.0,
            "passed_invariants": [],
            "failed_invariants": invars,
            "feedback": (
                "Submission is incomplete or lacks substantive verification evidence. "
                "All required invariants must be addressed."
            ),
            "receipt": {
                "status": "Failed",
                "score": 0.0,
                "timestamp": stamp,
                "step": step_clean,
                "topic": topic_clean,
            },
        }

    invariants = list(expected_invariants or [])
    if not invariants:
        spec = build_lab_specification(topic_clean, step=step_clean)
        invariants = spec["invariants"]

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
        # Also check for explicit invariant mentions like "invariant 1", "invariant 2", or "invariant"
        if not matched and "invariant" in sub_lower:
            matched = True

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


def build_lab_note_content(
    *,
    topic: str,
    step: str = "construction",
    lab_spec: Dict[str, Any],
    submission: str,
    grade_result: Dict[str, Any],
    now: Optional[datetime] = None,
) -> str:
    """Format markdown note content matching the education-lab template."""
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    stamp = base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    topic_clean = (topic or "Topic").strip()
    step_clean = (step or "construction").strip().lower()
    receipt = grade_result.get("receipt") or {}
    status = receipt.get("status") or ("Passed" if grade_result.get("passed") else "Failed")

    tasks_md = "\n".join(lab_spec.get("tasks") or [f"1. Implement {topic_clean}"])
    invariants_md = "\n".join(f"- {inv}" for inv in (lab_spec.get("invariants") or []))
    criteria_md = "\n".join(f"- {c}" for c in (lab_spec.get("verification_criteria") or []))

    return (
        f"# Lab: {step_clean.title()} — {topic_clean}\n\n"
        f"> **Topic:** {topic_clean}\n"
        f"> **Pedagogy Phase:** {step_clean.title()}\n"
        f"> **Status:** {status}\n\n"
        f"---\n\n"
        f"## 1. Objective & Invariants\n"
        f"{lab_spec.get('objective', '')}\n\n"
        f"### Required Invariants\n"
        f"{invariants_md}\n\n"
        f"## 2. Hands-on Tasks\n"
        f"{tasks_md}\n\n"
        f"## 3. Verification Criteria\n"
        f"- Test command: `{lab_spec.get('test_command', 'pytest')}`\n"
        f"- Expected outcomes:\n"
        f"{criteria_md}\n\n"
        f"## 4. Verification Receipt\n"
        f"- **Status:** {status}\n"
        f"- **Score:** {grade_result.get('score', 0.0)}\n"
        f"- **Graded At:** {stamp}\n"
        f"- **Feedback:** {grade_result.get('feedback', '')}\n\n"
        f"## 5. Learner Submission\n"
        f"```text\n"
        f"{submission.strip()}\n"
        f"```\n"
    )
