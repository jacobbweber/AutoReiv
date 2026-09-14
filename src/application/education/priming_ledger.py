"""Priming write-back orchestrator [CARD-317]."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.application.education.priming_schema import (
    PRIMING_FORBIDDEN_TOOLS,
    PRIMING_KIND,
    PRIMING_WIKI_TOOLS,
    build_priming_schema_markdown,
    is_priming_wiki_tool,
    soft_fail_unregistered_tool,
)
from src.application.education.priming_wiki_io import (
    create_priming_note,
    search_grounding_notes,
)
from src.application.education.priming_seed import seed_ledger_anchors_from_priming_note


def priming_writeback(
    *,
    topic: str,
    wiki_tools_or_store: Any,
    memory_repo: Any = None,
    teach_style: str = "",
    search_first: bool = True,
    attempt_forbidden_tools: Optional[Sequence[str]] = None,
    write_learner_fact: bool = True,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Full Priming write-back: soft-fail ghosts then Wiki schema note then ledger anchors."""
    topic_clean = (topic or "").strip()
    if not topic_clean:
        return {"success": False, "error": "topic_required", "tools_used": []}

    tools_used: List[str] = []
    tool_trace: List[Dict[str, Any]] = []
    soft_fails: List[Dict[str, Any]] = []

    for ghost in attempt_forbidden_tools or ():
        name = str(ghost or "").strip()
        if not name:
            continue
        if name in PRIMING_FORBIDDEN_TOOLS or (
            name.startswith("wiki_") and name not in PRIMING_WIKI_TOOLS
        ) or not is_priming_wiki_tool(name):
            soft = soft_fail_unregistered_tool(name)
            soft_fails.append(soft)
            tool_trace.append(soft)

    excerpts: List[Dict[str, Any]] = []
    if search_first:
        search_res = search_grounding_notes(
            wiki_tools_or_store, query=topic_clean, limit=5
        )
        tools_used.append("wiki_note_search")
        tool_trace.append(search_res)
        for hit in search_res.get("hits") or []:
            excerpts.append(
                {
                    "path": hit.get("path") or hit.get("relative_path"),
                    "title": hit.get("title"),
                    "snippet": hit.get("snippet") or hit.get("summary") or "",
                }
            )

    content = build_priming_schema_markdown(
        topic=topic_clean,
        teach_style=teach_style,
        source_excerpts=excerpts,
        now=now,
    )
    title = f"Priming: {topic_clean}"
    create_res = create_priming_note(
        wiki_tools_or_store,
        title=title,
        content=content,
        topic=topic_clean,
        summary=f"Priming schema/outline for {topic_clean}",
    )
    tools_used.append("wiki_note_create")
    tool_trace.append(create_res)

    path = str(create_res.get("path") or "")
    inbox_ok = bool(create_res.get("inbox")) or path.replace("\\", "/").startswith("00_Inbox/")
    note_ok = bool(create_res.get("success")) and inbox_ok

    ledger: Dict[str, Any] = {"success": False, "skipped": True}
    if note_ok and memory_repo is not None:
        ledger = seed_ledger_anchors_from_priming_note(
            memory_repo,
            content=content,
            wiki_path=path,
            topic=topic_clean,
            write_learner_fact=write_learner_fact,
        )

    forbidden_called = [t for t in tools_used if t in PRIMING_FORBIDDEN_TOOLS]
    success = note_ok and not forbidden_called
    if soft_fails and note_ok:
        success = True

    return {
        "success": success,
        "kind": PRIMING_KIND,
        "topic": topic_clean,
        "title": title,
        "path": path,
        "inbox": inbox_ok,
        "content_preview": content[:400],
        "word_count": len(content.split()),
        "tools_used": tools_used,
        "tool_trace": tool_trace,
        "soft_fails": soft_fails,
        "forbidden_called": forbidden_called,
        "allowlist": sorted(PRIMING_WIKI_TOOLS),
        "ledger": ledger,
        "grader": "priming_wiki_note_plus_ledger",
        "error": create_res.get("error") if not note_ok else None,
    }
