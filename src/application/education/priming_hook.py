"""Priming wiki_note_create hook + Ask clause [CARD-317]."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Sequence

from src.application.education.priming_seed import seed_ledger_anchors_from_priming_note


def maybe_seed_ledger_after_priming_create(
    *,
    tags: Optional[Sequence[str]],
    path: str,
    content: str,
    title: str = "",
    topic: str = "",
) -> Dict[str, Any]:
    """Best-effort hook after wiki_note_create when tags include education+priming."""
    tag_set = {str(t or "").strip().lower() for t in (tags or [])}
    if "priming" not in tag_set or "education" not in tag_set:
        return {"success": False, "skipped": True, "reason": "not_priming_tags"}
    path_s = (path or "").strip()
    if not path_s:
        return {"success": False, "skipped": True, "reason": "no_path"}
    try:
        from src.application.kernel.tool_registry import get_tool_context
        from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

        ctx = get_tool_context()
        agent_id = str(ctx.get("agent_id") or "assistant").strip() or "assistant"
        data_dir = os.environ.get("AUTOREIV_DATA_DIR") or ctx.get("data_dir")
        if not data_dir:
            return {"success": False, "skipped": True, "reason": "no_data_dir"}
        repo = AgentMemoryRepository(agent_id=agent_id, data_dir=data_dir)
        repo.initialize_schema()
        topic_clean = (topic or "").strip() or (title or "").replace("Priming:", "").strip() or path_s
        return seed_ledger_anchors_from_priming_note(
            repo,
            content=content or "",
            wiki_path=path_s,
            topic=topic_clean,
            write_learner_fact=True,
        )
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "skipped": True, "fail_soft": True, "error": str(exc)}


def build_priming_ask_clause(
    *,
    topic: str,
    wiki_path: str = "",
    wiki_title: str = "",
    teach_style: str = "",
) -> str:
    """Shape Education Ask for Priming mode (CARD-241 allowlist + CARD-317 ledger)."""
    topic_clean = (topic or "").strip() or "this topic"
    style = (teach_style or "schema first").strip()
    wiki_bit = ""
    if wiki_path:
        wiki_bit = f' Ground in Wiki note "{wiki_title or wiki_path}" ({wiki_path}).'
    return (
        f'[Education Studio] [Mode: Priming] Teach me about "{topic_clean}" '
        f"using the education-priming skill.{wiki_bit} "
        f"How to teach me: {style}. "
        "Use only wiki_note_search/wiki_note_list/wiki_note_read/wiki_note_create "
        "(never wiki_overview). Soft-fail any unregistered wiki tool and continue. "
        "wiki_note_create a Priming schema note into 00_Inbox/ with outline + "
        "prerequisites + learning goals + Quiz; leave ledger anchors in memory.db. "
        f'Done-when: a Priming schema note exists in Wiki for "{topic_clean}" '
        "and ledger anchors for that topic exist in mastery/learner."
    )
