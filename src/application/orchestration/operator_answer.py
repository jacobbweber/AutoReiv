"""Operator Q&A durable notes for later job steps [CARD-619]."""

from __future__ import annotations

import re
from typing import Any, List, Optional

from src.application.orchestration.plain_question import ends_with_question

OPERATOR_ANSWER_PREFIX = "Jacob answered "
_ANSWER_NOTE_MAX = 800


def question_from_assistant_reply(text: str) -> str:
    """The last plain question in an assistant reply (ignores the waiting-for-answer note)."""
    raw = (text or "").strip()
    if not raw:
        return ""
    # Drop the standard waiting note if present.
    raw = re.sub(
        r"(?is)\n*The job is waiting for your answer\..*$",
        "",
        raw,
    ).strip()
    if ends_with_question(raw):
        # Prefer the last non-empty line that looks like a question.
        for line in reversed([ln.strip() for ln in raw.splitlines() if ln.strip()]):
            if ends_with_question(line) or line.endswith("?"):
                return line
        return raw
    # Fallback: last sentence ending in ?
    parts = re.split(r"(?<=[?])\s+", raw)
    for part in reversed(parts):
        part = part.strip()
        if part.endswith("?"):
            return part
    return ""


def format_operator_answer_note(question: str, answer: str, *, max_chars: int = _ANSWER_NOTE_MAX) -> str:
    """One durable line: ``Jacob answered <question>: <answer>`` [CARD-619]."""
    a = (answer or "").strip()
    if not a:
        return ""
    q = " ".join((question or "").strip().split())
    note = f"{OPERATOR_ANSWER_PREFIX}{q}: {a}" if q else f"{OPERATOR_ANSWER_PREFIX.rstrip()}: {a}"
    if len(note) > max_chars:
        note = note[: max_chars - 1].rstrip() + "…"
    return note


def last_assistant_content(store: Any, session_id: str) -> str:
    """Latest assistant message body in a session, or empty."""
    try:
        from src.domain.gateway.models import Role

        msgs = store.get_messages(session_id) or []
    except Exception:  # noqa: BLE001
        return ""
    for msg in reversed(msgs):
        if getattr(msg, "role", None) == Role.ASSISTANT and (msg.content or "").strip():
            return str(msg.content)
    return ""


def operator_answer_note_for_session(store: Any, session_id: str, answer: str) -> str:
    """Build the durable note from the waiting session's last question and Jacob's answer."""
    return format_operator_answer_note(question_from_assistant_reply(last_assistant_content(store, session_id)), answer)


def prepend_operator_answers(notes: Optional[List[str]], *answer_notes: str) -> List[str]:
    """Put answer notes ahead of other durable notes (later steps see them first)."""
    out: List[str] = []
    for n in answer_notes:
        n = (n or "").strip()
        if n and n not in out:
            out.append(n)
    for n in notes or []:
        n = (n or "").strip()
        if n and n not in out:
            out.append(n)
    return out
