"""Shared grounding helpers for course steps built from the learner's own wiki notes [CARD-640, CARD-646].

A grounded course step reads the learner's notes on the topic, makes one call to the configured
model for a JSON object, and checks the reply against those notes. When there are no notes on the
topic, no model, a model error, or a reply that is not grounded in the notes, the step writes nothing
and says why. There is no fallback template.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, Iterable, List, Optional

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

# Phrases from the retired per-topic templates. A reply that repeats any of them is refused.
BANNED_TEMPLATE_PHRASES = (
    # dual coding [CARD-640]
    "two representations used in dual coding",
    "verbal prose and visual diagrams",
    "key concepts & invariants",
    "concrete implementation flow",
    "verified mastery & application",
    # priming [CARD-646]
    "durable concept learned via priming",
    "outline + prerequisites + goals",
    "wiki schema/outline note",
    "memory.db ledger anchors",
    "priming schema outline",
    "why it matters (autoreiv",
    "key parts / moving pieces",
    # elaboration [CARD-644]
    "learner self-explanation to be added",
    "guarantees correct state progression through disciplined coordination",
    "intuitive mental model illustrating",
    "flawed design or antipattern violating",
    # labs [CARD-643]
    "structural consistency and boundary condition handling",
    "deterministic state progression and minimal disturbance",
    "invariant guarantees hold under workload and failure pressure",
    "emits verification receipt",
    "with verified invariants",
    # environment [CARD-642]
    "single-brain memory.db invariants",
    "delivery profile and runtime constraints",
)


def words(text: str) -> List[str]:
    return [w for w in _WORD.findall((text or "").lower()) if w not in _STOP]


def stem(word: str) -> str:
    return word[:5]


def topic_keywords(topic: str) -> List[str]:
    return [w for w in words(topic) if len(w) >= 3]


def is_generated(title: str, tags: Any) -> bool:
    """Notes written by the course or priming pipeline are never sources for grounded content."""
    tag_set = {str(t).strip().lower() for t in (tags or []) if str(t).strip()}
    return bool(_GENERATED_TITLE.match(title or "")) or bool(tag_set & _GENERATED_TAGS)


def mentions_topic(text: str, topic: str) -> bool:
    low = (text or "").lower()
    phrase = (topic or "").strip().lower()
    if phrase and phrase in low:
        return True
    keys = topic_keywords(topic)
    if not keys:
        return False
    stems = {stem(w) for w in words(low)}
    return all(stem(k) in stems for k in keys)


def find_sources(wiki_tools: Any, topic: str, limit: int = MAX_SOURCES) -> List[Dict[str, Any]]:
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
        logger.info("grounded source search failed: %s", exc)
        return []
    if isinstance(hits, dict):
        hits = hits.get("results") or hits.get("hits") or hits.get("notes") or []
    sources: List[Dict[str, Any]] = []
    for hit in hits or []:
        if not isinstance(hit, dict):
            continue
        path = str(hit.get("path") or "").replace("\\", "/")
        title = str(hit.get("title") or "")
        if not path or is_generated(title, hit.get("tags")):
            continue
        try:
            note = wiki_tools.read_wiki_note(path) if hasattr(wiki_tools, "read_wiki_note") else wiki_tools.read_note(path)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(note, dict) or not note.get("success", True):
            continue
        meta = note.get("meta") or {}
        title = str(note.get("title") or meta.get("title") or title)
        if is_generated(title, meta.get("tags") or hit.get("tags")):
            continue
        body = str(note.get("content") or "")
        if not body.strip() or not mentions_topic(f"{title}\n{body}", topic):
            continue
        sources.append({"path": path, "title": title or path, "text": body[:EXCERPT_CHARS]})
        if len(sources) >= limit:
            break
    return sources


def public_sources(sources: Optional[Iterable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return [{"path": s["path"], "title": s["title"]} for s in (sources or []) if s.get("path")]


def parse_reply(text: str) -> Optional[Dict[str, Any]]:
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


def vocab_of(texts: Iterable[str]) -> set:
    return {stem(w) for t in texts for w in words(t) if len(w) >= 4}


def source_vocab(sources: Iterable[Dict[str, Any]]) -> set:
    return vocab_of(f"{s.get('title', '')} {s.get('text', '')}" for s in sources)


def grounded_count(text: str, vocab: set, topic_stems: set) -> int:
    """How many distinct non-topic words in `text` also appear in the source notes."""
    return len({stem(w) for w in words(text) if len(w) >= 4} & vocab - topic_stems)


def has_banned(texts: Iterable[str], extra: Iterable[str] = ()) -> bool:
    blob = " ".join(str(t) for t in texts).lower()
    return any(b in blob for b in (*BANNED_TEMPLATE_PHRASES, *extra))


def skip(topic: str, reason: str, sources: Optional[List[Dict[str, Any]]] = None, detail: str = "") -> Dict[str, Any]:
    return {
        "ok": False,
        "topic": topic,
        "skip_reason": reason,
        "detail": detail,
        "sources": public_sources(sources),
    }


def notes_block(sources: Iterable[Dict[str, Any]]) -> str:
    return "\n\n".join(f"### Note: {s['title']} ({s['path']})\n{s['text']}" for s in sources)


async def call_model(
    gateway: Any,
    system: str,
    user: str,
    *,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
    max_tokens: int = 1500,
) -> Dict[str, Any]:
    """One background call to the configured model. Returns {"text", "model"} or {"error"}."""
    if gateway is None:
        return {"error": "no model gateway"}
    from src.application.kernel.reply_limits import helper_call_seconds
    from src.domain.gateway.models import ChatMessage, CompletionRequest, Role

    model_id = model or getattr(gateway, "default_model_id", None) or "default"
    try:
        req = CompletionRequest(
            model=model_id,
            messages=[
                ChatMessage(role=Role.SYSTEM, content=system),
                ChatMessage(role=Role.USER, content=user),
            ],
            temperature=0.2,
            max_tokens=max_tokens,
            think=False,
            background=True,
        )
        resp = await asyncio.wait_for(gateway.complete(req), timeout=timeout or helper_call_seconds())
    except Exception as exc:  # noqa: BLE001 - no model answer means the step writes nothing
        logger.warning("grounded model call failed: %s", exc)
        return {"error": str(exc)[:200] or type(exc).__name__}
    return {"text": getattr(resp, "text", None) or "", "model": model_id}
