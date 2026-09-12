"""Quiz engine: Wiki-sourced items + binary external grade (not LLM) [CARD-242]."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional

_QA_BULLET_RE = re.compile(
    r"^[-\*]\s*Q:\s*(?P<q>.+?)\s*(?:\n|\r\n)[ \t]*A:\s*(?P<a>.+?)\s*(?=(?:\n|\r\n)[-\*]|\n##|\Z)",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
_QA_INLINE_RE = re.compile(
    r"^[-\*]\s*Q:\s*(?P<q>[^\n]+?)\s+[—\-–]\s*A:\s*(?P<a>[^\n]+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _normalize_answer(text: str) -> str:
    s = (text or "").strip().casefold()
    s = re.sub(r"\s+", " ", s)
    s = s.strip(" .,;:!?\"'`")
    return s


def grade_answer_binary(expected: str, given: str) -> bool:
    """Binary external grade via normalized string equality. No LLM self-score."""
    exp = _normalize_answer(expected)
    got = _normalize_answer(given)
    if not exp:
        return False
    return exp == got


def _item_id_for(wiki_path: str, prompt: str) -> str:
    digest = hashlib.sha1(f"{wiki_path}|{prompt}".encode("utf-8")).hexdigest()[:12]
    return f"edu_{digest}"


def extract_quiz_items_from_note(
    content: str,
    *,
    wiki_path: str,
    topic: str = "",
) -> List[Dict[str, Any]]:
    """Extract Q/A quiz items from a Priming / Dual Coding Wiki note body.

    Looks for a Quiz section with `- Q: ... / A: ...` bullets (or inline Q — A).
    """
    text = content or ""
    # Prefer content under ## Quiz if present
    quiz_section = text
    m = re.search(r"^##\s+Quiz\s*$", text, re.IGNORECASE | re.MULTILINE)
    if m:
        rest = text[m.end() :]
        nxt = re.search(r"^##\s+\S", rest, re.MULTILINE)
        quiz_section = rest[: nxt.start()] if nxt else rest

    items: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for rx in (_QA_INLINE_RE, _QA_BULLET_RE):
        for match in rx.finditer(quiz_section):
            q = (match.group("q") or "").strip()
            a = (match.group("a") or "").strip()
            # Collapse multiline answers to single line for storage
            a = re.sub(r"\s+", " ", a).strip()
            q = re.sub(r"\s+", " ", q).strip()
            if not q or not a:
                continue
            iid = _item_id_for(wiki_path, q)
            if iid in seen:
                continue
            seen.add(iid)
            items.append(
                {
                    "item_id": iid,
                    "topic": topic or wiki_path,
                    "wiki_path": wiki_path,
                    "prompt": q,
                    "expected_answer": a,
                }
            )
    return items


def build_review_job_intent(item: Dict[str, Any]) -> str:
    """Outcome-shaped standing ask for a due Education review Job."""
    topic = item.get("topic") or "Education"
    prompt = item.get("prompt") or ""
    path = item.get("wiki_path") or ""
    iid = item.get("item_id") or ""
    return (
        f"[Education Studio] [Mode: Retrieval Review] Resurface quiz review for item {iid} "
        f'on topic "{topic}" (Wiki: {path}). '
        f"Prompt the learner with: {prompt}. "
        "Do not invent a chat-only toast or remind-me-later — this is a standing Job. "
        "Use only wiki_note_search/wiki_note_read when grounding (never wiki_overview). "
        f'Done-when: the learner has attempted the review for "{topic}" item {iid}.'
    )
