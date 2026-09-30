"""Quiz engine: Wiki-sourced items + binary external grade (not LLM) [CARD-242]."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List

_QA_BULLET_RE = re.compile(
    r"^[-\*]\s*Q:\s*(?P<q>.+?)\s*(?:\n|\r\n)[ \t]*A:\s*(?P<a>.+?)\s*(?=(?:\n|\r\n)[-\*]|\n##|\Z)",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
_QA_INLINE_RE = re.compile(
    r"^[-\*]\s*Q:\s*(?P<q>[^\n]+?)\s+[—\-–]\s*A:\s*(?P<a>[^\n]+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# CARD-583: the shipped education-quiz template writes items as
# "- **Prompt:** ..." followed by "- **Expected Binary Answer:** ..." (bold optional).
_QA_TEMPLATE_RE = re.compile(
    r"^[-\*]\s*\**Prompt\**:\**\s*(?P<q>[^\n]+?)\s*\n[ \t]*[-\*]\s*\**Expected(?:\s+Binary)?\s+Answer\**:\**\s*(?P<a>[^\n]+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_PLACEHOLDER_RE = re.compile(r"^\[[^\]]*\]$")


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

    for rx in (_QA_INLINE_RE, _QA_BULLET_RE, _QA_TEMPLATE_RE):
        for match in rx.finditer(quiz_section):
            q = (match.group("q") or "").strip()
            a = (match.group("a") or "").strip()
            # Collapse multiline answers to single line for storage
            a = re.sub(r"\s+", " ", a).strip()
            q = re.sub(r"\s+", " ", q).strip()
            if not q or not a or _PLACEHOLDER_RE.match(q) or _PLACEHOLDER_RE.match(a):
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


# CARD-587: definition lines in a plain note ("- **Term**: meaning", "Term: meaning", "Term - meaning").
_DEF_BOLD_RE = re.compile(r"^\s*(?:[-\*]\s+)?\*\*(?P<term>[^*\n]{1,60}?)\*\*\s*(?::|\s[-\u2013\u2014]\s)\s*(?P<d>[^\n]{8,300})$")
_DEF_PLAIN_RE = re.compile(r"^\s*[-\*]\s+(?P<term>[^:\n*`]{1,50}?)\s*(?::|\s[-\u2013\u2014]\s)\s*(?P<d>[^\n]{8,300})$")
MAX_SUGGESTED_ITEMS = 10


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4 :]
    return text


def suggest_quiz_items_from_note(content: str, *, limit: int = MAX_SUGGESTED_ITEMS) -> List[Dict[str, str]]:
    """CARD-587: suggest recall questions from a plain note's definition lines.

    The grader is exact (normalized) string equality, so each question asks for the short term and the answer is the
    term itself: "Which term matches: <meaning>?" -> "<term>". Returns [] for prose without definitions; the agent
    then writes its own questions (education_quiz_extract questions=[...]).
    """
    out: List[Dict[str, str]] = []
    seen: set[str] = set()
    for line in _strip_frontmatter(content or "").splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = _DEF_BOLD_RE.match(line) or _DEF_PLAIN_RE.match(line)
        if not m:
            continue
        term = m.group("term").strip().strip("`*_ ").rstrip(":")
        meaning = re.sub(r"\s+", " ", m.group("d")).strip().rstrip(".")
        if not term or len(term.split()) > 6 or len(meaning.split()) < 3 or re.match(r"^(https?|Q|A)$", term, re.I):
            continue
        if _PLACEHOLDER_RE.match(term) or term.casefold() in seen:
            continue
        seen.add(term.casefold())
        out.append({"prompt": f"Which term matches this description: {meaning}?", "answer": term})
        if len(out) >= limit:
            break
    return out


def quiz_note_path_for(source_path: str) -> str:
    """CARD-587: the separate quiz note next to its source (``01_Notes/k8s/basics.md`` -> ``01_Notes/k8s/basics-quiz.md``)."""
    src = (source_path or "").replace("\\", "/").strip().strip("/")
    stem, dot, ext = src.rpartition(".")
    if not dot or "/" in ext:
        stem, ext = src, "md"
    return f"{stem}-quiz.{ext or 'md'}"


def render_quiz_note(*, title: str, source_path: str, items: List[Dict[str, str]]) -> str:
    """CARD-587: quiz note body in the shipped education-quiz template format (what extraction reads)."""
    lines = [
        f"# Quiz: {title}",
        "",
        f"> **Topic:** {title}",
        f"> **Source note:** [[{source_path}]] (not edited; questions live here)",
        "> **Pedagogy Phase:** Retrieval Practice (Active Recall)",
        "",
        "---",
        "",
        "## 1. Active Recall Questions",
    ]
    for n, it in enumerate(items, start=1):
        lines += [
            f"### Item {n}",
            f"- **Prompt:** {it['prompt']}",
            f"- **Expected Binary Answer:** {it['answer']}",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


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
