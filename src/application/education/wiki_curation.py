"""Wiki curation from links / curriculum for Tutor Learning OS [CARD-440].

Durable path: fetch or accept outline -> stage Wiki note(s) via wiki_note_create
(One-Door into 00_Inbox/). Education templates from templates.py when claimed;
raw/source notes MAY omit education tags. Failures never claim library updated.
"""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence
from urllib.parse import urlparse

from src.application.education.templates import (
    EDUCATION_TEMPLATES,
    assert_education_template_required,
    get_education_template,
    list_education_templates,
)

SKILL_ID = "education-wiki-curation"
HTTP_CONTRACT = "POST /api/education/wiki/curate"
DEFAULT_EDUCATION_TEMPLATE = "education-concept"
RAW_SOURCE_TEMPLATE = "zettelkasten-atomic"
FETCH_TIMEOUT_SEC = 12
MAX_BODY_CHARS = 24_000
USER_AGENT = "AutoReiv-EducationWikiCuration/1.0 (+CARD-440)"


def catalog_education_templates() -> List[Dict[str, Any]]:
    """Return catalogue entries for Tutor / Learning OS curation UI."""
    out: List[Dict[str, Any]] = []
    for item in list_education_templates():
        out.append(
            {
                "slug": item.get("slug"),
                "title": item.get("title"),
                "description": item.get("description"),
                "filename": item.get("filename"),
                "tags": list(item.get("tags") or []),
            }
        )
    return out


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(text: str, *, fallback: str = "note") -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return (clean or fallback)[:64]


def _looks_like_url(value: str) -> bool:
    raw = (value or "").strip()
    if not raw:
        return False
    parsed = urlparse(raw)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return True
    return False


def _strip_html(raw: str) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw or "")
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _extract_html_title(raw: str) -> Optional[str]:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw or "")
    if not m:
        return None
    title = _strip_html(m.group(1))
    return title.strip() or None


