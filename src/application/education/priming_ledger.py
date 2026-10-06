"""Priming write-back orchestrator [CARD-317, CARD-646]."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from src.application.education.priming_schema import (
    PRIMING_FORBIDDEN_TOOLS,
    PRIMING_KIND,
    PRIMING_WIKI_TOOLS,
    build_grounded_priming_markdown,
    is_priming_wiki_tool,
    soft_fail_unregistered_tool,
)
from src.application.education.priming_seed import seed_ledger_anchors_from_priming_note
from src.application.education.priming_wiki_io import create_priming_note


def priming_writeback(
    *,
    topic: str,
    wiki_tools_or_store: Any,
    memory_repo: Any = None,
    composed: Optional[Dict[str, Any]] = None,
    attempt_forbidden_tools: Optional[Sequence[str]] = None,
    write_learner_fact: bool = True,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Priming write-back: soft-fail ghost tools, then a grounded Wiki note and its ledger anchors.

    `composed` is the grounded content from `grounded_steps.compose_step_content(..., "priming")`
    [CARD-646]. Without it (no notes on the topic, no model, or an ungrounded reply) nothing is
    written and the result carries `skip_reason`. There is no template outline.
    """
    topic_clean = (topic or "").strip()
    if not topic_clean:
        return {"success": False, "error": "topic_required", "tools_used": []}

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

    composed = composed or {}
    if not composed.get("ok"):
        return {
            "success": False,
            "skipped": True,
            "skip_reason": composed.get("skip_reason") or "not_composed",
            "detail": composed.get("detail") or "",
            "kind": PRIMING_KIND,
            "topic": topic_clean,
            "title": None,
            "path": None,
            "inbox": False,
            "tools_used": ["wiki_note_search"] if composed else [],
            "tool_trace": tool_trace,
            "soft_fails": soft_fails,
            "forbidden_called": [],
            "allowlist": sorted(PRIMING_WIKI_TOOLS),
            "ledger": {"success": True, "count": 0, "item_ids": []},
            "sources": composed.get("sources") or [],
            "grader": "priming_wiki_note_plus_ledger",
            "error": None,
        }

    from src.application.education.grounded import drop_duplicate_quiz

    composed = drop_duplicate_quiz(composed, memory_repo) or composed  # CARD-650
    tools_used: List[str] = ["wiki_note_search"]
    content = build_grounded_priming_markdown(topic=topic_clean, composed=composed)
    title = f"Priming: {topic_clean}"
    create_res = create_priming_note(
        wiki_tools_or_store,
        title=title,
        content=content,
        topic=topic_clean,
        summary=f"Priming from your notes on {topic_clean}",
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

    return {
        "success": success,
        "skipped": False,
        "skip_reason": None,
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
        "sources": composed.get("sources") or [],
        "grader": "priming_wiki_note_plus_ledger",
        "quiz_skip_reason": composed.get("quiz_skip_reason"),
        "error": create_res.get("error") if not note_ok else None,
    }
