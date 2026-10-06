"""Grounded dual coding for the course pipeline [CARD-640].

The dual coding step pairs a short explanation with a Mermaid diagram. It is built only from the
learner's own wiki notes on the topic, through one model call, and checked against those notes.
When there are no notes on the topic, no model, a model error, or a reply that is not grounded in
the notes, the step writes nothing and says why. There is no fallback template.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_SOURCES = 3
EXCERPT_CHARS = 2500

_STOP = frozenset(
    "the and for with that this from into onto over under about your their there them they then than "
    "when what which while where who whom whose why how are was were been being have has had does did "
    "doing can could should would will shall may might must not but also each every some any all its "
    "it's our ours you yours his her hers him she he we us very more most less least such only own same "
    "other another just one two three four five first second step steps topic course note notes".split()
)
_WORD = re.compile(r"[a-z][a-z0-9\-]{2,}")
_GENERATED_TITLE = re.compile(r"^\s*(course\b|priming\s*:|dual coding\b)", re.IGNORECASE)
_GENERATED_TAGS = frozenset({"course", "priming"})
_BANNED = (
    "two representations used in dual coding",
    "verbal prose and visual diagrams",
    "key concepts & invariants",
    "concrete implementation flow",
    "verified mastery & application",
)

SYSTEM_PROMPT = (
    "You turn a learner's own notes into a dual coding study aid. Use ONLY facts stated in the notes. "
    "Do not add outside knowledge and do not write generic study advice. Reply with one JSON object and "
    "nothing else, with these keys: "
    '"prose" (2 to 4 sentences explaining the topic using the notes), '
    '"mermaid" (a Mermaid flowchart starting with "flowchart TD", 4 to 8 boxes whose labels are concrete '
    "terms from the notes), "
    '"steps" (3 to 5 short strings walking through the diagram), '
    '"question" (one question a learner can answer from the notes), '
    '"answer" (the short answer, taken from the notes).'
)


def _words(text: str) -> List[str]:
    return [w for w in _WORD.findall((text or "").lower()) if w not in _STOP]


def _stem(word: str) -> str:
    return word[:5]


def topic_keywords(topic: str) -> List[str]:
    return [w for w in _words(topic) if len(w) >= 3]


def _is_generated(title: str, tags: Any) -> bool:
    tag_set = {str(t).strip().lower() for t in (tags or []) if str(t).strip()}
    return bool(_GENERATED_TITLE.match(title or "")) or bool(tag_set & _GENERATED_TAGS)


def _mentions_topic(text: str, topic: str) -> bool:
    low = (text or "").lower()
    phrase = (topic or "").strip().lower()
    if phrase and phrase in low:
        return True
    keys = topic_keywords(topic)
    if not keys:
        return False
    stems = {_stem(w) for w in _words(low)}
    return all(_stem(k) in stems for k in keys)


def find_dual_coding_sources(wiki_tools: Any, topic: str, limit: int = MAX_SOURCES) -> List[Dict[str, Any]]:
    """The learner's own wiki notes that are about `topic` (course- and priming-written notes excluded)."""
    topic = (topic or "").strip()
    if not topic or wiki_tools is None:
        return []
    try:
        if hasattr(wiki_tools, "search_wiki_notes"):
            hits = wiki_tools.search_wiki_notes(topic, limit=12)
        elif hasattr(wiki_tools, "search_notes"):
            hits = wiki_tools.search_notes(topic, limit=12)
        else:
            return []
    except Exception as exc:  # noqa: BLE001 - a broken search means no sources, never a template
        logger.info("dual coding source search failed: %s", exc)
        return []
    if isinstance(hits, dict):
        hits = hits.get("results") or hits.get("hits") or hits.get("notes") or []
    sources: List[Dict[str, Any]] = []
    for hit in hits or []:
        if not isinstance(hit, dict):
            continue
        path = str(hit.get("path") or "").replace("\\", "/")
        title = str(hit.get("title") or "")
        if not path or _is_generated(title, hit.get("tags")):
            continue
        try:
            note = wiki_tools.read_wiki_note(path) if hasattr(wiki_tools, "read_wiki_note") else wiki_tools.read_note(path)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(note, dict) or not note.get("success", True):
            continue
        meta = note.get("meta") or {}
        title = str(note.get("title") or meta.get("title") or title)
        if _is_generated(title, meta.get("tags") or hit.get("tags")):
            continue
        body = str(note.get("content") or "")
        if not body.strip() or not _mentions_topic(f"{title}\n{body}", topic):
            continue
        sources.append({"path": path, "title": title or path, "text": body[:EXCERPT_CHARS]})
        if len(sources) >= limit:
            break
    return sources


def _parse_reply(text: str) -> Optional[Dict[str, Any]]:
    raw = re.sub(r"<think>.*?(</think>|$)", "", str(text or ""), flags=re.S | re.I).strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.S)
    candidate = fenced.group(1) if fenced else raw[raw.find("{") : raw.rfind("}") + 1] if "{" in raw else ""
    if not candidate:
        return None
    try:
        data = json.loads(candidate)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _clean_mermaid(text: str) -> str:
    body = re.sub(r"^```(?:mermaid)?\s*|\s*```$", "", str(text or "").strip())
    return body.strip()


