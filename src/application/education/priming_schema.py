"""Priming schema note helpers (wiki_note_* only) [CARD-317]."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.application.safety.tool_policy_gate import (
    EDUCATION_FORBIDDEN_WIKI_TOOLS,
    EDUCATION_WIKI_NOTE_TOOLS,
)

PRIMING_WIKI_TOOLS: frozenset[str] = frozenset(EDUCATION_WIKI_NOTE_TOOLS)
PRIMING_FORBIDDEN_TOOLS: frozenset[str] = frozenset(EDUCATION_FORBIDDEN_WIKI_TOOLS)
PRIMING_KIND = "priming_schema"
PRIMING_LEARNER_ATTR = "priming_topic"


def assert_priming_tool_allowed(tool_name: str) -> None:
    """Raise if Priming attempts an out-of-catalog Wiki tool (hard assert for helpers)."""
    name = str(tool_name or "").strip()
    if name in PRIMING_FORBIDDEN_TOOLS or (
        name.startswith("wiki_") and name not in PRIMING_WIKI_TOOLS
    ):
        raise ValueError(
            f"Priming forbids out-of-catalog tool '{name}'. "
            f"Use only: {', '.join(sorted(PRIMING_WIKI_TOOLS))}."
        )


def soft_fail_unregistered_tool(tool_name: str) -> Dict[str, Any]:
    """CARD-317/241: unregistered / non-catalog wiki tools soft-fail (skip, do not abort)."""
    name = str(tool_name or "").strip() or "unknown_tool"
    return {
        "success": True,
        "skipped": True,
        "fail_soft": True,
        "tool": name,
        "reason": f"unregistered_or_out_of_catalog:{name}",
        "hint": (
            "Skip this tool and continue. For Education Priming use catalog-matched "
            "wiki_note_search / wiki_note_list / wiki_note_read / wiki_note_create "
            "(optional wiki_note_append) only; never wiki_overview."
        ),
    }


def is_priming_wiki_tool(tool_name: str) -> bool:
    return str(tool_name or "").strip() in PRIMING_WIKI_TOOLS


def slug_topic(topic: str) -> str:
    raw = re.sub(r"[^a-zA-Z0-9]+", "_", (topic or "topic").strip()).strip("_").lower()
    return (raw or "topic")[:48]


def topic_anchor_id(topic: str, wiki_path: str = "") -> str:
    digest = hashlib.sha1(f"priming|{topic}|{wiki_path}".encode("utf-8")).hexdigest()[:12]
    return f"edu_prim_{digest}"


def build_priming_schema_markdown(
    *,
    topic: str,
    teach_style: str = "",
    source_excerpts: Optional[Sequence[Dict[str, Any]]] = None,
    now: Optional[datetime] = None,
) -> str:
    """Build Priming schema/outline note body with Quiz section for ledger seeding."""
    topic_clean = (topic or "Untitled topic").strip() or "Untitled topic"
    style = (teach_style or "schema first, then detail").strip()
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    stamp = base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    excerpts = list(source_excerpts or [])

    grounding_lines: List[str] = []
    for ex in excerpts[:5]:
        path = str(ex.get("path") or ex.get("wiki_path") or "").strip()
        title = str(ex.get("title") or path or "note").strip()
        snip = re.sub(r"\s+", " ", str(ex.get("snippet") or ex.get("content") or "").strip())[:180]
        if path:
            grounding_lines.append(f"- [[{path}|{title}]] - {snip or '(no snippet)'}")
        elif snip:
            grounding_lines.append(f"- {title}: {snip}")
    if not grounding_lines:
        grounding_lines.append("- (no prior Wiki grounding — primed from topic alone)")

    outline = [
        f"What is {topic_clean}?",
        "Why it matters (AutoReiv / your vault)",
        "Key parts / moving pieces",
        "Prerequisites and priors",
        "How you will prove understanding",
    ]

    quiz_q1 = f"In one sentence, what is {topic_clean}?"
    quiz_a1 = (
        f"{topic_clean} is a durable concept learned via Priming schema "
        "(outline + prerequisites + goals) before deep detail."
    )
    quiz_q2 = f"Where should Priming write durable knowledge for {topic_clean}?"
    quiz_a2 = "Wiki schema/outline note and memory.db ledger anchors"

    parts = [
        f"# Priming: {topic_clean}",
        "",
        f"> Generated {stamp} — teach style: {style}",
        f"> Kind: {PRIMING_KIND}",
        "> Tools: wiki_note_search / wiki_note_list / wiki_note_read / wiki_note_create only (never wiki_overview)",
        "",
        "## Grounding",
        "\n".join(grounding_lines),
        "",
        "## Outline",
        "\n".join(f"- {b}" for b in outline),
        "",
        "## Prerequisites",
        "- Ability to open Wiki notes in Education Studio",
        "- Willing to retrieve later (quiz) instead of chat-only toast",
        "",
        "## Learning goals",
        f"- Activate priors for {topic_clean} before deep detail",
        f"- Hold a clear outline of {topic_clean} in Wiki",
        "- Leave ledger anchors in memory.db so Retrieval can practice the same topic",
        "",
        "## Quiz",
        f"- Q: {quiz_q1}",
        f"  A: {quiz_a1}",
        f"- Q: {quiz_q2}",
        f"  A: {quiz_a2}",
        "",
        "## Done-when",
        f"- Priming schema note exists in Wiki for \"{topic_clean}\" (outline + prerequisites + goals)",
        "- Ledger anchors for the topic exist in agent memory.db (education_mastery and/or learner facts)",
        "",
    ]
    return "\n".join(parts)
