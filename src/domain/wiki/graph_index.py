"""Vault listing, search, graph, mindmap, tree, and inventory indexing [CARD-714]."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from .frontmatter import FrontmatterParser
from .templates_catalog import slugify

if TYPE_CHECKING:
    from .store import WikiStore

_LINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")
_WORD_PATTERN = re.compile(r"[a-zA-Z0-9_]{3,}")

_CATEGORY_FOLDERS = {
    "inbox": ("00_inbox/", "inbox/"),
    "notes": ("01_notes/", "notes/"),
    "resources": ("02_resources/", "resources/"),
    "archive": ("03_archive/", "archive/"),
}


def _category_prefixes(category: str) -> tuple:
    """CARD-589: folder prefixes (lower case) for a list category: 'notes' -> 01_Notes/ or legacy notes/."""
    cat = category.lower().strip().strip("/")
    for name, folders in _CATEGORY_FOLDERS.items():
        if cat == name or cat + "/" in folders:
            return folders
    return (cat,)


def list_notes(
    root_dir: Path,
    category: Optional[str] = None,
    domain: Optional[str] = None,
    topic: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    author: Optional[str] = None,
    pinned: Optional[bool] = None,
    priority: Optional[str] = None,
    hidden: Optional[Callable[[str], bool]] = None,
) -> List[Dict[str, Any]]:
    """List markdown notes across the wiki matching folder or frontmatter filters."""
    if not root_dir.is_dir():
        return []

    out: List[Dict[str, Any]] = []
    for file_path in sorted(root_dir.rglob("*.md")):
        rel = str(file_path.relative_to(root_dir)).replace("\\", "/")
        if rel.startswith("."):
            continue
        if hidden is not None and hidden(rel):
            continue

        if category:
            prefixes = _category_prefixes(category)
            if not any(rel.lower().startswith(pfx) for pfx in prefixes):
                continue

        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
        meta, body = FrontmatterParser.parse(raw_text)

        if domain and meta.domain.lower() != domain.lower().strip():
            continue
        if topic and meta.topic.lower() != topic.lower().strip():
            continue
        if status and meta.status.lower() != status.lower().strip():
            continue
        if tag and not any(tag.lower().strip() == t.lower() for t in meta.tags):
            continue
        if author and meta.author.lower() != author.lower().strip():
            continue
        if pinned is not None and meta.pinned != pinned:
            continue
        if priority and meta.priority.lower() != priority.lower().strip():
            continue

        out.append(
            {
                "path": rel,
                "title": meta.title,
                "domain": meta.domain,
                "topic": meta.topic,
                "document_type": meta.document_type,
                "tags": meta.tags,
                "status": meta.status,
                "priority": meta.priority,
                "author": meta.author,
                "pinned": meta.pinned,
                "summary": meta.summary,
                "preview": body[:200],
                "last_updated": meta.last_updated,
                "word_count": meta.word_count,
                "context_tokens": meta.context_tokens,
                "content_hash": meta.content_hash,
            }
        )
    return out


def search_notes(
    root_dir: Path,
    query: str = "",
    limit: int = 5,
    tags: Optional[List[str]] = None,
    domain: Optional[str] = None,
    topic: Optional[str] = None,
    document_type: Optional[str] = None,
    hidden: Optional[Callable[[str], bool]] = None,
) -> List[Dict[str, Any]]:
    """
    Progressive search scoring terms across note titles, tags, and summary snippets,
    with optional structured filtering by tags, domain, topic, and document_type [CARD-353].
    """
    terms = {w.lower() for w in _WORD_PATTERN.findall(query or "")}
    normalized_tags = [t.lower().strip() for t in (tags or []) if t and t.strip()]

    scored = []
    include_templates = document_type == "template" or (domain and "template" in domain.lower())
    for note in list_notes(root_dir, hidden=hidden):
        note_path = str(note.get("path", "")).lower()
        if not include_templates and (
            "_templates" in note_path
            or "templates/" in note_path
            or note_path.endswith("tag-authority.md")
        ):
            continue
        if domain and note.get("domain", "").lower() != domain.lower().strip():
            continue
        if topic and note.get("topic", "").lower() != topic.lower().strip():
            continue
        if document_type and note.get("document_type", "").lower() != document_type.lower().strip():
            continue

        note_tags = [t.lower().strip() for t in note.get("tags", [])]
        if normalized_tags:
            if not any(req_t in note_tags for req_t in normalized_tags):
                continue

        if terms:
            title_words = {w.lower() for w in _WORD_PATTERN.findall(note.get("title", ""))}
            body_words = {
                w.lower() for w in _WORD_PATTERN.findall(note.get("preview", "") + " " + note.get("summary", ""))
            }
            tag_words = set(note_tags)

            score = len(terms & title_words) * 3 + len(terms & tag_words) * 2 + len(terms & body_words)
            if score > 0:
                scored.append((score, note))
        else:
            tag_bonus = sum(1 for req_t in normalized_tags if req_t in note_tags)
            scored.append((1 + tag_bonus, note))

    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:limit]]


def _scan_non_template_notes_with_links(root_dir: Path) -> List[Dict[str, Any]]:
    """Single-pass scan of non-template vault notes extracting metadata and [[wikilinks]] [CARD-714]."""
    if not root_dir.is_dir():
        return []

    notes: List[Dict[str, Any]] = []
    for file_path in sorted(root_dir.rglob("*.md")):
        rel = str(file_path.relative_to(root_dir)).replace("\\", "/")
        if rel.startswith(".") or "_Templates" in rel or "templates" in rel:
            continue
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
        meta, body = FrontmatterParser.parse(raw_text)
        links = [target.strip() for target in _LINK_PATTERN.findall(body)]
        notes.append(
            {
                "path": rel,
                "title": meta.title,
                "domain": meta.domain,
                "topic": meta.topic,
                "tags": meta.tags,
                "word_count": meta.word_count,
                "context_tokens": meta.context_tokens,
                "_links": links,
            }
        )
    return notes


def get_graph(store: "WikiStore") -> Dict[str, Any]:
    """
    Extract [[wikilink]] references across all notes and generate directed graph nodes and edges.
    Reads and parses each non-template note once per call [CARD-714].
    """
    notes = _scan_non_template_notes_with_links(store.root_dir)
    by_slug = {p["path"].rsplit("/", 1)[-1][:-3].lower(): p for p in notes}
    by_title = {p["title"].lower(): p for p in notes}

    nodes = [
        {
            "id": p["path"],
            "title": p["title"],
            "domain": p["domain"],
            "topic": p["topic"],
            "size": max(1, p["word_count"] // 100),
        }
        for p in notes
    ]

    edges = []
    for p in notes:
        for target_clean in p["_links"]:
            t_lower = target_clean.lower()
            dest_note = by_title.get(t_lower) or by_slug.get(slugify(target_clean))
            if dest_note and dest_note["path"] != p["path"]:
                edges.append(
                    {
                        "source": p["path"],
                        "target": dest_note["path"],
                        "target_title": dest_note["title"],
                    }
                )

    return {"nodes": nodes, "edges": edges}


def get_mindmap(
    store: "WikiStore",
    include_tags: bool = True,
    include_taxonomy: bool = True,
) -> Dict[str, Any]:
    """
    Extract multi-dimensional knowledge graph for Obsidian-style Mind Map.
    Reads and parses each non-template note once per call [CARD-714].
    """
    store.scaffold()
    notes = _scan_non_template_notes_with_links(store.root_dir)

    by_title = {n["title"].lower(): n for n in notes}
    by_slug = {slugify(n["title"]): n for n in notes}

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    tag_counts: Dict[str, int] = {}
    domain_counts: Dict[str, int] = {}
    topic_counts: Dict[str, int] = {}

    # 1. Note Nodes
    for p in notes:
        nodes.append(
            {
                "id": p["path"],
                "label": p["title"],
                "type": "note",
                "domain": p["domain"],
                "topic": p["topic"],
                "tags": p["tags"],
                "words": p["word_count"],
                "tokens": p["context_tokens"],
                "path": p["path"],
            }
        )

        for t in p["tags"]:
            t_clean = t.strip().lower()
            if t_clean:
                tag_counts[t_clean] = tag_counts.get(t_clean, 0) + 1

        if p["domain"]:
            domain_counts[p["domain"]] = domain_counts.get(p["domain"], 0) + 1
        if p["domain"] and p["topic"]:
            top_key = f"{p['domain']}:{p['topic']}"
            topic_counts[top_key] = topic_counts.get(top_key, 0) + 1

    # 2. Tag Nodes & Edges
    if include_tags:
        for tag, count in sorted(tag_counts.items()):
            tag_node_id = f"tag:{tag}"
            nodes.append(
                {
                    "id": tag_node_id,
                    "label": f"#{tag}",
                    "type": "tag",
                    "count": count,
                }
            )

        for p in notes:
            for t in p["tags"]:
                t_clean = t.strip().lower()
                if t_clean:
                    edges.append(
                        {
                            "source": p["path"],
                            "target": f"tag:{t_clean}",
                            "type": "has_tag",
                            "label": "tagged",
                        }
                    )

    # 3. Taxonomy Nodes & Edges
    if include_taxonomy:
        for dom, count in sorted(domain_counts.items()):
            dom_node_id = f"domain:{dom}"
            nodes.append(
                {
                    "id": dom_node_id,
                    "label": f"🎓 {dom}",
                    "type": "domain",
                    "count": count,
                }
            )

        for top_key, count in sorted(topic_counts.items()):
            dom, top = top_key.split(":", 1)
            top_node_id = f"topic:{dom}:{top}"
            nodes.append(
                {
                    "id": top_node_id,
                    "label": f"📖 {top}",
                    "type": "topic",
                    "count": count,
                }
            )
            edges.append(
                {
                    "source": top_node_id,
                    "target": f"domain:{dom}",
                    "type": "in_domain",
                    "label": "part_of",
                }
            )

        for p in notes:
            if p["domain"] and p["topic"]:
                edges.append(
                    {
                        "source": p["path"],
                        "target": f"topic:{p['domain']}:{p['topic']}",
                        "type": "in_topic",
                        "label": "categorized_in",
                    }
                )

    # 4. Wikilink Edges (using links extracted during the single file read)
    for p in notes:
        for target_clean in p["_links"]:
            t_lower = target_clean.lower()
            dest_note = by_title.get(t_lower) or by_slug.get(slugify(target_clean))
            if dest_note and dest_note["path"] != p["path"]:
                edges.append(
                    {
                        "source": p["path"],
                        "target": dest_note["path"],
                        "type": "wikilink",
                        "label": "links_to",
                        "target_title": dest_note["title"],
                    }
                )

    return {"nodes": nodes, "edges": edges}


def get_tree(store: "WikiStore") -> Dict[str, Any]:
    """Build nested category tree for UI sidebar explorer."""
    store.scaffold()
    notes = list_notes(store.root_dir)

    tree: Dict[str, Any] = {
        "inbox": [],
        "notes": {},
        "resources": {
            "operating_manuals": [],
            "templates": [],
        },
        "archive": [],
        "00_Inbox": [],
        "01_Notes": {},
        "02_Resources": {
            "operating_manuals": [],
            "templates": [],
        },
        "03_Archive": [],
    }

    for n in notes:
        path_parts = n["path"].split("/")
        raw_root = path_parts[0]
        clean_root = re.sub(r"^\d+_", "", raw_root).lower()

        if clean_root == "inbox" or raw_root.lower() == "inbox":
            tree["inbox"].append(n)
            tree["00_Inbox"].append(n)
        elif clean_root in ("resources", "templates", "operating_manuals") or raw_root.lower() == "resources":
            sub = "operating_manuals"
            if len(path_parts) >= 3:
                sub = re.sub(r"^\d+_", "", path_parts[1]).lower()
                if sub.startswith("_"):
                    sub = sub.lstrip("_").lower()
            elif clean_root in ("templates", "_templates"):
                sub = "templates"
            tree["resources"].setdefault(sub, []).append(n)
            tree["02_Resources"].setdefault(sub, []).append(n)
        elif clean_root == "archive" or raw_root.lower() == "archive":
            tree["archive"].append(n)
            tree["03_Archive"].append(n)
        elif clean_root in ("notes", "projects", "areas") or raw_root.lower() == "notes":
            if len(path_parts) >= 4:
                domain = path_parts[1]
                topic = path_parts[2]
            elif len(path_parts) == 3:
                domain = path_parts[1]
                topic = n.get("topic") if n.get("topic") and n.get("topic") != "general" else domain
            elif len(path_parts) == 2:
                domain = "general"
                topic = n.get("topic") or "general"
            else:
                domain = "general"
                topic = "general"
            tree["notes"].setdefault(domain, {}).setdefault(topic, []).append(n)
            tree["01_Notes"].setdefault(domain, {}).setdefault(topic, []).append(n)
        else:
            domain = raw_root
            topic = path_parts[1] if len(path_parts) >= 3 else "general"
            tree["notes"].setdefault(domain, {}).setdefault(topic, []).append(n)
            tree["01_Notes"].setdefault(domain, {}).setdefault(topic, []).append(n)

    return tree


def get_overview(root_dir: Path, max_items: int = 20, hidden: Optional[Callable[[str], bool]] = None) -> str:
    """Generate a compact, prompt-ready text inventory under 150 tokens."""
    notes = list_notes(root_dir, hidden=hidden)
    if not notes:
        return "Wiki is currently empty. Direct the Librarian to file notes."

    lines = [f"Wiki Vault: {len(notes)} total notes."]
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for n in notes:
        root = n["path"].split("/")[0]
        by_cat.setdefault(root, []).append(n)

    for cat, items in sorted(by_cat.items()):
        lines.append(f"- {cat}/ ({len(items)} notes):")
        for item in items[: max(2, max_items // max(1, len(by_cat)))]:
            lines.append(f"  * {item['title']} (path: {item['path']})")

    return "\n".join(lines)


def get_stats(root_dir: Path) -> Dict[str, Any]:
    """Return aggregate statistics across the wiki."""
    notes = list_notes(root_dir)
    total_words = sum(n["word_count"] for n in notes)
    total_tokens = sum(n["context_tokens"] for n in notes)
    by_category: Dict[str, int] = {}
    for n in notes:
        root = n["path"].split("/")[0]
        by_category[root] = by_category.get(root, 0) + 1

    return {
        "total_notes": len(notes),
        "total_words": total_words,
        "total_tokens": total_tokens,
        "by_category": by_category,
    }
