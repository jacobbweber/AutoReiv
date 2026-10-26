"""Wiki note creation, deletion, and move helper implementations for WikiTools [CARD-744]."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.application.skills.template_scope import caller_template_scope
from src.domain.wiki.frontmatter import FrontmatterParser, coerce_string_or_list_of_strings

if TYPE_CHECKING:
    from src.application.skills.wiki_tools import WikiTools


def create_wiki_note_impl(
    tools: "WikiTools",
    title: str,
    content: str = "",
    domain: str = "general",
    topic: str = "general",
    category: str = "inbox",
    inbox_priority: str = "need_to_do",
    document_type: str = "atomic_note",
    tags: Optional[List[str]] = None,
    summary: str = "",
    status: str = "inbox",
    priority: str = "medium",
    relative_path: Optional[str] = None,
    extra_frontmatter: Optional[Dict[str, Any]] = None,
    template: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new markdown note with structured YAML frontmatter inside the wiki."""
    clean_doc_type = str(document_type or "").strip().lower()
    extra_fm = dict(extra_frontmatter or {})
    extra_type = str(extra_fm.get("type") or "").strip().lower()
    title_lower = str(title or "").strip().lower()

    title_is_template = (
        title_lower == "template"
        or title_lower.endswith(" template")
        or title_lower.endswith("-template")
        or title_lower.endswith("_template")
    )

    is_template = clean_doc_type == "template" or extra_type == "template" or title_is_template
    if not is_template and content and content.strip().startswith("---"):
        try:
            parsed_meta, _ = FrontmatterParser.parse(content)
            extra = getattr(parsed_meta, "model_extra", None) or {}
            if str(extra.get("type") or "").strip().lower() == "template":
                is_template = True
            elif not clean_doc_type and str(getattr(parsed_meta, "document_type", "") or "").lower() == "template":
                is_template = True
        except Exception:
            pass

    if is_template:
        clean_slug = re.sub(r"[^a-z0-9\-]", "", title_lower.replace(" ", "-").replace("_", "-"))
        if clean_slug.endswith("-template"):
            clean_slug = clean_slug[:-9].rstrip("-")
        clean_slug = clean_slug or "new-template"
        return {
            "success": False,
            "error": (
                f"Templates cannot be created with wiki_note_create. Use wiki_template_create(slug='{clean_slug}', "
                f"title='{title}', ...) to author structured templates in this agent's template folder."
            ),
        }

    explicit_template = (template or "").strip()
    effective_template = explicit_template or "zettelkasten-atomic"
    clean_tags = coerce_string_or_list_of_strings(tags)
    extra_frontmatter = dict(extra_frontmatter or {})
    extra_frontmatter.setdefault("template", effective_template)
    if not content:
        scope = caller_template_scope()
        if scope is None:
            tmpl = tools.store.get_template(effective_template)
        else:
            tmpl = tools.store.get_template(effective_template, folder=scope.own) if scope.own else None
        if tmpl:
            content = tmpl["content"].replace("${TITLE}", title)
        elif scope is not None and explicit_template:
            return {"success": False, "error": f"Template '{explicit_template}' not found."}

    vault_root = str(tools.store.root_dir.resolve())

    def _enrich(res_dict: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(res_dict, dict) and res_dict.get("success"):
            res_dict["vault_root"] = vault_root
            res_dict["relative_path"] = res_dict.get("path", "")
            res_dict["template"] = extra_frontmatter.get("template", effective_template)
            if str(res_dict.get("path", "")).startswith("00_Inbox/"):
                res_dict["note"] = (
                    "Staged in 00_Inbox/ per One-Door Policy. To move this note to a folder in "
                    "01_Notes/ or 02_Resources/, call wiki_note_move(source_path='"
                    + str(res_dict.get("path", ""))
                    + "', destination_path='<target_path>')."
                )
        return res_dict

    if relative_path:
        safe_target = tools.store._resolve_safe_path(relative_path)
        if safe_target is None:
            return {"success": False, "error": "Path traversal detected: target path is outside wiki root."}

        rel_lower = relative_path.replace("\\", "/").lower().lstrip("/")
        if rel_lower.startswith("01_notes/") or rel_lower.startswith("notes/"):
            filed = tools.store.file_note(
                title=title,
                content=content,
                domain=domain,
                topic=topic,
                category="inbox",
                inbox_priority=inbox_priority,
                document_type=document_type,
                tags=clean_tags,
                summary=summary,
                status="inbox",
                priority=priority,
                extra_meta=extra_frontmatter,
            )
            seeded = tools._maybe_seed_priming_ledger(
                filed if isinstance(filed, dict) else {"success": True, "path": filed, "title": title},
                tags=clean_tags,
                content=content,
                title=title,
                topic=topic,
            )
            return _enrich(seeded)

        is_resource = rel_lower.startswith("02_resources/") or rel_lower.startswith("resources/")
        res = tools.store.write_note(
            relative_path=relative_path,
            content=content,
            update_frontmatter={
                "title": title,
                "domain": domain,
                "topic": topic,
                "document_type": document_type,
                "tags": clean_tags,
                "summary": summary,
                "status": "active" if is_resource else "inbox",
                "priority": priority,
                **(extra_frontmatter or {}),
            },
        )
        seeded = tools._maybe_seed_priming_ledger(
            {
                "success": True,
                "path": res["path"],
                "title": title,
                "category": "resources" if is_resource else "inbox",
            },
            tags=clean_tags,
            content=content,
            title=title,
            topic=topic,
        )
        return _enrich(seeded)

    clean_cat = str(category or "inbox").lower().strip()
    target_category = "resources" if clean_cat in ("resources", "02_resources") else "inbox"

    filed = tools.store.file_note(
        title=title,
        content=content,
        domain=domain,
        topic=topic,
        category=target_category,
        inbox_priority=inbox_priority,
        document_type=document_type,
        tags=clean_tags,
        summary=summary,
        status=status if target_category == "resources" else "inbox",
        priority=priority,
        extra_meta=extra_frontmatter,
    )
    seeded = tools._maybe_seed_priming_ledger(
        filed if isinstance(filed, dict) else {"success": True, "path": filed, "title": title},
        tags=clean_tags,
        content=content,
        title=title,
        topic=topic,
    )
    return _enrich(seeded)
