"""
WikiStore Core Engine [REQ-WIKI-001, REQ-WIKI-003, REQ-WIKI-004].
Manages local-first plain-text markdown files under the Degree/Class taxonomy.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .frontmatter import (
    FrontmatterParser,
    WikiInboxNoteMeta,
    WikiNoteMeta,
    clean_note_content,
    compute_content_hash,
    compute_context_tokens,
    compute_word_count,
)

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
        """Ensure standard CARD-173 numbered taxonomy folders exist on disk and seed canonical assets."""
        directories = [
            self.root_dir / "00_Inbox",
            self.root_dir / "01_Notes",
            self.root_dir / "01_Notes" / "computer_science" / "artificial_intelligence",
            self.root_dir / "01_Notes" / "systems_engineering" / "observability",
            self.root_dir / "01_Notes" / "operations" / "worklog",
            self.root_dir / "01_Notes" / "operations" / "diagnostics",
            self.root_dir / "01_Notes" / "general" / "notes",
            self.root_dir / "02_Resources" / "operating_manuals",
            self.root_dir / "02_Resources" / "_Templates",
            self.root_dir / "03_Archive",
        ]
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)

        # Ensure canonical Tag Authority exists
        tag_auth = self.root_dir / "02_Resources" / "_Templates" / "tag-authority.md"
        if not tag_auth.exists():
            tag_auth_content = (
                "---\n"
                "title: \"Wiki Tag Authority\"\n"
                "document_type: \"authority\"\n"
                "domain: \"general\"\n"
                "topic: \"templates\"\n"
                "status: \"active\"\n"
                "tags: [\"authority\", \"metadata\", \"taxonomy\"]\n"
                "---\n\n"
                "# Wiki Tag Authority\n\n"
                "Canonical registry of approved tags across domains. Check this list before adding new tags. If a novel concept is needed, register it here.\n\n"
                "## Domains & Approved Tags\n\n"
                "### systems_engineering\n"
                "- `hyperv`\n"
                "- `virtualization`\n"
                "- `powershell`\n"
                "- `networking`\n"
                "- `infrastructure`\n"
                "- `storage`\n\n"
                "### computer_science\n"
                "- `ai_engineering`\n"
                "- `agents`\n"
                "- `rag`\n"
                "- `llm`\n"
                "- `memory`\n"
                "- `architecture`\n\n"
                "### operations\n"
                "- `worklog`\n"
                "- `diagnostics`\n"
                "- `telemetry`\n"
                "- `observability`\n\n"
                "### general\n"
                "- `guide`\n"
                "- `onboarding`\n"
                "- `reference`\n"
                "- `template`\n"
                "- `notes`\n"
            )
            tag_auth.write_text(tag_auth_content, encoding="utf-8")

        # Ensure canonical note template exists
        note_tmpl = self.root_dir / "02_Resources" / "_Templates" / "note_template.md"
        if not note_tmpl.exists():
            tmpl_content = (
                "---\n"
                "uid: \"YYYYMMDD-HHMMSS\"\n"
                "title: \"Standard Note Template\"\n"
                "aliases: []\n"
                "document_type: \"template\"\n"
                "domain: \"general\"\n"
                "topic: \"notes\"\n"
                "tags: []\n"
                "summary: \"1-2 sentence overview of this note.\"\n"
                "status: \"template\"\n"
                "priority: \"medium\"\n"
                "sensitivity: \"internal\"\n"
                "confidence_score: 1.0\n"
                "pinned: false\n"
                "parent: \"\"\n"
                "related: []\n"
                "moc: \"\"\n"
                "source: \"manual\"\n"
                "author: \"assistant\"\n"
                "model: \"\"\n"
                "content_hash: \"\"\n"
                "date_created: \"YYYY-MM-DD\"\n"
                "last_updated: \"YYYY-MM-DD\"\n"
                "last_accessed: \"YYYY-MM-DD\"\n"
                "access_count: 0\n"
                "word_count: 0\n"
                "context_tokens: 0\n"
                "schema_version: \"1.0\"\n"
                "---\n\n"
                "# ${TITLE}\n\n"
                "## Context\n"
                "${CONTEXT}\n\n"
                "## Details\n"
                "${DETAILS}\n\n"
                "## References\n"
                "- [[local_agent_architecture]]\n"
            )
            note_tmpl.write_text(tmpl_content, encoding="utf-8")

        should_seed = self.auto_seed if seed_starter is None else seed_starter
        if should_seed:
            self._seed_starter_notes_if_empty()

    def _seed_starter_notes_if_empty(self) -> None:
        """Seed default knowledge vault notes if no markdown files exist."""
        existing_md = [
            f for f in self.root_dir.rglob("*.md")
            if "_Templates" not in f.parts and "templates" not in f.parts
        ]
        if existing_md:
            return

        # 1. Inbox Staging Note
        inbox_note = (
            "---\n"
            "uid: \"20260824-000000\"\n"
            "title: Welcome to AutoReiv Knowledge Vault\n"
            "domain: general\n"
            "topic: onboarding\n"
            "status: inbox\n"
            "document_type: note\n"
            "tags: [onboarding, guide, getting-started]\n"
            "date_created: \"2026-08-24\"\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# Welcome to AutoReiv Knowledge Vault\n\n"
            "Welcome to the **AutoReiv Distributed Knowledge Vault**! This vault organizes notes following Jacob's PARA-Wiki architecture:\n\n"
            "- **00_Inbox**: Flat staging ground for raw captures, agent thoughts, and quick ideas.\n"
            "- **01_Notes**: Long-term hierarchical knowledge categorized by domain and topic (Degree rule).\n"
            "- **02_Resources**: Reference operating manuals and reusable templates (_Templates).\n"
            "- **03_Archive**: Retired notes.\n\n"
            "Use the scheduled **Wiki Curation Routine** to curate and graduate staged inbox notes.\n"
        )
        (self.root_dir / "00_Inbox" / "welcome_to_autoreiv.md").write_text(inbox_note, encoding="utf-8")

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
            "3. **Scoped Episodic Memory**: Fast SQLite WAL indexing and native FTS5 full-text search.\n\n"
            "See also: [[telemetry_and_metrics]] and [[librarian_workflow_manual]].\n"
        )
        (
            self.root_dir / "01_Notes" / "computer_science" / "artificial_intelligence" / "local_agent_architecture.md"
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
        (self.root_dir / "01_Notes" / "systems_engineering" / "observability" / "telemetry_and_metrics.md").write_text(
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
            "1. **Stage Raw Note**: Write raw markdown content to `00_Inbox/`.\n"
            "2. **Hydrate Frontmatter**: Inject domain, topic, summary, and semantic tags.\n"
            "3. **File to Warehouse**: Move note from `00_Inbox/` to `01_Notes/{domain}/{topic}/`.\n"
        )
        (self.root_dir / "02_Resources" / "operating_manuals" / "librarian_workflow_manual.md").write_text(
            lib_manual, encoding="utf-8"
        )

    def migrate_legacy_vault(self) -> Dict[str, Any]:
        """
        Migrate legacy unnumbered (inbox, notes, resources, archive) or old 0X_ folders
        into the standardized CARD-173 numbered layout:
        00_Inbox/, 01_Notes/, 02_Resources/, 03_Archive/.
        """
        self.scaffold()
        actions = []
        migrated_files = 0

        # 1. Legacy inbox/ -> 00_Inbox/
        legacy_inbox = self.root_dir / "inbox"
        inbox_dest = self.root_dir / "00_Inbox"
        if legacy_inbox.exists() and legacy_inbox.is_dir():
            for f in list(legacy_inbox.rglob("*.md")):
                target = inbox_dest / f.name
                if not target.exists():
                    shutil.move(str(f), str(target))
                    actions.append(f"Moved {f.name} to 00_Inbox/")
                    migrated_files += 1
                else:
                    f.unlink(missing_ok=True)
            if legacy_inbox.exists() and not any(legacy_inbox.iterdir()):
                shutil.rmtree(legacy_inbox, ignore_errors=True)

        # 2. Legacy notes/ -> 01_Notes/
        legacy_notes = self.root_dir / "notes"
        notes_dest = self.root_dir / "01_Notes"
        if legacy_notes.exists() and legacy_notes.is_dir():
            for f in list(legacy_notes.rglob("*.md")):
                rel_inside = f.relative_to(legacy_notes)
                target = notes_dest / rel_inside
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.move(str(f), str(target))
                    actions.append(f"Moved {rel_inside} to 01_Notes/")
                    migrated_files += 1
                else:
                    f.unlink(missing_ok=True)
            if legacy_notes.exists() and not any(legacy_notes.iterdir()):
                shutil.rmtree(legacy_notes, ignore_errors=True)

        # 3. Legacy resources/ -> 02_Resources/
        legacy_resources = self.root_dir / "resources"
        resources_dest = self.root_dir / "02_Resources"
        if legacy_resources.exists() and legacy_resources.is_dir():
            for f in list(legacy_resources.rglob("*.md")):
                rel_inside = f.relative_to(legacy_resources)
                rel_parts = list(rel_inside.parts)
                if rel_parts and rel_parts[0].lower() == "templates":
                    rel_parts[0] = "_Templates"
                target = resources_dest / Path(*rel_parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.move(str(f), str(target))
                    actions.append(f"Moved {rel_inside} to 02_Resources/")
                    migrated_files += 1
                else:
                    f.unlink(missing_ok=True)
            if legacy_resources.exists() and not any(legacy_resources.iterdir()):
                shutil.rmtree(legacy_resources, ignore_errors=True)

        # 4. Legacy archive/ -> 03_Archive/
        legacy_archive = self.root_dir / "archive"
        archive_dest = self.root_dir / "03_Archive"
        if legacy_archive.exists() and legacy_archive.is_dir():
            for f in list(legacy_archive.rglob("*.md")):
                target = archive_dest / f.name
                if not target.exists():
                    shutil.move(str(f), str(target))
                    actions.append(f"Moved {f.name} to 03_Archive/")
                    migrated_files += 1
                else:
                    f.unlink(missing_ok=True)
            if legacy_archive.exists() and not any(legacy_archive.iterdir()):
                shutil.rmtree(legacy_archive, ignore_errors=True)

        # 5. Clean legacy 01_Projects, 02_Areas, 03_resources, 04_Archive if present
        for legacy_name in ["01_Projects", "02_Areas", "03_resources", "04_Archive"]:
            legacy_dir = self.root_dir / legacy_name
            if legacy_dir.exists() and legacy_dir.is_dir():
                for f in list(legacy_dir.rglob("*.md")):
                    dest = inbox_dest / f.name
                    if not dest.exists():
                        shutil.move(str(f), str(dest))
                        actions.append(f"Moved {f.name} from {legacy_name} to 00_Inbox/")
                        migrated_files += 1
                    else:
                        f.unlink(missing_ok=True)
                shutil.rmtree(legacy_dir, ignore_errors=True)

        return {"success": True, "migrated_count": migrated_files, "actions": actions}

    def _resolve_safe_path(self, relative_path: str) -> Optional[Path]:
        """Ensure relative path does not escape root_dir, with alias resolution between legacy and numbered paths."""
        try:
            rel = relative_path.replace("\\", "/").lstrip("/")
            target = (self.root_dir / rel).resolve()
            if not str(target).startswith(str(self.root_dir)):
                return None
            if target.exists():
                return target

            # Check legacy -> numbered mapping
            prefix_map = {
                "inbox/": "00_Inbox/",
                "00_inbox/": "00_Inbox/",
                "notes/": "01_Notes/",
                "01_notes/": "01_Notes/",
                "resources/": "02_Resources/",
                "02_resources/": "02_Resources/",
                "archive/": "03_Archive/",
                "03_archive/": "03_Archive/",
                "02_resources/templates/": "02_Resources/_Templates/",
                "resources/templates/": "02_Resources/_Templates/",
            }
            rel_lower = rel.lower()
            for prefix, mapped in prefix_map.items():
                if rel_lower.startswith(prefix):
                    alt = self.root_dir / (mapped + rel[len(prefix):])
                    if alt.exists():
                        return alt.resolve()

            # Reverse mapping: numbered -> legacy
            reverse_map = {
                "00_inbox/": "inbox/",
                "01_notes/": "notes/",
                "02_resources/": "resources/",
                "03_archive/": "archive/",
            }
            for prefix, mapped in reverse_map.items():
                if rel_lower.startswith(prefix):
                    alt = self.root_dir / (mapped + rel[len(prefix):])
                    if alt.exists():
                        return alt.resolve()

            return target
        except Exception:
            return None

    def file_note(
        self,
        title: str,
        content: str,
        domain: str = "general",
        topic: str = "general",
        category: str = "inbox",
        inbox_priority: str = "need_to_do",
        document_type: str = "atomic_note",
        tags: Optional[List[str]] = None,
        summary: str = "",
        status: Optional[str] = None,
        priority: str = "medium",
        sensitivity: str = "internal",
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create and persist a new note with structured YAML frontmatter.
        Defaults to 00_Inbox/ with clean_note_content() applied to scrub conversational chatter.
        """
        self.scaffold()
        slug = slugify(title)
        cleaned_content = clean_note_content(content)
        cat_lower = (category or "inbox").lower().strip()

        if cat_lower in ("inbox", "00_inbox"):
            rel_path = f"00_Inbox/{slug}.md"
            meta_status = status or "inbox"
            meta_doc_type = document_type if document_type != "atomic_note" else "note"
            inbox_kwargs: Dict[str, Any] = {
                "title": title,
                "domain": slugify(domain) or "general",
                "topic": slugify(topic) or "general",
                "document_type": meta_doc_type,
                "tags": tags or [],
                "summary": summary,
                "status": meta_status,
                "author": (extra_meta or {}).get("author", "assistant"),
            }
            if extra_meta:
                for k, v in extra_meta.items():
                    if k not in inbox_kwargs:
                        inbox_kwargs[k] = v
            inbox_meta = WikiInboxNoteMeta(**inbox_kwargs)
            full_text = FrontmatterParser.dump(inbox_meta, cleaned_content)
            final_domain = inbox_meta.domain
            final_topic = inbox_meta.topic
            final_uid = inbox_meta.uid
        elif cat_lower in ("resources", "02_resources"):
            rel_path = f"02_Resources/operating_manuals/{slug}.md"
            meta_status = status or "active"
            meta_kwargs = {
                "title": title,
                "domain": domain,
                "topic": topic,
                "document_type": document_type,
                "tags": tags or [],
                "summary": summary,
                "status": meta_status,
                "priority": priority,
                "sensitivity": sensitivity,
            }
            if extra_meta:
                meta_kwargs.update(extra_meta)
            grad_meta = WikiNoteMeta(**meta_kwargs)
            full_text = FrontmatterParser.dump(grad_meta, cleaned_content)
            final_domain = grad_meta.domain
            final_topic = grad_meta.topic
            final_uid = grad_meta.uid
        elif cat_lower in ("archive", "03_archive"):
            rel_path = f"03_Archive/{slug}.md"
            meta_status = status or "archived"
            meta_kwargs = {
                "title": title,
                "domain": domain,
                "topic": topic,
                "document_type": document_type,
                "tags": tags or [],
                "summary": summary,
                "status": meta_status,
                "priority": priority,
                "sensitivity": sensitivity,
            }
            if extra_meta:
                meta_kwargs.update(extra_meta)
            grad_meta = WikiNoteMeta(**meta_kwargs)
            full_text = FrontmatterParser.dump(grad_meta, cleaned_content)
            final_domain = grad_meta.domain
            final_topic = grad_meta.topic
            final_uid = grad_meta.uid
        else:
            safe_domain = slugify(domain) or "general"
            safe_topic = slugify(topic) or "general"
            target_folder = "01_Notes" if (self.root_dir / "01_Notes").exists() else "notes"
            rel_path = f"{target_folder}/{safe_domain}/{safe_topic}/{slug}.md"
            meta_status = status or "draft"
            meta_kwargs = {
                "title": title,
                "domain": domain,
                "topic": topic,
                "document_type": document_type,
                "tags": tags or [],
                "summary": summary,
                "status": meta_status,
                "priority": priority,
                "sensitivity": sensitivity,
            }
            if extra_meta:
                meta_kwargs.update(extra_meta)
            grad_meta = WikiNoteMeta(**meta_kwargs)
            full_text = FrontmatterParser.dump(grad_meta, cleaned_content)
            final_domain = grad_meta.domain
            final_topic = grad_meta.topic
            final_uid = grad_meta.uid

        target_path = self.root_dir / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(full_text, encoding="utf-8")

        return {
            "success": True,
            "path": rel_path.replace("\\", "/"),
            "title": title,
            "uid": final_uid,
            "domain": final_domain,
            "topic": final_topic,
        }

    def get_backlinks(self, target_rel: str) -> List[str]:
        """Find all note relative paths that link to this note via [[...]]."""
        target_path = self._resolve_safe_path(target_rel)
        if not target_path or not target_path.exists():
            return []

        target_stem = target_path.stem.lower()
        raw = target_path.read_text(encoding="utf-8", errors="replace")
        meta, _ = FrontmatterParser.parse(raw)
        target_title = meta.title.lower()

        backlinks = []
        for f in sorted(self.root_dir.rglob("*.md")):
            if f.resolve() == target_path.resolve():
                continue
            f_rel = str(f.relative_to(self.root_dir)).replace("\\", "/")
            f_text = f.read_text(encoding="utf-8", errors="replace")
            for link in _LINK_PATTERN.findall(f_text):
                clean_link = link.strip().lower()
                if (
                    clean_link == target_stem
                    or clean_link == target_title
                    or clean_link.endswith("/" + target_stem)
                    or clean_link == target_stem.replace("_", " ")
                ):
                    backlinks.append(f_rel)
                    break
        return backlinks

    def read_note(self, relative_path: str) -> Dict[str, Any]:
        """
        Read a note, extract frontmatter, backlinks, and return clean content.
        """
        target_path = self._resolve_safe_path(relative_path)
        if target_path is None or not target_path.is_file():
            return {"success": False, "error": f"Note '{relative_path}' not found."}

        raw_text = target_path.read_text(encoding="utf-8", errors="replace")
        meta, body = FrontmatterParser.parse(raw_text)
        backlinks = self.get_backlinks(relative_path)
        raw_fm = FrontmatterParser.extract_raw_frontmatter(raw_text)
        if not raw_fm:
            dumped = FrontmatterParser.dump(meta)
            raw_fm = dumped.split("---")[1].strip() if "---" in dumped else ""

        return {
            "success": True,
            "path": relative_path.replace("\\", "/"),
            "meta": meta.model_dump(),
            "content": body,
            "title": meta.title,
            "backlinks": backlinks,
            "raw_frontmatter": raw_fm,
        }

    def append_note(
        self,
        relative_path: str,
        content: str,
        heading: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Safely append markdown content to an existing note (optionally under a heading)
        without corrupting frontmatter, and automatically update telemetry and content hash.
        """
        target = self._resolve_safe_path(relative_path)
        if target is None or not target.exists() or not target.is_file():
            return {"success": False, "error": f"Note not found: {relative_path}"}

        existing_text = target.read_text(encoding="utf-8", errors="replace")
        meta, body = FrontmatterParser.parse(existing_text)

        append_chunk = content.strip()
        if heading:
            clean_heading = heading.strip()
            if not clean_heading.startswith("#"):
                clean_heading = f"## {clean_heading}"
            append_chunk = f"\n\n{clean_heading}\n\n{append_chunk}"
        else:
            append_chunk = f"\n\n{append_chunk}"

        new_body = (body.strip() + append_chunk).strip()

        meta_dict = meta.model_dump()
        meta_dict["last_updated"] = dt.datetime.now().strftime("%Y-%m-%d")
        meta_dict["last_accessed"] = dt.datetime.now().strftime("%Y-%m-%d")

        serialized = FrontmatterParser.dump(meta_dict, new_body)
        target.write_text(serialized, encoding="utf-8")

        return {
            "success": True,
            "path": relative_path.replace("\\", "/"),
            "title": meta.title,
            "word_count": compute_word_count(new_body),
            "context_tokens": compute_context_tokens(new_body),
            "content_hash": compute_content_hash(new_body),
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
        meta_dict["status"] = "final"
        if new_title:
            meta_dict["title"] = new_title
        if summary:
            meta_dict["summary"] = summary
        if tags is not None:
            meta_dict["tags"] = tags
        meta_dict["last_updated"] = dt.datetime.now().strftime("%Y-%m-%d")

        word_count = compute_word_count(body)
        meta_dict["word_count"] = word_count
        meta_dict["context_tokens"] = compute_context_tokens(body)

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

    def list_notes(
        self,
        category: Optional[str] = None,
        domain: Optional[str] = None,
        topic: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        author: Optional[str] = None,
        pinned: Optional[bool] = None,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List markdown notes across the wiki matching folder or frontmatter filters."""
        if not self.root_dir.is_dir():
            return []

        out = []
        for file_path in sorted(self.root_dir.rglob("*.md")):
            rel = str(file_path.relative_to(self.root_dir)).replace("\\", "/")
            if rel.startswith("."):
                continue

            # Category filter (e.g. inbox, notes, resources)
            if category:
                cat_lower = category.lower().strip()
                if not rel.lower().startswith(cat_lower):
                    continue

            raw_text = file_path.read_text(encoding="utf-8", errors="replace")
            meta, body = FrontmatterParser.parse(raw_text)

            # Metadata domain filter
            if domain and meta.domain.lower() != domain.lower().strip():
                continue

            # Metadata topic filter
            if topic and meta.topic.lower() != topic.lower().strip():
                continue

            # Metadata status filter
            if status and meta.status.lower() != status.lower().strip():
                continue

            # Metadata tag filter
            if tag and not any(tag.lower().strip() == t.lower() for t in meta.tags):
                continue

            # Metadata author filter
            if author and meta.author.lower() != author.lower().strip():
                continue

            # Metadata pinned filter
            if pinned is not None and meta.pinned != pinned:
                continue

            # Metadata priority filter
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

    def cleanup_vault(self) -> Dict[str, Any]:
        """
        Clean up misplaced templates from notes/, organize weekly worklogs to operations/worklog/,
        and ensure the single canonical template lives in resources/templates/note_template.md.
        """
        self.scaffold()
        actions = []

        # 1. Clean templates inside notes/
        notes_dir = self.root_dir / "notes"
        if notes_dir.exists():
            for f in list(notes_dir.rglob("*.md")):
                f_name = f.name.lower()
                parent_name = f.parent.name.lower()
                if "template" in f_name or "templates" == parent_name:
                    f.unlink(missing_ok=True)
                    actions.append(f"Deleted misplaced template: {f.name}")

        # 2. Relocate legacy weekly logs to notes/operations/worklog/
        legacy_weekly = self.root_dir / "notes" / "weekly"
        ops_worklog = self.root_dir / "notes" / "operations" / "worklog"
        ops_worklog.mkdir(parents=True, exist_ok=True)
        if legacy_weekly.exists() and legacy_weekly.is_dir():
            for f in list(legacy_weekly.glob("*.md")):
                dest = ops_worklog / f.name
                if not dest.exists():
                    f.rename(dest)
                    actions.append(f"Moved weekly note to operations/worklog: {f.name}")
                else:
                    f.unlink(missing_ok=True)

        # 3. Clean legacy 01_Notes and 03_resources directories
        for legacy_name in ["01_Notes", "03_resources", "00_Inbox", "02_Areas", "04_Archive"]:
            legacy_dir = self.root_dir / legacy_name
            if legacy_dir.exists() and legacy_dir.is_dir():
                for f in list(legacy_dir.rglob("*.md")):
                    if "week" in f.name.lower() or "w" in f.name.lower():
                        dest = ops_worklog / f.name
                        if not dest.exists():
                            f.rename(dest)
                            actions.append(f"Migrated legacy note to operations/worklog: {f.name}")
                    else:
                        inbox_dest = self.root_dir / "inbox" / f.name
                        if not inbox_dest.exists():
                            f.rename(inbox_dest)
                            actions.append(f"Migrated legacy note to inbox: {f.name}")
                import shutil
                shutil.rmtree(legacy_dir, ignore_errors=True)
                actions.append(f"Removed legacy directory: {legacy_name}")

        # 4. Ensure single canonical template in resources/templates/note_template.md
        tmpl_dir = self.root_dir / "resources" / "templates"
        tmpl_dir.mkdir(parents=True, exist_ok=True)
        canonical_tmpl = tmpl_dir / "note_template.md"
        if not canonical_tmpl.exists():
            tmpl_content = (
                "---\n"
                "uid: \"YYYYMMDD-HHMMSS\"\n"
                "title: \"Standard Note Template\"\n"
                "aliases: []\n"
                "document_type: \"template\"\n"
                "domain: \"general\"\n"
                "topic: \"notes\"\n"
                "tags: []\n"
                "summary: \"1-2 sentence overview of this note.\"\n"
                "status: \"template\"\n"
                "priority: \"medium\"\n"
                "sensitivity: \"internal\"\n"
                "confidence_score: 1.0\n"
                "pinned: false\n"
                "parent: \"\"\n"
                "related: []\n"
                "moc: \"\"\n"
                "source: \"manual\"\n"
                "author: \"assistant\"\n"
                "model: \"\"\n"
                "content_hash: \"\"\n"
                "date_created: \"YYYY-MM-DD\"\n"
                "last_updated: \"YYYY-MM-DD\"\n"
                "last_accessed: \"YYYY-MM-DD\"\n"
                "access_count: 0\n"
                "word_count: 0\n"
                "context_tokens: 0\n"
                "schema_version: \"1.0\"\n"
                "---\n\n"
                "# ${TITLE}\n\n"
                "## Context\n"
                "${CONTEXT}\n\n"
                "## Details\n"
                "${DETAILS}\n\n"
                "## References\n"
                "- [[local_agent_architecture]]\n"
            )
            canonical_tmpl.write_text(tmpl_content, encoding="utf-8")
            actions.append("Created canonical template at resources/templates/note_template.md")

        return {"success": True, "actions": actions}

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
        notes = [n for n in self.list_notes() if "_Templates" not in n["path"] and "templates" not in n["path"]]
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
        notes = [n for n in self.list_notes() if "_Templates" not in n["path"] and "templates" not in n["path"]]

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