_LABEL = re.compile(r"[\[\(\{]+\"?([^\[\]\(\)\{\}\"]+)\"?[\]\)\}]+")


def _grounded(text: str, vocab: set, topic_stems: set) -> int:
    """How many distinct non-topic words in `text` also appear in the source notes."""
    return len({_stem(w) for w in _words(text) if len(w) >= 4} & vocab - topic_stems)


def validate_dual_coding(payload: Dict[str, Any], sources: List[Dict[str, Any]], topic: str) -> Optional[str]:
    """Return why `payload` is not grounded in `sources`, or None when it is."""
    prose = str(payload.get("prose") or "").strip()
    mermaid = _clean_mermaid(payload.get("mermaid") or "")
    question = str(payload.get("question") or "").strip()
    answer = str(payload.get("answer") or "").strip()
    blob = " ".join([prose, mermaid, question, answer]).lower()
    if any(b in blob for b in _BANNED):
        return "generic template text"
    if len(prose) < 40 or not question or not answer:
        return "missing explanation, question or answer"
    first = mermaid.splitlines()[0].strip().lower() if mermaid else ""
    if not (first.startswith("flowchart") or first.startswith("graph")):
        return "diagram is not a Mermaid flowchart"
    labels = [lab.strip() for lab in _LABEL.findall(mermaid) if lab.strip()]
    if len(labels) < 3:
        return "diagram has fewer than three boxes"
    vocab = {_stem(w) for s in sources for w in _words(f"{s.get('title', '')} {s.get('text', '')}") if len(w) >= 4}
    topic_stems = {_stem(w) for w in topic_keywords(topic)}
    grounded_labels = sum(1 for lab in labels if _grounded(lab, vocab, topic_stems) >= 1)
    if grounded_labels * 2 < len(labels):
        return "diagram boxes are not taken from the notes"
    if _grounded(prose, vocab, topic_stems) < 3:
        return "explanation is not taken from the notes"
    if _grounded(answer, vocab, topic_stems) < 1:
        return "answer is not taken from the notes"
    return None


def _skip(topic: str, reason: str, sources: Optional[List[Dict[str, Any]]] = None, detail: str = "") -> Dict[str, Any]:
    return {
        "ok": False,
        "topic": topic,
        "skip_reason": reason,
        "detail": detail,
        "sources": [{"path": s["path"], "title": s["title"]} for s in (sources or [])],
    }


async def compose_dual_coding(
    gateway: Any,
    wiki_tools: Any,
    topic: str,
    *,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """Build grounded dual coding content for `topic`, or a skip with its reason (never a template)."""
    topic = (topic or "").strip()
    sources = find_dual_coding_sources(wiki_tools, topic)
    if not sources:
        return _skip(topic, "no_wiki_notes")
    if gateway is None:
        return _skip(topic, "model_unavailable", sources, "no model gateway")

    from src.application.kernel.reply_limits import helper_call_seconds
    from src.domain.gateway.models import ChatMessage, CompletionRequest, Role

    notes_block = "\n\n".join(f"### Note: {s['title']} ({s['path']})\n{s['text']}" for s in sources)
    user = f"Topic: {topic}\n\nThe learner's notes:\n\n{notes_block}\n\nReturn the JSON object now."
    try:
        req = CompletionRequest(
            model=model or getattr(gateway, "default_model_id", None) or "default",
            messages=[
                ChatMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT),
                ChatMessage(role=Role.USER, content=user),
            ],
            temperature=0.2,
            max_tokens=1500,
            think=False,
            background=True,
        )
        resp = await asyncio.wait_for(gateway.complete(req), timeout=timeout or helper_call_seconds())
        text = getattr(resp, "text", None) or ""
    except Exception as exc:  # noqa: BLE001 - no model answer means the step writes nothing
        logger.warning("dual coding model call failed: %s", exc)
        return _skip(topic, "model_unavailable", sources, str(exc)[:200])

    data = _parse_reply(text)
    if data is None:
        return _skip(topic, "model_output_invalid", sources, "reply was not a JSON object")
    problem = validate_dual_coding(data, sources, topic)
    if problem:
        return _skip(topic, "model_output_invalid", sources, problem)
    steps = [str(s).strip() for s in (data.get("steps") or []) if str(s).strip()][:6]
    return {
        "ok": True,
        "topic": topic,
        "skip_reason": None,
        "prose": str(data["prose"]).strip(),
        "mermaid": _clean_mermaid(data["mermaid"]),
        "steps": steps,
        "question": str(data["question"]).strip(),
        "answer": str(data["answer"]).strip(),
        "sources": [{"path": s["path"], "title": s["title"]} for s in sources],
        "model": getattr(req, "model", None),
    }
