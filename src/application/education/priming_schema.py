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