def fetch_link_text(
    url: str,
    *,
    opener: Optional[Callable[[str], bytes]] = None,
) -> Dict[str, Any]:
    """Fetch a public http(s) URL and return plain text + title.

    On failure returns success=False with error; never invents content.
    """
    clean = (url or "").strip()
    if not _looks_like_url(clean):
        return {
            "success": False,
            "error": "url must be an absolute http(s) URL",
            "url": clean,
            "durable": False,
        }

    try:
        if opener is not None:
            raw_bytes = opener(clean)
        else:
            req = urllib.request.Request(
                clean,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain,*/*"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_SEC) as resp:
                raw_bytes = resp.read(MAX_BODY_CHARS + 1024)
    except urllib.error.HTTPError as exc:
        return {
            "success": False,
            "error": f"fetch HTTP {exc.code}: {exc.reason}",
            "url": clean,
            "durable": False,
        }
    except Exception as exc:  # noqa: BLE001 - surface honest fetch failure
        return {
            "success": False,
            "error": f"fetch failed: {exc}",
            "url": clean,
            "durable": False,
        }

    if raw_bytes is None:
        return {
            "success": False,
            "error": "fetch returned empty body",
            "url": clean,
            "durable": False,
        }

    try:
        raw = raw_bytes.decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "error": f"decode failed: {exc}",
            "url": clean,
            "durable": False,
        }

    title = _extract_html_title(raw) or urlparse(clean).path.rsplit("/", 1)[-1] or clean
    body = _strip_html(raw)
    if len(body) > MAX_BODY_CHARS:
        body = body[:MAX_BODY_CHARS] + "\n\n…[truncated]"
    if not body.strip():
        return {
            "success": False,
            "error": "fetched page had no usable text",
            "url": clean,
            "durable": False,
        }
    return {
        "success": True,
        "url": clean,
        "title": title.strip()[:200],
        "body": body,
        "durable": False,  # fetch alone is not a library write
    }


def parse_curriculum_bullets(outline: str) -> List[str]:
    """Split curriculum outline into non-empty bullet/line items."""
    items: List[str] = []
    for line in (outline or "").splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        cleaned = re.sub(r"^[-*•]+\s*", "", cleaned)
        cleaned = re.sub(r"^\d+[.)]\s*", "", cleaned)
        cleaned = cleaned.strip()
        if cleaned:
            items.append(cleaned)
    return items


def _render_education_note(
    *,
    title: str,
    topic: str,
    template_slug: str,
    body: str,
    source_url: Optional[str] = None,
    curriculum_item: Optional[str] = None,
) -> str:
    tmpl = get_education_template(template_slug)
    stamp = _iso_now()
    if tmpl and tmpl.get("content"):
        content = str(tmpl["content"]).replace("${TITLE}", title)
        # Replace placeholder uid
        content = content.replace('uid: "YYYYMMDD-HHMMSS"', f'uid: "{stamp.replace("-", "").replace(":", "")}"')
        # Soft-fill title frontmatter
        content = re.sub(
            r'(?m)^title:\s*"[^"]*"\s*$',
            f'title: "{title.replace(chr(34), "")}"',
            content,
            count=1,
        )
        content = re.sub(
            r"(?m)^status:\s*\"template\"\s*$",
            'status: "inbox"',
            content,
            count=1,
        )
    else:
        content = (
            f"---\n"
            f'title: "{title}"\n'
            f'template: "{template_slug}"\n'
            f'domain: "education"\n'
            f'topic: "{_slugify(topic)}"\n'
            f'tags: ["education", "{template_slug}"]\n'
            f'status: "inbox"\n'
            f"---\n\n"
            f"# {title}\n\n"
        )

    extras: List[str] = ["\n---\n\n## Curated Source\n"]
    extras.append(f"- **Curated at:** {stamp}")
    extras.append(f"- **Skill:** `{SKILL_ID}`")
    extras.append(f"- **Topic:** {topic}")
    if source_url:
        extras.append(f"- **Source URL:** {source_url}")
    if curriculum_item:
        extras.append(f"- **Curriculum item:** {curriculum_item}")
    extras.append("\n## Extract / Outline\n")
    extras.append(body.strip() or "_(empty)_")
    extras.append("\n")
    return content.rstrip() + "\n" + "\n".join(extras)


def _render_raw_source_note(
    *,
    title: str,
    topic: str,
    body: str,
    source_url: Optional[str] = None,
) -> str:
    stamp = _iso_now()
    tags = ["source", "curation", "raw"]
    fm_tags = ", ".join(f'"{t}"' for t in tags)
    lines = [
        "---",
        f'title: "{title.replace(chr(34), "")}"',
        f'template: "{RAW_SOURCE_TEMPLATE}"',
        'domain: "general"',
        f'topic: "{_slugify(topic, fallback="source")}"',
        f"tags: [{fm_tags}]",
        'document_type: "source_note"',
        'status: "inbox"',
        f'curated_at: "{stamp}"',
        f'curation_skill: "{SKILL_ID}"',
        "---",
        "",
        f"# {title}",
        "",
        "> Raw / source note (no education tags). Catalogued education templates were not forced.",
        "",
    ]
    if source_url:
        lines.extend([f"**Source URL:** {source_url}", ""])
    lines.extend(["## Source Text", "", body.strip() or "_(empty)_", ""])
    return "\n".join(lines)


def _create_note(
    wiki_tools: Any,
    *,
    title: str,
    content: str,
    topic: str,
    tags: Sequence[str],
    template: str,
    summary: str,
    domain: str,
    document_type: str,
) -> Dict[str, Any]:
    if wiki_tools is None:
        return {"success": False, "error": "no_wiki_tools", "durable": False}
    if not hasattr(wiki_tools, "create_wiki_note") and not hasattr(wiki_tools, "wiki_note_create"):
        return {"success": False, "error": "wiki_note_create unavailable", "durable": False}

    create = getattr(wiki_tools, "create_wiki_note", None) or getattr(wiki_tools, "wiki_note_create")
    try:
        result = create(
            title=title,
            content=content,
            domain=domain,
            topic=_slugify(topic),
            category="inbox",
            tags=list(tags),
            summary=summary,
            document_type=document_type,
            template=template,
            extra_frontmatter={"template": template, "curation_skill": SKILL_ID},
        )
    except Exception as exc:  # noqa: BLE001 - honest wiki write failure
        return {"success": False, "error": f"wiki write failed: {exc}", "durable": False}

    if not isinstance(result, dict):
        return {"success": False, "error": "wiki write returned non-dict", "durable": False}

    path = str(result.get("path") or result.get("relative_path") or "")
    ok = bool(result.get("success")) and bool(path)
    out = dict(result)
    out["success"] = ok
    out["durable"] = ok
    out["path"] = path
    out["relative_path"] = path
    if not ok and not out.get("error"):
        out["error"] = "wiki_note_create did not return a path"
        out["durable"] = False
    return out


def curate_from_link(
    wiki_tools: Any,
    *,
    url: str,
    topic: str = "",
    title: Optional[str] = None,
    template: Optional[str] = None,
    raw_source: bool = False,
    body: Optional[str] = None,
    opener: Optional[Callable[[str], bytes]] = None,
) -> Dict[str, Any]:
    """Curate one link into a durable Wiki note via wiki_note_create."""
    clean_url = (url or "").strip()
    topic_clean = (topic or "").strip() or "untitled"

    fetched_body = (body or "").strip()
    fetched_title = (title or "").strip()
    if not fetched_body:
        fetched = fetch_link_text(clean_url, opener=opener)
        if not fetched.get("success"):
            return {
                "success": False,
                "durable": False,
                "mode": "link",
                "url": clean_url,
                "error": fetched.get("error") or "fetch failed",
                "skill_hint": SKILL_ID,
                "http_contract": HTTP_CONTRACT,
                "notes": [],
            }
        fetched_body = str(fetched.get("body") or "")
        if not fetched_title:
            fetched_title = str(fetched.get("title") or "").strip()

    note_title = fetched_title or f"Source: {clean_url}"
    note_title = note_title[:180]

    # raw_source => omit education tags (REQ-440-002).
    # Explicit template wins unless raw_source is forced.
    # Default (Tutor education mode): education-concept.
    if raw_source:
        use_raw = True
    elif (template or "").strip():
        use_raw = False
    else:
        use_raw = False
        template = DEFAULT_EDUCATION_TEMPLATE

    if use_raw:
        content = _render_raw_source_note(
            title=note_title,
            topic=topic_clean,
            body=fetched_body,
            source_url=clean_url,
        )
        created = _create_note(
            wiki_tools,
            title=note_title,
            content=content,
            topic=topic_clean,
            tags=["source", "curation", "raw"],
            template=RAW_SOURCE_TEMPLATE,
            summary=f"Raw source curated from {clean_url}",
            domain="general",
            document_type="source_note",
        )
        template_used = RAW_SOURCE_TEMPLATE
        education_tags = False
    else:
        try:
            tpl = assert_education_template_required(template or DEFAULT_EDUCATION_TEMPLATE)
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "durable": False,
                "mode": "link",
                "url": clean_url,
                "error": str(exc),
                "skill_hint": SKILL_ID,
                "http_contract": HTTP_CONTRACT,
                "notes": [],
            }
        content = _render_education_note(
            title=note_title,
            topic=topic_clean,
            template_slug=tpl,
            body=fetched_body,
            source_url=clean_url,
        )
        tags = ["education", "curation", tpl]
        created = _create_note(
            wiki_tools,
            title=note_title,
            content=content,
            topic=topic_clean,
            tags=tags,
            template=tpl,
            summary=f"Education note curated from {clean_url}",
            domain="education",
            document_type="education_note",
        )
        template_used = tpl
        education_tags = True

    note = {
        "path": created.get("path") or "",
        "title": note_title,
        "template": template_used,
        "education_tags": education_tags,
        "raw_source": use_raw,
    }
    ok = bool(created.get("success")) and bool(note["path"])
    return {
        "success": ok,
        "durable": ok,
        "mode": "link",
        "url": clean_url,
        "topic": topic_clean,
        "template": template_used,
        "education_tags": education_tags,
        "raw_source": use_raw,
        "notes": [note] if ok else [],
        "path": note["path"] if ok else "",
        "error": None if ok else (created.get("error") or "wiki write failed"),
        "skill_hint": SKILL_ID,
        "http_contract": HTTP_CONTRACT,
        "vault_root": created.get("vault_root"),
    }


def curate_from_curriculum(
    wiki_tools: Any,
    *,
    curriculum: str,
    topic: str = "",
    template: Optional[str] = None,
    raw_source: bool = False,
    max_items: int = 12,
) -> Dict[str, Any]:
    """Curate curriculum bullet list into durable Wiki note(s)."""
    topic_clean = (topic or "").strip() or "curriculum"
    items = parse_curriculum_bullets(curriculum)
    if not items:
        return {
            "success": False,
            "durable": False,
            "mode": "curriculum",
            "topic": topic_clean,
            "error": "curriculum outline is empty",
            "skill_hint": SKILL_ID,
            "http_contract": HTTP_CONTRACT,
            "notes": [],
        }

    items = items[: max(1, min(int(max_items or 12), 30))]
    notes: List[Dict[str, Any]] = []
    errors: List[str] = []

    if raw_source:
        # One raw outline note without education tags
        title = f"Curriculum source: {topic_clean}"
        body = "\n".join(f"- {it}" for it in items)
        content = _render_raw_source_note(
            title=title,
            topic=topic_clean,
            body=body,
            source_url=None,
        )
        created = _create_note(
            wiki_tools,
            title=title,
            content=content,
            topic=topic_clean,
            tags=["source", "curation", "raw", "curriculum"],
            template=RAW_SOURCE_TEMPLATE,
            summary=f"Raw curriculum outline for {topic_clean}",
            domain="general",
            document_type="source_note",
        )
        if created.get("success") and created.get("path"):
            notes.append(
                {
                    "path": created.get("path"),
                    "title": title,
                    "template": RAW_SOURCE_TEMPLATE,
                    "education_tags": False,
                    "raw_source": True,
                }
            )
        else:
            errors.append(str(created.get("error") or "wiki write failed"))
    else:
        try:
            tpl = assert_education_template_required(template or DEFAULT_EDUCATION_TEMPLATE)
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "durable": False,
                "mode": "curriculum",
                "topic": topic_clean,
                "error": str(exc),
                "skill_hint": SKILL_ID,
                "http_contract": HTTP_CONTRACT,
                "notes": [],
            }
        for item in items:
            title = f"{topic_clean}: {item}"[:180]
            content = _render_education_note(
                title=title,
                topic=topic_clean,
                template_slug=tpl,
                body=item,
                curriculum_item=item,
            )
            created = _create_note(
                wiki_tools,
                title=title,
                content=content,
                topic=topic_clean,
                tags=["education", "curation", "curriculum", tpl],
                template=tpl,
                summary=f"Curriculum item for {topic_clean}",
                domain="education",
                document_type="education_note",
            )
            if created.get("success") and created.get("path"):
                notes.append(
                    {
                        "path": created.get("path"),
                        "title": title,
                        "template": tpl,
                        "education_tags": True,
                        "raw_source": False,
                    }
                )
            else:
                errors.append(str(created.get("error") or f"write failed for: {item}"))

    ok = len(notes) > 0 and not errors
    # Partial writes: success only if all requested notes landed (no fake full success)
    if notes and errors:
        ok = False
    elif notes and not errors:
        ok = True
    else:
        ok = False

    return {
        "success": ok,
        "durable": ok and len(notes) > 0,
        "mode": "curriculum",
        "topic": topic_clean,
        "template": None if raw_source else (template or DEFAULT_EDUCATION_TEMPLATE),
        "education_tags": not raw_source,
        "raw_source": raw_source,
        "item_count": len(items),
        "notes": notes,
        "paths": [n["path"] for n in notes],
        "path": notes[0]["path"] if notes else "",
        "error": None if ok else ("; ".join(errors) if errors else "no notes written"),
        "skill_hint": SKILL_ID,
        "http_contract": HTTP_CONTRACT,
        "partial": bool(notes) and bool(errors),
    }


def curate(
    wiki_tools: Any,
    *,
    mode: str,
    url: Optional[str] = None,
    curriculum: Optional[str] = None,
    topic: str = "",
    title: Optional[str] = None,
    template: Optional[str] = None,
    raw_source: bool = False,
    body: Optional[str] = None,
    opener: Optional[Callable[[str], bytes]] = None,
    max_items: int = 12,
) -> Dict[str, Any]:
    """Dispatch link or curriculum curation."""
    clean_mode = (mode or "").strip().lower()
    if clean_mode in ("link", "url", "from_link"):
        if not (url or "").strip() and not (body or "").strip():
            return {
                "success": False,
                "durable": False,
                "mode": "link",
                "error": "url is required for link curation",
                "skill_hint": SKILL_ID,
                "http_contract": HTTP_CONTRACT,
                "notes": [],
            }
        return curate_from_link(
            wiki_tools,
            url=url or "",
            topic=topic,
            title=title,
            template=template,
            raw_source=raw_source,
            body=body,
            opener=opener,
        )
    if clean_mode in ("curriculum", "outline", "from_curriculum"):
        return curate_from_curriculum(
            wiki_tools,
            curriculum=curriculum or "",
            topic=topic,
            template=template,
            raw_source=raw_source,
            max_items=max_items,
        )
    return {
        "success": False,
        "durable": False,
        "mode": clean_mode or "",
        "error": "mode must be 'link' or 'curriculum'",
        "skill_hint": SKILL_ID,
        "http_contract": HTTP_CONTRACT,
        "notes": [],
        "catalog_slugs": sorted(EDUCATION_TEMPLATES.keys()),
    }
