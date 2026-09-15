"""Priming wiki_note_search / wiki_note_create IO [CARD-317]."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from src.application.education.priming_schema import (
    assert_priming_tool_allowed,
    slug_topic,
)


def search_grounding_notes(
    wiki_tools_or_store: Any,
    *,
    query: str,
    limit: int = 5,
) -> Dict[str, Any]:
    """Fail-soft Wiki search via wiki_note_search. Never wiki_overview."""
    assert_priming_tool_allowed("wiki_note_search")
    q = (query or "").strip()
    if not q or wiki_tools_or_store is None:
        return {"success": True, "skipped": True, "hits": [], "tool": "wiki_note_search"}
    try:
        if hasattr(wiki_tools_or_store, "search_wiki_notes"):
            raw = wiki_tools_or_store.search_wiki_notes(q, limit=limit)
        elif hasattr(wiki_tools_or_store, "search_notes"):
            raw = wiki_tools_or_store.search_notes(q, limit=limit)
        else:
            return {
                "success": True,
                "skipped": True,
                "hits": [],
                "tool": "wiki_note_search",
                "reason": "no_search_handler",
            }
        hits: List[Dict[str, Any]] = []
        if isinstance(raw, dict):
            items = raw.get("results") or raw.get("hits") or raw.get("notes") or []
            if isinstance(items, list):
                for it in items[:limit]:
                    if isinstance(it, dict):
                        hits.append(it)
        elif isinstance(raw, list):
            hits = [h for h in raw[:limit] if isinstance(h, dict)]
        return {"success": True, "hits": hits, "tool": "wiki_note_search"}
    except Exception as exc:  # noqa: BLE001
        return {
            "success": True,
            "skipped": True,
            "hits": [],
            "tool": "wiki_note_search",
            "error": str(exc),
        }


def create_priming_note(
    wiki_tools_or_store: Any,
    *,
    title: str,
    content: str,
    topic: str,
    tags: Optional[Sequence[str]] = None,
    summary: str = "",
    template: Optional[str] = "education-priming",
) -> Dict[str, Any]:
    """Stage Priming schema via wiki_note_create (One-Door to 00_Inbox/)."""
    assert_priming_tool_allowed("wiki_note_create")
    if wiki_tools_or_store is None:
        return {"success": False, "error": "no_wiki_store", "tool": "wiki_note_create"}
    from src.application.education.templates import assert_education_template_required

    clean_template = assert_education_template_required(template)
    tag_list = list(tags or ["education", "priming", "schema"])
    if "education" not in tag_list:
        tag_list.append("education")
    if clean_template not in tag_list:
        tag_list.append(clean_template)

    topic_slug = slug_topic(topic)
    summary_text = summary or f"Priming schema for {topic}"
    try:
        if hasattr(wiki_tools_or_store, "create_wiki_note"):
            result = wiki_tools_or_store.create_wiki_note(
                title=title,
                content=content,
                domain="education",
                topic=topic_slug,
                category="inbox",
                tags=tag_list,
                summary=summary_text,
                document_type="priming_schema",
                template=clean_template,
                extra_frontmatter={"template": clean_template},
            )
        elif hasattr(wiki_tools_or_store, "file_note"):
            result = wiki_tools_or_store.file_note(
                title=title,
                content=content,
                domain="education",
                topic=topic_slug,
                category="inbox",
                tags=tag_list,
                summary=summary_text,
                document_type="priming_schema",
                status="inbox",
                extra_meta={"template": clean_template},
            )
        else:
            return {
                "success": False,
                "error": "no_create_handler",
                "tool": "wiki_note_create",
            }
        if not isinstance(result, dict):
            return {"success": False, "error": "bad_create_result", "tool": "wiki_note_create"}
        path = str(result.get("path") or "")
        ok = bool(result.get("success", True)) and bool(path)
        inbox = path.replace("\\", "/").startswith("00_Inbox/")
        return {
            "success": ok,
            "tool": "wiki_note_create",
            "path": path,
            "title": result.get("title") or title,
            "inbox": inbox,
            "raw": {k: v for k, v in result.items() if k != "content"},
            "error": result.get("error"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc), "tool": "wiki_note_create"}
