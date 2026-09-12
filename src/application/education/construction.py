"""Education Construction: generative study artifacts via wiki_note_* only [CARD-245].

Produces multi-section study notes (schema + dual-code hooks + quiz/elaboration
prompts) and stages them into Wiki 00_Inbox/ using catalog-matched wiki_note_*
paths only. Never calls wiki_overview / wiki_graph. Fail-soft on search/read so
create can still land an Inbox note (CARD-241 posture).
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.application.safety.tool_policy_gate import (
    EDUCATION_FORBIDDEN_WIKI_TOOLS,
    EDUCATION_WIKI_NOTE_TOOLS,
)

CONSTRUCTION_WIKI_TOOLS: frozenset[str] = frozenset(EDUCATION_WIKI_NOTE_TOOLS)
CONSTRUCTION_FORBIDDEN_TOOLS: frozenset[str] = frozenset(EDUCATION_FORBIDDEN_WIKI_TOOLS)
ARTIFACT_KIND = "construction_study_artifact"


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


def _artifact_id(topic: str, source_path: str = "") -> str:
    digest = hashlib.sha1(f"const|{topic}|{source_path}".encode("utf-8")).hexdigest()[:12]
    return f"const_{digest}"


def build_study_artifact_markdown(
    *,
    topic: str,
    source_excerpts: Optional[Sequence[Dict[str, Any]]] = None,
    teach_style: str = "",
    now: Optional[datetime] = None,
) -> str:
    """Build generative study artifact body (deterministic; no LLM)."""
    topic_clean = (topic or "Untitled topic").strip() or "Untitled topic"
    style = (teach_style or "clear stepwise study artifact").strip()
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
        grounding_lines.append("- (no prior Wiki grounding - constructed from topic alone)")

    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", topic_clean)]
    concepts = words[:5] or ["core idea", "practice", "retention"]
    outline = [
        f"What is {topic_clean}?",
        "Why it matters in AutoReiv / your vault",
        "Key parts / moving pieces",
        "Common failure modes",
        "How you will prove understanding",
    ]

    quiz_q1 = f"In one sentence, what is {topic_clean}?"
    quiz_a1 = f"{topic_clean} is a durable concept you can retrieve and apply without chat fluff."
    quiz_q2 = f"Name one failure mode when studying {topic_clean}."
    quiz_a2 = "Treating a chat toast as Done instead of writing a Wiki study artifact."

    elab_prompt = f"Explain {topic_clean} in your own words."
    elab_ref = (
        f"{topic_clean} is learned by constructing a Wiki study artifact "
        "(schema + dual codes + retrieval prompts), not by scrolling chat."
    )
    elab_concepts = ", ".join(concepts[:3])

    mermaid_lines = [
        "```mermaid",
        "flowchart TD",
        f"  T[Topic: {topic_clean}] --> S[Schema / Priming]",
        "  S --> D[Dual Coding prose + diagram]",
        "  D --> R[Retrieval quiz prompts]",
        "  R --> E[Elaboration explain-it-back]",
        "  E --> W[Wiki 00_Inbox artifact]",
        "```",
    ]
    mermaid = "\n".join(mermaid_lines)

    parts = [
        f"# Construction study artifact: {topic_clean}",
        "",
        f"> Generated {stamp} - teach style: {style}",
        f"> Kind: {ARTIFACT_KIND}",
        "> Tools: wiki_note_search / wiki_note_read / wiki_note_create only (never wiki_overview)",
        "",
        "## Grounding",
        "\n".join(grounding_lines),
        "",
        "## Priming schema",
        "### Outline",
        "\n".join(f"- {b}" for b in outline),
        "",
        "### Prerequisites",
        "- Ability to open Wiki notes in Education Studio",
        "- Willing to write answers back (quiz / elaboration) instead of LLM self-score theatre",
        "",
        "### Learning goals",
        f"- Retrieve the core definition of {topic_clean} without looking",
        f"- Draw or narrate a dual-code (prose + structure) for {topic_clean}",
        "- Catch one failure mode before it becomes chat fluff",
        "",
        "## Dual Coding",
        "### Prose",
        (
            f"{topic_clean} becomes durable when you **construct** a study artifact in Wiki: "
            "search priors, draft a schema, pair prose with a structured diagram, then add "
            "retrieval and explain-it-back prompts. Construction uses catalog-matched "
            "`wiki_note_*` only so Execute cannot die on out-of-catalog `wiki_overview`."
        ),
        "",
        "### Diagram",
        mermaid,
        "",
        "## Quiz",
        f"- Q: {quiz_q1}",
        f"  A: {quiz_a1}",
        f"- Q: {quiz_q2}",
        f"  A: {quiz_a2}",
        "",
        "## Elaboration",
        f"- Prompt: {elab_prompt}",
        f"  Reference: {elab_ref}",
        f"  Concepts: {elab_concepts}",
        "",
        "## Construction checklist",
        "- [ ] Schema outline filled",
        "- [ ] Dual-code prose + Mermaid present",
        "- [ ] At least two quiz prompts with answers",
        "- [ ] Explain-it-back prompt with reference/concepts",
        "- [ ] Note staged in `00_Inbox/` via `wiki_note_create`",
        "",
    ]
    return "\n".join(parts)


def search_grounding_notes(
    wiki_tools_or_store: Any,
    *,
    query: str,
    limit: int = 5,
) -> Dict[str, Any]:
    """Fail-soft Wiki search via wiki_note_search equivalent. Never wiki_overview."""
    assert_construction_tool_allowed("wiki_note_search")
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


def read_grounding_note(
    wiki_tools_or_store: Any,
    *,
    relative_path: str,
) -> Dict[str, Any]:
    """Fail-soft Wiki read via wiki_note_read equivalent. Never wiki_overview."""
    assert_construction_tool_allowed("wiki_note_read")
    path = (relative_path or "").strip()
    if not path or wiki_tools_or_store is None:
        return {"success": True, "skipped": True, "tool": "wiki_note_read"}
    try:
        if hasattr(wiki_tools_or_store, "read_wiki_note"):
            raw = wiki_tools_or_store.read_wiki_note(relative_path=path)
        elif hasattr(wiki_tools_or_store, "read_note"):
            raw = wiki_tools_or_store.read_note(path)
        else:
            return {
                "success": True,
                "skipped": True,
                "tool": "wiki_note_read",
                "reason": "no_read_handler",
            }
        if isinstance(raw, dict) and raw.get("success") is False:
            return {
                "success": True,
                "skipped": True,
                "tool": "wiki_note_read",
                "error": raw.get("error"),
                "path": path,
            }
        return {
            "success": True,
            "tool": "wiki_note_read",
            "path": (raw or {}).get("path") if isinstance(raw, dict) else path,
            "title": (raw or {}).get("title") if isinstance(raw, dict) else "",
            "content": (raw or {}).get("content") or (raw or {}).get("body") or "",
            "frontmatter": (raw or {}).get("frontmatter") or (raw or {}).get("meta") or {},
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": True,
            "skipped": True,
            "tool": "wiki_note_read",
            "error": str(exc),
            "path": path,
        }


def create_study_artifact_note(
    wiki_tools_or_store: Any,
    *,
    title: str,
    content: str,
    topic: str,
    tags: Optional[Sequence[str]] = None,
    summary: str = "",
) -> Dict[str, Any]:
    """Stage study artifact via wiki_note_create path (One-Door -> 00_Inbox/)."""
    assert_construction_tool_allowed("wiki_note_create")
    if wiki_tools_or_store is None:
        return {"success": False, "error": "no_wiki_store", "tool": "wiki_note_create"}
    tag_list = list(tags or ["education", "construction", "study-artifact"])
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
                document_type="study_artifact",
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
                document_type="study_artifact",
                status="inbox",
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


def construct_study_artifact(
    *,
    topic: str,
    wiki_tools_or_store: Any,
    wiki_path: Optional[str] = None,
    teach_style: str = "",
    search_first: bool = True,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Full Construction path: optional search/read (fail soft) -> create Inbox note.

    Guarantees: never invokes wiki_overview/wiki_graph; create uses wiki_note_create.
    """
    topic_clean = (topic or "").strip()
    if not topic_clean:
        return {"success": False, "error": "topic_required", "tools_used": []}

    tools_used: List[str] = []
    tool_trace: List[Dict[str, Any]] = []
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

    source = (wiki_path or "").strip()
    if source:
        read_res = read_grounding_note(wiki_tools_or_store, relative_path=source)
        tools_used.append("wiki_note_read")
        tool_trace.append(read_res)
        if not read_res.get("skipped"):
            excerpts.insert(
                0,
                {
                    "path": read_res.get("path") or source,
                    "title": read_res.get("title") or source,
                    "snippet": (read_res.get("content") or "")[:240],
                    "content": read_res.get("content") or "",
                },
            )

    content = build_study_artifact_markdown(
        topic=topic_clean,
        source_excerpts=excerpts,
        teach_style=teach_style,
        now=now,
    )
    title = f"Construction: {topic_clean}"
    create_res = create_study_artifact_note(
        wiki_tools_or_store,
        title=title,
        content=content,
        topic=topic_clean,
        summary=f"Generative Construction study artifact for {topic_clean}",
    )
    tools_used.append("wiki_note_create")
    tool_trace.append(create_res)

    aid = _artifact_id(topic_clean, source)
    path = str(create_res.get("path") or "")
    inbox_ok = bool(create_res.get("inbox")) or path.replace("\\", "/").startswith("00_Inbox/")
    forbidden_called = [t for t in tools_used if t in CONSTRUCTION_FORBIDDEN_TOOLS]

    return {
        "success": bool(create_res.get("success")) and inbox_ok and not forbidden_called,
        "artifact_id": aid,
        "kind": ARTIFACT_KIND,
        "topic": topic_clean,
        "title": title,
        "path": path,
        "inbox": inbox_ok,
        "content_preview": content[:400],
        "word_count": len(content.split()),
        "tools_used": tools_used,
        "tool_trace": tool_trace,
        "forbidden_called": forbidden_called,
        "allowlist": sorted(CONSTRUCTION_WIKI_TOOLS),
        "grader": "construction_wiki_note_only",
        "error": create_res.get("error"),
    }


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
