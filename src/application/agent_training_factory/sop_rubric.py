"""Generic SOP structure rubric for Intent Distill / Ground (domain-agnostic)."""

from __future__ import annotations

import re
from typing import Iterable

_PURPOSE = ("purpose", "objective", "intent", "goal")
_STEPS = ("step", "procedure", "workflow", "how to", "actions", "sequence")
_VERIFY = ("verif", "done-when", "done when", "confirm", "validate", "check that", "acceptance")
_ROLLBACK = ("rollback", "undo", "recover", "revert", "back out", "restore prior")


def _has_any(text: str, markers: Iterable[str]) -> bool:
    low = text.lower()
    return any(m in low for m in markers)


def sop_is_structured(text: str) -> bool:
    """True when text covers purpose, steps, verify, and rollback as distinct sections."""
    body = (text or "").strip()
    if len(body) < 120:
        return False
    # Require heading-like section markers so a one-line keyword list cannot pass.
    heading = re.compile(r"(?m)^\s{0,3}#{1,3}\s*", re.I)
    labeled = re.compile(
        r"(?i)(?:^|\n)\s*(?:#{1,3}\s*)?(?:purpose|objectives?|steps?|procedure|verify|verification|rollback)\b"
    )
    labels = labeled.findall(body)
    if len(set(x.strip().lower().lstrip("# ").split()[0] for x in labels if x.strip())) >= 4:
        return True
    # Fallback: four keyword families AND at least two markdown headings
    if heading.findall(body) and len(heading.findall(body)) >= 2:
        return (
            _has_any(body, _PURPOSE)
            and _has_any(body, _STEPS)
            and _has_any(body, _VERIFY)
            and _has_any(body, _ROLLBACK)
            and "\n" in body
        )
    return False


def looks_like_brief_echo(text: str, seed_intent: str) -> bool:
    """Vacuous when mostly restates the brief without operational structure."""
    body = (text or "").strip()
    seed = (seed_intent or "").strip()
    if not body:
        return True
    if sop_is_structured(body):
        return False
    if seed and seed[:48].lower() in body.lower() and len(body) < max(160, len(seed) + 80):
        return True
    # Classic Factory theater phrase is always vacuous echo.
    if re.search(r"a professional sop for this role covers:", body, re.I):
        return True
    return not sop_is_structured(body)


def ensure_structured_sop(text: str, *, seed_intent: str, objectives: list | None = None, title: str = "Role") -> str:
    """Return text if structured; otherwise a generic structured SOP scaffold."""
    if sop_is_structured(text) and not looks_like_brief_echo(text, seed_intent):
        return text
    objs = [str(o) for o in (objectives or []) if str(o).strip()]
    obj_lines = "\n".join(f"- {o}" for o in objs) if objs else f"- Achieve: {seed_intent}"
    return (
        f"## Purpose\n{seed_intent or title}\n\n"
        f"## Objectives\n{obj_lines}\n\n"
        f"## Steps\n"
        f"1. Confirm prerequisites and target medium access.\n"
        f"2. Execute the brief actions against the live medium.\n"
        f"3. Capture outputs needed for verification.\n\n"
        f"## Verify\n"
        f"- Each DONE-WHEN / objective is demonstrably true on the medium.\n"
        f"- No out-of-scope capabilities were exercised.\n\n"
        f"## Rollback\n"
        f"- Undo the last mutating action when safe (delete/remove/restore prior state).\n"
        f"- Record what changed and stop if approval is required.\n"
    )
