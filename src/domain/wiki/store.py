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

    def __init__(self, root_dir: str | Path = "data/wiki", auto_seed: bool = False):
        self.root_dir = Path(root_dir).resolve()
        self.auto_seed = auto_seed

    def scaffold(self, seed_starter: Optional[bool] = None) -> None:
        """Ensure standard taxonomy folders exist on disk and optionally seed starter notes."""
        directories = [
            self.root_dir / "inbox",
            self.root_dir / "notes",
            self.root_dir / "notes" / "computer_science" / "artificial_intelligence",
            self.root_dir / "notes" / "systems_engineering" / "observability",
            self.root_dir / "resources" / "operating_manuals",
            self.root_dir / "resources" / "templates",
        ]
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)

        should_seed = self.auto_seed if seed_starter is None else seed_starter
        if should_seed:
            self._seed_starter_notes_if_empty()

    def _seed_starter_notes_if_empty(self) -> None:
        """Seed default knowledge vault notes if no markdown files exist."""
        existing_md = list(self.root_dir.rglob("*.md"))
        if existing_md:
            return

        # 1. Inbox Staging Note
        inbox_note = (
            "---\n"
            "title: Welcome to AutoReiv Knowledge Vault\n"
            "domain: general\n"
            "topic: onboarding\n"
            "category: inbox\n"
            "document_type: atomic_note\n"
            "status: draft\n"
            "priority: high\n"
            "sensitivity: internal\n"
            "tags: [onboarding, guide, getting-started]\n"
            "created_at: 2026-08-24T00:00:00Z\n"
            "updated_at: 2026-08-24T00:00:00Z\n"
            "---\n\n"
            "# Welcome to AutoReiv Knowledge Vault\n\n"
            "Welcome to the **AutoReiv Distributed Knowledge Vault**! This vault organizes notes following a streamlined PARA and Dewey-inspired taxonomy:\n\n"
            "- **Inbox**: Flat staging ground for raw captures, agent thoughts, and quick ideas.\n"
            "- **Notes (Warehouse)**: Long-term hierarchical knowledge categorized by domain and topic.\n"
            "- **Resources**: Reference operating manuals, blueprints, and reusable markdown templates.\n\n"
            "Use the **Librarian Agent** to organize staged inbox notes, extract entities, and hydrate YAML frontmatter.\n"
        )
        (self.root_dir / "inbox" / "welcome_to_autoreiv.md").write_text(inbox_note, encoding="utf-8")

        # 2. Computer Science Note
        ai_note = (
            "---\n"
            "title: Local Agent Architecture & Bounded Loops\n"
            "domain: computer_science\n"
            "topic: artificial_intelligence\n"
            "category: notes\n"
            "document_type: atomic_note\n"
            "status: active\n"
            "priority: high\n"
            "sensitivity: internal\n"
            "tags: [agents, architecture, react, memory]\n"
            "created_at: 2026-08-24T00:00:00Z\n"
            "updated_at: 2026-08-24T00:00:00Z\n"
            "---\n\n"
            "# Local Agent Architecture & Bounded Loops\n\n"
            "AutoReiv coordinates localized autonomous agents with deterministic tools and bounded loops.\n\n"
            "## Architectural Invariants\n"
            "1. **Stateless ReAct Loops**: Bounded step execution preventing runaway LLM cycles.\n"
            "2. **Multi-Provider LLM Gateway**: Unified routing across Ollama, OpenAI, and Claude.\n"
            "3. **Scoped Episodic Memory**: Fast SQLite WAL indexing and vector retrieval.\n\n"
            "See also: [[telemetry_and_metrics]] and [[librarian_workflow_manual]].\n"
        )
        (
            self.root_dir / "notes" / "computer_science" / "artificial_intelligence" / "local_agent_architecture.md"
        ).write_text(ai_note, encoding="utf-8")

        # 3. Systems Engineering Note
        obs_note = (
            "---\n"
            "title: Telemetry, Observability & Live Event Streams\n"
            "domain: systems_engineering\n"
            "topic: observability\n"
            "category: notes\n"
            "document_type: atomic_note\n"
            "status: active\n"
            "priority: medium\n"
            "sensitivity: internal\n"
            "tags: [observability, telemetry, events, metrics]\n"
            "created_at: 2026-08-24T00:00:00Z\n"
            "updated_at: 2026-08-24T00:00:00Z\n"
            "---\n\n"
            "# Telemetry, Observability & Live Event Streams\n\n"
            "AutoReiv streams sub-millisecond execution logs and telemetry events via FastAPI Server-Sent Events (SSE).\n\n"
            "## Key Metrics Tracked\n"
            "- **Token Usage**: Prompt tokens, completion tokens, and estimated cost.\n"
            "- **Execution Latency**: Wall-clock duration per turn and tool invocation.\n"
            "- **Memory Compaction**: Automatic context compaction when token budgets exceed thresholds.\n"
        )
        (self.root_dir / "notes" / "systems_engineering" / "observability" / "telemetry_and_metrics.md").write_text(
            obs_note, encoding="utf-8"
        )

        # 4. Resources: Operating Manual
        lib_manual = (
            "---\n"
            "title: Librarian Agent Operating Manual\n"
            "domain: general\n"
            "topic: operations\n"
            "category: resources\n"
            "document_type: operating_manual\n"
            "status: active\n"
            "priority: medium\n"
            "sensitivity: internal\n"
            "tags: [manual, librarian, workflow, curation]\n"
            "created_at: 2026-08-24T00:00:00Z\n"
            "updated_at: 2026-08-24T00:00:00Z\n"
            "---\n\n"
            "# Librarian Agent Operating Manual\n\n"
            "This manual specifies the operational procedures for knowledge ingestion, note filing, and taxonomy reorganization.\n\n"
            "## Standard Ingestion Pipeline\n"
            "1. **Stage Raw Note**: Write raw markdown content to `data/wiki/inbox/`.\n"
            "2. **Hydrate Frontmatter**: Inject domain, topic, summary, and semantic tags.\n"
            "3. **File to Warehouse**: Move note from `inbox/` to `notes/{domain}/{topic}/`.\n"
        )
        (self.root_dir / "resources" / "operating_manuals" / "librarian_workflow_manual.md").write_text(
            lib_manual, encoding="utf-8"
        )

        # 5. Resources: Template
        template_note = (
            "---\n"
            "title: Standard Atomic Note Template\n"
            "domain: general\n"
            "topic: templates\n"
            "category: resources\n"
            "document_type: template\n"
            "status: draft\n"
            "priority: low\n"
            "sensitivity: internal\n"
            "tags: [template, markdown, standard]\n"
            "created_at: 2026-08-24T00:00:00Z\n"
            "updated_at: 2026-08-24T00:00:00Z\n"
            "---\n\n"
            "# ${TITLE}\n\n"
            "## Context\n"
            "${CONTEXT}\n\n"
            "## Details\n"
            "${DETAILS}\n\n"
            "## References\n"
            "- [[local_agent_architecture]]\n"
        )
        (self.root_dir / "resources" / "templates" / "standard_note_template.md").write_text(
            template_note, encoding="utf-8"
        )

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

    def organize_note(
        self,
        source_path: str,
        target_domain: str,
        target_topic: str,
        document_type: str = "atomic_note",
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        new_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Move a note (e.g. from inbox/ to notes/<domain>/<topic>/) and hydrate frontmatter.
        """
        source_file = self._resolve_safe_path(source_path)
        if not source_file or not source_file.is_file():
            return {"success": False, "error": f"Source note '{source_path}' does not exist."}

        raw_text = source_file.read_text(encoding="utf-8", errors="replace")
        meta, body = FrontmatterParser.parse(raw_text)
        meta_dict = meta.model_dump()

        safe_domain = _SLUG_CLEAN_PATTERN.sub("_", (target_domain or "general").lower()).strip("_")
        safe_topic = _SLUG_CLEAN_PATTERN.sub("_", (target_topic or "general").lower()).strip("_")
        slug = source_file.stem

        target_rel = f"notes/{safe_domain}/{safe_topic}/{slug}.md"
        target_file = self._resolve_safe_path(target_rel)
        if target_file is None:
            return {"success": False, "error": "Invalid destination path."}

        # Update metadata
        meta_dict["domain"] = safe_domain
        meta_dict["topic"] = safe_topic
        meta_dict["category"] = "notes"
        meta_dict["document_type"] = document_type
        meta_dict["inbox_priority"] = ""
        meta_dict["status"] = "published"
        if new_title:
            meta_dict["title"] = new_title
        if summary:
            meta_dict["summary"] = summary
        if tags is not None:
            meta_dict["tags"] = tags
        meta_dict["last_updated"] = dt.datetime.now().strftime("%Y-%m-%d")

        word_count = len(body.split())
        meta_dict["word_count"] = word_count
        meta_dict["context_tokens"] = int(word_count * 1.3)

        updated_meta = WikiNoteMeta.model_validate(meta_dict)
        full_text = FrontmatterParser.dump(updated_meta, body)

        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(full_text, encoding="utf-8")

        # Remove source if different from destination
        if source_file.resolve() != target_file.resolve():
            source_file.unlink(missing_ok=True)

        return {
            "success": True,
            "source_path": source_path,
            "target_path": target_rel,
            "title": updated_meta.title,
            "domain": safe_domain,
            "topic": safe_topic,
            "document_type": updated_meta.document_type,
            "tags": updated_meta.tags,
            "summary": updated_meta.summary,
        }

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
            out.append(
                {
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
                }
            )
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
            body_words = {
                w.lower() for w in _WORD_PATTERN.findall(note.get("preview", "") + " " + note.get("summary", ""))
            }
            tag_words = {t.lower() for t in note.get("tags", [])}

            score = len(terms & title_words) * 3 + len(terms & tag_words) * 2 + len(terms & body_words)
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
                    edges.append(
                        {
                            "source": p["path"],
                            "target": dest_note["path"],
                            "target_title": dest_note["title"],
                        }
                    )

        return {"nodes": nodes, "edges": edges}

    def get_mindmap(self, include_tags: bool = True, include_taxonomy: bool = True) -> Dict[str, Any]:
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
                # Edge topic -> domain
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
            raw_root = path_parts[0]
            clean_root = re.sub(r"^\d+_", "", raw_root).lower()

            if clean_root == "inbox" or raw_root.lower() == "inbox":
                tree["inbox"].append(n)
            elif clean_root in ("resources", "templates", "operating_manuals") or raw_root.lower() == "resources":
                if len(path_parts) >= 3:
                    sub = re.sub(r"^\d+_", "", path_parts[1]).lower()
                    tree["resources"].setdefault(sub, []).append(n)
                elif clean_root == "templates":
                    tree["resources"]["templates"].append(n)
                elif clean_root == "operating_manuals":
                    tree["resources"]["operating_manuals"].append(n)
                else:
                    tree["resources"].setdefault("general", []).append(n)
            elif clean_root in ("notes", "projects", "areas", "archive") or raw_root.lower() == "notes":
                if len(path_parts) >= 4:
                    domain = path_parts[1]
                    topic = path_parts[2]
                    tree["notes"].setdefault(domain, {}).setdefault(topic, []).append(n)
                elif len(path_parts) == 3:
                    domain = path_parts[1]
                    topic = n.get("topic") if n.get("topic") and n.get("topic") != "general" else domain
                    tree["notes"].setdefault(domain, {}).setdefault(topic, []).append(n)
                elif len(path_parts) == 2:
                    domain = "general"
                    topic = n.get("topic") or "general"
                    tree["notes"].setdefault(domain, {}).setdefault(topic, []).append(n)
            else:
                # Any other custom directory
                domain = raw_root
                topic = path_parts[1] if len(path_parts) >= 3 else "general"
                tree["notes"].setdefault(domain, {}).setdefault(topic, []).append(n)

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
