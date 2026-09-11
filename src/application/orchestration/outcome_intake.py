"""Outcome intake for standing Chat → durable Job + testable success_rule [CARD-230].

Extends the standing Job/Phase path (215–229). Not a second orchestrator.
"""

from __future__ import annotations

import re
from typing import Sequence

from src.application.orchestration.standing_job_graph import is_multi_step_outcome

# Vibes-only phrases that must never become a standing success_rule.
_VIBES_ONLY = re.compile(
    r"^\s*(?:"
    r"looks?\s+good|seems?\s+(?:fine|good|ok|okay)|feels?\s+(?:right|good)|"
    r"good\s+enough|ship\s+it|lgtm|ok(?:ay)?|fine|nice|perfect|"
    r"vibes?(?:\s+only)?|whatever|n/?a"
    r")\s*[.!]*\s*$",
    re.IGNORECASE,
)

# Structured stop-condition markers the 216 verifier can fail against.
_TESTABLE_MARKERS = re.compile(
    r"(?:"
    r"\bdone\s+when\b|"
    r"\bwhen\s+.+\s+exists\b|"
    r"\btest\s+\S+\s+passes\b|"
    r"\bpytest\b|"
    r"\bhealth\b.+\b(?:returns?\s+)?200\b|"
    r"\breturns?\s+200\b|"
    r"\bHTTP\s*200\b|"
    r"\bassert\b|"
    r"\bverify(?:ied)?\b.+\b(?:pass|exist|200|ok)\b|"
    r"\bfile\s+\S+\s+exists\b|"
    r"\bexit(?:s|\s+code)\s+0\b"
    r")",
    re.IGNORECASE,
)

# Goal / deliverable language (beyond first/then multi-step).
# CARD-236: wiki/note write deliverables + hyphenated done-when always mint Jobs.
_GOAL_DELIVERABLE = re.compile(
    r"(?:"
    r"\b(?:deliver|delivery|deliverable)\b|"
    r"\b(?:build|create|produce|ship|implement|author|write|save|draft|add)\b.+\b(?:that|which|so\s+that|until|when)\b|"
    r"\b(?:create|write|author|save|draft|add)\b.+\b(?:wiki|note)s?\b|"
    r"\b(?:wiki|note)s?\b.+\b(?:create|write|author|save|draft)\b|"
    r"\bdone[\s-]+when\b|"
    r"\bsuccess\s+(?:when|criteria|rule|condition)\b|"
    r"\bprove(?:s|n)?\b.+\b(?:exists|passes|returns|200)\b|"
    r"\bhealth\b.+\b200\b|"
    r"\bacceptance\s+criteria\b"
    r")",
    re.IGNORECASE,
)


class OutcomeIntakeError(ValueError):
    """Fail-closed intake / phase-1 gate error [REQ-INTAKE-002, REQ-INTAKE-004]."""


def is_vibes_only_success_rule(rule: str | None) -> bool:
    if not rule or not isinstance(rule, str):
        return True
    trimmed = rule.strip()
    if not trimmed:
        return True
    if _VIBES_ONLY.match(trimmed):
        return True
    # Very short unstructured praise with no testable marker.
    if len(trimmed) < 12 and not _TESTABLE_MARKERS.search(trimmed):
        return True
    return False


def is_testable_success_rule(rule: str | None) -> bool:
    if not rule or not isinstance(rule, str):
        return False
    trimmed = rule.strip()
    if not trimmed or is_vibes_only_success_rule(trimmed):
        return False
    if _TESTABLE_MARKERS.search(trimmed):
        return True
    # Structured "done when …" style we synthesize is always testable enough.
    if trimmed.lower().startswith("done when"):
        return len(trimmed) >= 16
    return False


def is_outcome_shaped(text: str | None) -> bool:
    """Outcome-shaped = multi-step OR goal/deliverable language (not short chitchat)."""
    if not text or not isinstance(text, str):
        return False
    trimmed = text.strip()
    if len(trimmed) < 25:
        return False
    if is_multi_step_outcome(trimmed):
        return True
    if len(trimmed) >= 40 and _GOAL_DELIVERABLE.search(trimmed):
        return True
    return False


def derive_success_rule(intent: str, *, explicit: str | None = None) -> str:
    """
    Produce a testable stop condition for the Job [REQ-INTAKE-002].

    Explicit vibes-only → OutcomeIntakeError.
    Prefer structured clauses found in the ask; else synthesize `done when: …`.
    """
    if explicit is not None:
        candidate = str(explicit).strip()
        if is_vibes_only_success_rule(candidate):
            raise OutcomeIntakeError(
                f"success_rule rejected as vibes-only: {candidate!r}"
            )
        if is_testable_success_rule(candidate):
            return candidate
        # Non-vibes but unstructured: wrap into done-when form.
        return f"done when: {candidate}"

    text = (intent or "").strip()
    if not text:
        raise OutcomeIntakeError("cannot derive success_rule from empty intent")

    # Prefer an explicit clause already in the ask (space or hyphen done-when).
    m = re.search(
        r"(done[\s-]+when\s*[:\-]?\s*[^.;\n]+|health\b[^.;\n]*returns?\s+200|"
        r"test\s+\S+\s+passes|when\s+[^.;\n]+\s+exists)",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        clause = m.group(0).strip()
        # Normalize done-when / done when: → "done when ..."
        clause = re.sub(
            r"^done[\s-]+when\s*[:\-]?\s*",
            "done when ",
            clause,
            count=1,
            flags=re.IGNORECASE,
        )
        if not clause.lower().startswith("done when"):
            clause = f"done when {clause}"
        if is_vibes_only_success_rule(clause):
            raise OutcomeIntakeError(
                f"success_rule rejected as vibes-only: {clause!r}"
            )
        return clause

    # Synthesize a structured stop condition from the goal text.
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) > 180:
        compact = compact[:177].rstrip() + "..."
    synthesized = f"done when: outcome verified — {compact}"
    if is_vibes_only_success_rule(synthesized):
        raise OutcomeIntakeError(
            f"success_rule rejected as vibes-only: {synthesized!r}"
        )
    return synthesized


def matched_ids_authority(
    resolved_ids: Sequence[str],
    *,
    preferred_agent_id: str | None = None,
    widen_attempt: Sequence[str] | None = None,
) -> list[str]:
    """
    Matched catalog IDs are capability authority [REQ-INTAKE-003].

    preferred_agent_id is preference only (ignored for the subset).
    widen_attempt is never merged in.
    """
    _ = preferred_agent_id  # preference only — does not alter matched subset
    _ = widen_attempt
    return [str(x) for x in (resolved_ids or [])]


def assert_intake_ready_for_phase1(
    *,
    success_rule: str | None,
    matched_capability_ids: Sequence[str] | None,
) -> None:
    """Fail closed before phase 1 when intake fields are missing [REQ-INTAKE-004]."""
    rule = (success_rule or "").strip()
    ids = [str(x) for x in (matched_capability_ids or []) if str(x).strip()]
    if not rule:
        raise OutcomeIntakeError(
            "fail-closed: Job missing non-empty success_rule before phase 1"
        )
    if is_vibes_only_success_rule(rule) or not is_testable_success_rule(rule):
        raise OutcomeIntakeError(
            f"fail-closed: success_rule not testable before phase 1: {rule!r}"
        )
    if not ids:
        raise OutcomeIntakeError(
            "fail-closed: checkpoint missing matched_capability_ids before phase 1"
        )
