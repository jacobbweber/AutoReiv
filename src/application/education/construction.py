"""Education Construction: the wiki_note_* allowlist, the shared study-note creator and the Ask clause [CARD-245].

The course lab writers file their grounded notes into Wiki 00_Inbox/ through
create_study_artifact_note, using catalog-matched wiki_note_* paths only. Never calls
wiki_overview / wiki_graph. The template study-artifact generator and its HTTP route were
removed [CARD-648].
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Sequence

from src.application.safety.tool_policy_gate import (
    EDUCATION_FORBIDDEN_WIKI_TOOLS,
    EDUCATION_WIKI_NOTE_TOOLS,
)

CONSTRUCTION_WIKI_TOOLS: frozenset[str] = frozenset(EDUCATION_WIKI_NOTE_TOOLS)
CONSTRUCTION_FORBIDDEN_TOOLS: frozenset[str] = frozenset(EDUCATION_FORBIDDEN_WIKI_TOOLS)


def assert_construction_tool_allowed(tool_name: str) -> None:
    """Raise if Construction attempts an out-of-catalog Wiki tool."""
    name = str(tool_name or "").strip()
    if name in CONSTRUCTION_FORBIDDEN_TOOLS or (
        name.startswith("wiki_") and name not in CONSTRUCTION_WIKI_TOOLS
    ):
        raise ValueError(
            f"Construction forbids out-of-catalog tool '{name}'. "
            f"Use only: {', '.join(sorted(CONSTRUCTION_WIKI_TOOLS))}."
        )


def _slug_topic(topic: str) -> str:
    raw = re.sub(r"[^a-zA-Z0-9]+", "_", (topic or "topic").strip()).strip("_").lower()
    return (raw or "topic")[:48]


def create_study_artifact_note(
    wiki_tools_or_store: Any,
    *,
    title: str,
    content: str,
    topic: str,
    tags: Optional[Sequence[str]] = None,
    summary: str = "",
    template: Optional[str] = "education-lab",
    document_type: str = "study_artifact",
    extra_frontmatter: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Stage study artifact via wiki_note_create path (One-Door -> 00_Inbox/)."""
    assert_construction_tool_allowed("wiki_note_create")
    if wiki_tools_or_store is None:
        return {"success": False, "error": "no_wiki_store", "tool": "wiki_note_create"}
    from src.application.education.templates import assert_education_template_required

    clean_template = assert_education_template_required(template)
    tag_list = list(tags or ["education", "construction", "study-artifact"])
    if "education" not in tag_list:
        tag_list.append("education")
    if clean_template not in tag_list:
        tag_list.append(clean_template)

    extra_fm = dict(extra_frontmatter or {})  # CARD-645: course step metadata goes to front matter
    topic_slug = _slug_topic(topic)
    summary_text = summary or f"Construction study artifact for {topic}"
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
                document_type=document_type,
                template=clean_template,
                extra_frontmatter={**extra_fm, "template": clean_template},
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
                document_type=document_type,
                status="inbox",
                extra_meta={**extra_fm, "template": clean_template},
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


def build_construction_ask_clause(
    *,
    topic: str,
    wiki_path: str = "",
    wiki_title: str = "",
    teach_style: str = "",
) -> str:
    """Shape Education Ask for Construction mode (CARD-241 allowlist language)."""
    topic_clean = (topic or "").strip() or "this topic"
    style = (teach_style or "generate a durable study artifact").strip()
    wiki_bit = ""
    if wiki_path:
        wiki_bit = f' Ground in Wiki note "{wiki_title or wiki_path}" ({wiki_path}).'
    return (
        f'[Education Studio] [Mode: Construction] Construct a generative study artifact for "{topic_clean}" '
        f"using the education-construction skill.{wiki_bit} "
        f"How to teach me: {style}. "
        "Use only wiki_note_search/wiki_note_list/wiki_note_read/wiki_note_create "
        "(never wiki_overview). Search Wiki first (fail soft if empty), then "
        "wiki_note_create a Construction study note into 00_Inbox/ with schema + "
        "dual-code (prose+Mermaid) + quiz + elaboration prompts. "
        f'Done-when: a Construction study artifact note exists in Wiki 00_Inbox/ for "{topic_clean}" '
        "and I can open it."
    )
