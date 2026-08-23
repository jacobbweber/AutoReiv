"""
WikiStore Core Engine [REQ-WIKI-001, REQ-WIKI-003, REQ-WIKI-004].
Manages local-first plain-text markdown files under the Degree/Class taxonomy.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .frontmatter import FrontmatterParser, WikiNoteMeta

log = logging.getLogger(__name__)

_LINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")
_WORD_PATTERN = re.compile(r"[a-zA-Z0-9_]{3,}")
_SLUG_CLEAN_PATTERN = re.compile(r"[^a-zA-Z0-9_]+")


def slugify(text: str) -> str:
    """Convert text to clean snake_case filename slug."""
    s = text.strip().lower()
    s = _SLUG_CLEAN_PATTERN.sub("_", s).strip("_")
    return s[:80] or f"note_{int(dt.datetime.now().timestamp())}"


class WikiStore:
    """
    Core local-first document storage and indexing engine.
    """

    def __init__(self, root_dir: str | Path = "data/wiki"):
        self.root_dir = Path(root_dir).resolve()

    def scaffold(self) -> None:
        """Ensure standard taxonomy folders exist on disk."""
        directories = [
            self.root_dir / "inbox",
            self.root_dir / "notes",
            self.root_dir / "resources" / "operating_manuals",
            self.root_dir / "resources" / "templates",
        ]
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Optional[Path]:
        """Ensure relative path does not escape root_dir."""
        try:
            target = (self.root_dir / relative_path).resolve()
            if not str(target).startswith(str(self.root_dir)):
                return None
            return target
        except Exception:
            return None

    def file_note(
        self,
        title: str,
        content: str,
        domain: str = "general",
        topic: str = "general",
        category: str = "notes",
        inbox_priority: str = "medium",
        document_type: str = "atomic_note",
        tags: Optional[List[str]] = None,
        summary: str = "",
        status: str = "draft",
        priority: str = "medium",
        sensitivity: str = "internal",
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create and persist a new note with structured YAML frontmatter.
        """
        self.scaffold()
        slug = slugify(title)

        if category.lower() == "inbox" or category.lower().startswith("inbox"):
            rel_path = f"inbox/{slug}.md"
        elif category.lower() == "resources":
            rel_path = f"resources/operating_manuals/{slug}.md"
        else:
            safe_domain = slugify(domain) or "general"
            safe_topic = slugify(topic) or "general"
            rel_path = f"notes/{safe_domain}/{safe_topic}/{slug}.md"

        target_path = self.root_dir / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        meta_kwargs: Dict[str, Any] = {
            "title": title,
            "domain": domain,
            "topic": topic,
            "document_type": document_type,
            "tags": tags or [],
            "summary": summary,
            "status": status,
            "priority": priority,
            "sensitivity": sensitivity,
        }
        if extra_meta:
            meta_kwargs.update(extra_meta)

        meta = WikiNoteMeta(**meta_kwargs)
        full_text = FrontmatterParser.dump(meta, content)
        target_path.write_text(full_text, encoding="utf-8")

        return {
            "success": True,
            "path": rel_path.replace("\\", "/"),
            "title": title,
            "uid": meta.uid,
            "domain": meta.domain,
            "topic": meta.topic,
        }

    def read_note(self, relative_path: str) -> Dict[str, Any]:
        """
        Read a note, extract frontmatter, and return clean content.
        """
        target_path = self._resolve_safe_path(relative_path)
        if target_path is None or not target_path.is_file():
            return {"success": False, "error": f"Note '{relative_path}' not found."}

        raw_text = target_path.read_text(encoding="utf-8", errors="replace")
        meta, body = FrontmatterParser.parse(raw_text)

        # Update last_accessed in-memory representation
        return {
            "success": True,
            "path": relative_path.replace("\\", "/"),
            "meta": meta.model_dump(),
            "content": body,
            "title": meta.title,
        }

    def write_note(
        self,
        relative_path: str,
        content: str,
        update_frontmatter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Non-destructively update an existing note's body, preserving metadata and bumping last_updated.
        """
        target_path = self._resolve_safe_path(relative_path)
        if target_path is None:
            return {"success": False, "error": "Invalid or unsafe path."}

        if target_path.is_file():
            raw_text = target_path.read_text(encoding="utf-8", errors="replace")
            meta, _ = FrontmatterParser.parse(raw_text)
            meta_dict = meta.model_dump()
        else:
            meta_dict = WikiNoteMeta(title=target_path.stem.replace("_", " ")).model_dump()
            target_path.parent.mkdir(parents=True, exist_ok=True)

        if update_frontmatter:
            meta_dict.update(update_frontmatter)

        meta_dict["last_updated"] = dt.datetime.now().strftime("%Y-%m-%d")
        updated_meta = WikiNoteMeta.model_validate(meta_dict)

        full_text = FrontmatterParser.dump(updated_meta, content)
        target_path.write_text(full_text, encoding="utf-8")

        return {
            "success": True,
            "path": relative_path.replace("\\", "/"),
            "uid": updated_meta.uid,
            "title": updated_meta.title,
        }

    def delete_note(self, relative_path: str) -> bool:
        """Delete a note from disk."""
        target_path = self._resolve_safe_path(relative_path)
        if target_path and target_path.is_file():
            target_path.unlink()
            return True
        return False

    def list_notes(self) -> List[Dict[str, Any]]:
        """List all markdown notes across the wiki."""
        if not self.root_dir.is_dir():
            return []

        out = []
        for file_path in sorted(self.root_dir.rglob("*.md")):
            rel = str(file_path.relative_to(self.root_dir)).replace("\\", "/")
            if rel.startswith("."):
                continue
            raw_text = file_path.read_text(encoding="utf-8", errors="replace")
            meta, body = FrontmatterParser.parse(raw_text)
            out.append({
                "path": rel,
                "title": meta.title,
                "domain": meta.domain,
                "topic": meta.topic,
                "document_type": meta.document_type,
                "tags": meta.tags,
                "status": meta.status,
                "summary": meta.summary,
                "preview": body[:200],
                "last_updated": meta.last_updated,
                "word_count": meta.word_count,
                "context_tokens": meta.context_tokens,
            })
        return out

    def search_notes(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Progressive search scoring terms across note titles (2x weight) and body text.
        """
        terms = {w.lower() for w in _WORD_PATTERN.findall(query or "")}
        if not terms:
            return []

        scored = []
        for note in self.list_notes():
            title_words = {w.lower() for w in _WORD_PATTERN.findall(note["title"])}
            body_words = {w.lower() for w in _WORD_PATTERN.findall(note.get("preview", "") + " " + note.get("summary", ""))}
            tag_words = {t.lower() for t in note.get("tags", [])}

            score = (
                len(terms & title_words) * 3
                + len(terms & tag_words) * 2
                + len(terms & body_words)
            )
            if score > 0:
                scored.append((score, note))

        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored[:limit]]

    def get_graph(self) -> Dict[str, Any]:
        """
        Extract [[wikilink]] references across all notes and generate directed graph nodes and edges.
        """
        notes = self.list_notes()
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
            target_path = self._resolve_safe_path(p["path"])
            if not target_path or not target_path.is_file():
                continue
            raw = target_path.read_text(encoding="utf-8", errors="replace")
            _, body = FrontmatterParser.parse(raw)

            for target in _LINK_PATTERN.findall(body):
                target_clean = target.strip()
                t_lower = target_clean.lower()
                dest_note = by_title.get(t_lower) or by_slug.get(slugify(target_clean))
                if dest_note and dest_note["path"] != p["path"]:
                    edges.append({
                        "source": p["path"],
                        "target": dest_note["path"],
                        "target_title": dest_note["title"],
                    })

        return {"nodes": nodes, "edges": edges}

    def get_mindmap(
        self, include_tags: bool = True, include_taxonomy: bool = True
    ) -> Dict[str, Any]:
        """
        Extract multi-dimensional knowledge graph for Obsidian-style Mind Map.
        Returns nodes (note, tag, domain, topic) and typed edges (wikilink, has_tag, in_topic, in_domain).
        """
        self.scaffold()
        notes = self.list_notes()

        by_title = {n["title"].lower(): n for n in notes}
        by_slug = {slugify(n["title"]): n for n in notes}

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        tag_counts: Dict[str, int] = {}
        domain_counts: Dict[str, int] = {}
        topic_counts: Dict[str, int] = {}

        # 1. Note Nodes
        for p in notes:
            nodes.append({
                "id": p["path"],
                "label": p["title"],
                "type": "note",
                "domain": p["domain"],
                "topic": p["topic"],
                "tags": p["tags"],
                "words": p["word_count"],
                "tokens": p["context_tokens"],
                "path": p["path"],
            })

            # Tally tags
            for t in p["tags"]:
                t_clean = t.strip().lower()
                if t_clean:
                    tag_counts[t_clean] = tag_counts.get(t_clean, 0) + 1

            # Tally taxonomy
            if p["domain"]:
                domain_counts[p["domain"]] = domain_counts.get(p["domain"], 0) + 1
            if p["domain"] and p["topic"]:
                top_key = f"{p['domain']}:{p['topic']}"
                topic_counts[top_key] = topic_counts.get(top_key, 0) + 1

        # 2. Tag Nodes & Edges
        if include_tags:
            for tag, count in sorted(tag_counts.items()):
                tag_node_id = f"tag:{tag}"
                nodes.append({
                    "id": tag_node_id,
                    "label": f"#{tag}",
                    "type": "tag",
                    "count": count,
                })

            for p in notes:
                for t in p["tags"]:
                    t_clean = t.strip().lower()
                    if t_clean:
                        edges.append({
                            "source": p["path"],
                            "target": f"tag:{t_clean}",
                            "type": "has_tag",
                            "label": "tagged",
                        })

        # 3. Taxonomy Nodes & Edges
        if include_taxonomy:
            for dom, count in sorted(domain_counts.items()):
                dom_node_id = f"domain:{dom}"
                nodes.append({
                    "id": dom_node_id,
                    "label": f"🎓 {dom}",
                    "type": "domain",
                    "count": count,
                })

            for top_key, count in sorted(topic_counts.items()):
                dom, top = top_key.split(":", 1)
                top_node_id = f"topic:{dom}:{top}"
                nodes.append({
                    "id": top_node_id,
                    "label": f"📖 {top}",
                    "type": "topic",
                    "count": count,
                })
                # Edge topic -> domain
                edges.append({
                    "source": top_node_id,
                    "target": f"domain:{dom}",
                    "type": "in_domain",
                    "label": "part_of",
                })

            for p in notes:
                if p["domain"] and p["topic"]:
                    edges.append({
                        "source": p["path"],
                        "target": f"topic:{p['domain']}:{p['topic']}",
                        "type": "in_topic",
                        "label": "categorized_in",
                    })

        # 4. Wikilink Edges
        for p in notes:
            target_path = self._resolve_safe_path(p["path"])
            if not target_path or not target_path.is_file():
                continue
            raw = target_path.read_text(encoding="utf-8", errors="replace")
            _, body = FrontmatterParser.parse(raw)

            for target in _LINK_PATTERN.findall(body):
                target_clean = target.strip()
                t_lower = target_clean.lower()
                dest_note = by_title.get(t_lower) or by_slug.get(slugify(target_clean))
                if dest_note and dest_note["path"] != p["path"]:
                    edges.append({
                        "source": p["path"],
                        "target": dest_note["path"],
                        "type": "wikilink",
                        "label": "links_to",
                        "target_title": dest_note["title"],
                    })

        return {"nodes": nodes, "edges": edges}

    def get_tree(self) -> Dict[str, Any]:
        """
        Build nested category tree for UI sidebar explorer.
        """
        self.scaffold()
        notes = self.list_notes()

        tree: Dict[str, Any] = {
            "inbox": [],
            "notes": {},  # domain -> topic -> list of notes
            "resources": {
                "operating_manuals": [],
                "templates": [],
            },
        }

        for n in notes:
            path_parts = n["path"].split("/")
            root = path_parts[0]

            if root == "inbox":
                tree["inbox"].append(n)
            elif root == "resources" and len(path_parts) >= 3:
                sub = path_parts[1]
                if sub in tree["resources"]:
                    tree["resources"][sub].append(n)
            elif root == "notes" and len(path_parts) >= 4:
                domain = path_parts[1]
                topic = path_parts[2]
                tree["notes"].setdefault(domain, {}).setdefault(topic, []).append(n)
            elif root == "notes" and len(path_parts) == 3:
                domain = path_parts[1]
                tree["notes"].setdefault(domain, {}).setdefault("general", []).append(n)

        return tree

    def get_overview(self, max_items: int = 20) -> str:
        """
        Generate a compact, prompt-ready text inventory under 150 tokens.
        """
        notes = self.list_notes()
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

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics across the wiki."""
        notes = self.list_notes()
        total_words = sum(n["word_count"] for n in notes)
        total_tokens = sum(n["context_tokens"] for n in notes)
        by_category = {}
        for n in notes:
            root = n["path"].split("/")[0]
            by_category[root] = by_category.get(root, 0) + 1

        return {
            "total_notes": len(notes),
            "total_words": total_words,
            "total_tokens": total_tokens,
            "by_category": by_category,
        }
