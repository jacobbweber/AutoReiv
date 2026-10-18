"""
WikiStore Core Engine [REQ-WIKI-001, REQ-WIKI-003, REQ-WIKI-004, CARD-714].
Manages local-first plain-text markdown files under the Degree/Class taxonomy.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.domain.data_root import LEGACY_WIKI_STRINGS, resolve_default_wiki_path

from .frontmatter import (
    FrontmatterParser,
    WikiInboxNoteMeta,
    WikiNoteMeta,
    clean_note_content,
    compute_content_hash,
    compute_context_tokens,
    compute_word_count,
)
from .graph_index import (
    _CATEGORY_FOLDERS,
    _LINK_PATTERN,
    _WORD_PATTERN,
    _category_prefixes,
)
from .graph_index import (
    get_graph as _get_graph,
)
from .graph_index import (
    get_mindmap as _get_mindmap,
)
from .graph_index import (
    get_overview as _get_overview,
)
from .graph_index import (
    get_stats as _get_stats,
)
from .graph_index import (
    get_tree as _get_tree,
)
from .graph_index import (
    list_notes as _list_notes,
)
from .graph_index import (
    search_notes as _search_notes,
)
from .template_folders import TemplateFolderError, normalize_template_folder
from .templates_catalog import (
    _EMPTY_SEED_TAXONOMY_REL_PATHS,
    _SLUG_CLEAN_PATTERN,
    CORE_STRUCTURED_TEMPLATES,
    SEED_TEMPLATE_GROUPS,
    slugify,
    template_seed_group,
)
from .vault_migration import (
    cleanup_vault as _cleanup_vault,
)
from .vault_migration import (
    create_template as _create_template,
)
from .vault_migration import (
    get_template as _get_template,
)
from .vault_migration import (
    list_templates as _list_templates,
)
from .vault_migration import (
    migrate_legacy_vault as _migrate_legacy_vault,
)
from .vault_migration import (
    scaffold_vault as _scaffold_vault,
)
from .vault_migration import (
    scrub_empty_seed_taxonomy as _scrub_empty_seed_taxonomy,
)
from .vault_migration import (
    update_template as _update_template,
)

log = logging.getLogger(__name__)

__all__ = [
    "CORE_STRUCTURED_TEMPLATES",
    "SEED_TEMPLATE_GROUPS",
    "WikiStore",
    "_CATEGORY_FOLDERS",
    "_EMPTY_SEED_TAXONOMY_REL_PATHS",
    "_LINK_PATTERN",
    "_SLUG_CLEAN_PATTERN",
    "_WORD_PATTERN",
    "_category_prefixes",
    "slugify",
    "template_seed_group",
]


class WikiStore:
    """
    Core local-first document storage and indexing engine.
    """

    def __init__(self, root_dir: str | Path | None = None, auto_seed: bool = False):
        if root_dir is None or str(root_dir).strip() in LEGACY_WIKI_STRINGS:
            self.root_dir = resolve_default_wiki_path()
        else:
            self.root_dir = Path(root_dir).resolve()
        self.auto_seed = auto_seed

    def scaffold(self, seed_starter: Optional[bool] = None, auto_migrate: bool = True) -> None:
        """Ensure standard CARD-173 numbered taxonomy folders exist on disk and seed canonical assets."""
        _scaffold_vault(self, auto_migrate=auto_migrate)

    def scrub_empty_seed_taxonomy(self) -> List[str]:
        """Idempotently remove empty pre-CARD-406 seed taxonomy dirs under 01_Notes [CARD-416]."""
        return _scrub_empty_seed_taxonomy(self.root_dir)

    def migrate_legacy_vault(self, ensure_scaffold: bool = True) -> Dict[str, Any]:
        """Migrate legacy unnumbered or old 0X_ folders into the CARD-173 numbered layout."""
        return _migrate_legacy_vault(self, ensure_scaffold=ensure_scaffold)

    def cleanup_vault(self) -> Dict[str, Any]:
        """Clean up misplaced templates, organize weekly worklogs, and ensure canonical templates exist."""
        return _cleanup_vault(self)

    def _resolve_safe_path(self, relative_path: str) -> Optional[Path]:
        """Ensure relative path does not escape root_dir, with alias resolution between legacy and numbered paths."""
        try:
            rel = relative_path.replace("\\", "/").lstrip("/")
            target = (self.root_dir / rel).resolve()
            if not str(target).startswith(str(self.root_dir)):
                return None
            if target.exists():
                return target

            # Check legacy -> numbered mapping (longest prefix first)
            prefix_pairs = [
                ("02_resources/templates/", "02_Resources/_Templates/"),
                ("resources/templates/", "02_Resources/_Templates/"),
                ("00_inbox/", "00_Inbox/"),
                ("inbox/", "00_Inbox/"),
                ("01_notes/", "01_Notes/"),
                ("notes/", "01_Notes/"),
                ("02_resources/", "02_Resources/"),
                ("resources/", "02_Resources/"),
                ("03_archive/", "03_Archive/"),
                ("archive/", "03_Archive/"),
            ]
            rel_lower = rel.lower()
            for prefix, mapped in prefix_pairs:
                if rel_lower.startswith(prefix):
                    alt = self.root_dir / (mapped + rel[len(prefix):])
                    if alt.exists():
                        return alt.resolve()

            # Reverse mapping: numbered -> legacy
            reverse_pairs = [
                ("02_resources/_templates/", "resources/templates/"),
                ("00_inbox/", "inbox/"),
                ("01_notes/", "notes/"),
                ("02_resources/", "resources/"),
                ("03_archive/", "archive/"),
            ]
            for prefix, mapped in reverse_pairs:
                if rel_lower.startswith(prefix):
                    alt = self.root_dir / (mapped + rel[len(prefix):])
                    if alt.exists():
                        return alt.resolve()

            # For paths that do not exist yet (e.g. creating/targeting), map aliases if destination directory exists
            for prefix, mapped in prefix_pairs:
                if rel_lower.startswith(prefix):
                    alt = self.root_dir / (mapped + rel[len(prefix):])
                    if (self.root_dir / mapped).exists():
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
                "author": (extra_meta or {}).get("author", "autoreiv"),
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
        """Read a note, extract frontmatter, backlinks, and return clean content."""
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

    def archive_note(
        self,
        relative_path: str,
        reason: str = "archived",
        preserve_source: bool = False,
    ) -> Dict[str, Any]:
        """
        Safely archive a note to 03_Archive/<slug>_<timestamp>.md [CARD-409].
        Preserves frontmatter, sets status='archived', and updates archive metadata.
        """
        self.scaffold()
        target_path = self._resolve_safe_path(relative_path)
        if target_path is None or not target_path.is_file():
            return {"success": False, "error": f"Note '{relative_path}' not found."}

        raw_text = target_path.read_text(encoding="utf-8", errors="replace")
        meta, body = FrontmatterParser.parse(raw_text)
        meta_dict = meta.model_dump()
        meta_dict["status"] = "archived"
        meta_dict["archived_at"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if reason:
            meta_dict["archive_reason"] = reason

        archive_dir = self.root_dir / "03_Archive"
        archive_dir.mkdir(parents=True, exist_ok=True)

        stem = target_path.stem
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_filename = f"{stem}_{ts}.md"
        dest_path = archive_dir / archive_filename
        counter = 1
        while dest_path.exists():
            dest_path = archive_dir / f"{stem}_{ts}_{counter}.md"
            counter += 1

        updated_meta = WikiNoteMeta.model_validate(meta_dict)
        full_text = FrontmatterParser.dump(updated_meta, body)
        dest_path.write_text(full_text, encoding="utf-8")

        if not preserve_source:
            target_path.unlink(missing_ok=True)

        rel_dest = str(dest_path.relative_to(self.root_dir)).replace("\\", "/")
        return {
            "success": True,
            "source_path": relative_path.replace("\\", "/"),
            "archive_path": rel_dest,
            "title": updated_meta.title,
            "status": "archived",
        }

    def write_note(
        self,
        relative_path: str,
        content: str,
        update_frontmatter: Optional[Dict[str, Any]] = None,
        backup_to_archive: bool = False,
    ) -> Dict[str, Any]:
        """
        Non-destructively update an existing note's body, preserving metadata and bumping last_updated.
        """
        target_path = self._resolve_safe_path(relative_path)
        if target_path is None:
            return {"success": False, "error": "Invalid or unsafe path."}

        if target_path.is_file():
            if backup_to_archive:
                self.archive_note(relative_path, reason="Backup before update", preserve_source=True)
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

    def delete_folder(self, relative_path: str) -> Dict[str, Any]:
        """
        Delete a subfolder from the wiki vault [REQ-WIKI-024, REQ-WIKI-025].
        Strictly prevents deleting root folders (00_Inbox, 01_Notes, 02_Resources, 03_Archive, or the vault root).
        """
        clean_rel = (relative_path or "").replace("\\", "/").strip().strip("/")
        clean_lower = clean_rel.lower()

        protected_roots = {
            "",
            ".",
            "00_inbox",
            "inbox",
            "01_notes",
            "notes",
            "02_resources",
            "resources",
            "03_archive",
            "archive",
        }
        if not clean_rel or clean_lower in protected_roots:
            return {
                "success": False,
                "error": f"Cannot delete protected root vault folder '{relative_path}'.",
            }

        target_path = self._resolve_safe_path(clean_rel)
        if target_path is None:
            return {"success": False, "error": "Path traversal detected: target path is outside wiki root."}

        resolved_str = str(target_path.resolve())
        root_str = str(self.root_dir.resolve())
        if resolved_str == root_str:
            return {"success": False, "error": "Cannot delete protected root vault directory."}

        for root_name in ["00_Inbox", "01_Notes", "02_Resources", "03_Archive", "inbox", "notes", "resources", "archive"]:
            if resolved_str == str((self.root_dir / root_name).resolve()):
                return {
                    "success": False,
                    "error": f"Cannot delete protected root vault folder '{relative_path}'.",
                }

        if not target_path.exists() or not target_path.is_dir():
            return {"success": False, "error": f"Folder '{relative_path}' not found."}

        try:
            shutil.rmtree(target_path)
            return {"success": True, "path": clean_rel}
        except Exception as e:
            return {"success": False, "error": f"Failed to delete folder '{clean_rel}': {e}"}

    # --- Templates [CARD-178, CARD-349, CARD-603] ---

    def _templates_root(self) -> Path:
        return self.root_dir / "02_Resources" / "_Templates"

    def _resolve_templates_dir(self, create: bool = True) -> Path:
        self.scaffold()
        p1 = self._templates_root()
        if create:
            p1.mkdir(parents=True, exist_ok=True)
            return p1
        if p1.exists():
            return p1
        p2 = self.root_dir / "resources" / "templates"
        if p2.exists():
            return p2
        return p1

    def template_folder_dir(self, folder: str) -> Optional[Path]:
        """Absolute path of a vault-relative template folder, or None if it is invalid or leaves the vault [CARD-603]."""
        try:
            clean = normalize_template_folder(folder)
        except TemplateFolderError:
            return None
        if not clean:
            return None
        root = self.root_dir.resolve()
        target = (root / clean).resolve()
        if target != root and root not in target.parents:
            return None
        return target

    def _template_files(self, folder: Optional[str] = None) -> List[Path]:
        if folder is not None:
            target = self.template_folder_dir(folder)
            if target is None or not target.is_dir():
                return []
            files = sorted(target.glob("*.md"))
        else:
            templates_dir = self._templates_root()
            if not templates_dir.exists():
                templates_dir = self.root_dir / "resources" / "templates"
                if not templates_dir.exists():
                    return []
            files = sorted(templates_dir.rglob("*.md"))
        return [f for f in files if f.name.lower() not in ("tag-authority.md", "tag_authority.md")]

    @staticmethod
    def _clean_template_slug(slug: str) -> str:
        clean_slug = str(slug or "").strip().lower().replace(" ", "-").replace("_", "-")
        if clean_slug.endswith(".md"):
            clean_slug = clean_slug[:-3]
        return re.sub(r"[^a-z0-9\-]", "", clean_slug)

    def list_templates(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """List structured note templates (in ``folder`` when given) [REQ-WIKI-031, CARD-603]."""
        return _list_templates(self, folder=folder)

    def get_template(self, slug: str, folder: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a specific structured template by its slug or filename [REQ-WIKI-031, CARD-603]."""
        return _get_template(self, slug=slug, folder=folder)

    def create_template(
        self,
        slug: str,
        title: str,
        description: str,
        content: str,
        tags: Optional[List[str]] = None,
        folder: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new structured note template strictly under the templates directory [CARD-349, CARD-603]."""
        return _create_template(
            self,
            slug=slug,
            title=title,
            description=description,
            content=content,
            tags=tags,
            folder=folder,
        )

    def update_template(
        self,
        slug: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        folder: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing structured note template [CARD-349, CARD-603]."""
        return _update_template(
            self,
            slug=slug,
            title=title,
            description=description,
            content=content,
            tags=tags,
            folder=folder,
        )

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
        """Move a note (e.g. from 00_Inbox/ to 01_Notes/<domain>/<topic>/) and hydrate frontmatter."""
        source_file = self._resolve_safe_path(source_path)
        if not source_file or not source_file.is_file():
            return {"success": False, "error": f"Source note '{source_path}' does not exist."}

        raw_text = source_file.read_text(encoding="utf-8", errors="replace")
        meta, body = FrontmatterParser.parse(raw_text)
        meta_dict = meta.model_dump()

        safe_domain = _SLUG_CLEAN_PATTERN.sub("_", (target_domain or "general").lower()).strip("_")
        safe_topic = _SLUG_CLEAN_PATTERN.sub("_", (target_topic or "general").lower()).strip("_")
        slug = source_file.stem

        target_folder = "01_Notes" if (self.root_dir / "01_Notes").exists() else "notes"
        target_rel = f"{target_folder}/{safe_domain}/{safe_topic}/{slug}.md"
        target_file = self._resolve_safe_path(target_rel)
        if target_file is None:
            return {"success": False, "error": "Invalid destination path."}

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

    # --- Indexing, Search, Graph, Mindmap, Tree ---

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
        hidden: Optional[Callable[[str], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """List markdown notes across the wiki matching folder or frontmatter filters."""
        return _list_notes(
            self.root_dir,
            category=category,
            domain=domain,
            topic=topic,
            status=status,
            tag=tag,
            author=author,
            pinned=pinned,
            priority=priority,
            hidden=hidden,
        )

    def search_notes(
        self,
        query: str = "",
        limit: int = 5,
        tags: Optional[List[str]] = None,
        domain: Optional[str] = None,
        topic: Optional[str] = None,
        document_type: Optional[str] = None,
        hidden: Optional[Callable[[str], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """Progressive search scoring terms across note titles, tags, and summary snippets [CARD-353]."""
        return _search_notes(
            self.root_dir,
            query=query,
            limit=limit,
            tags=tags,
            domain=domain,
            topic=topic,
            document_type=document_type,
            hidden=hidden,
        )

    def get_graph(self) -> Dict[str, Any]:
        """Extract [[wikilink]] references across all notes and generate directed graph nodes and edges."""
        return _get_graph(self)

    def get_mindmap(self, include_tags: bool = True, include_taxonomy: bool = True) -> Dict[str, Any]:
        """Extract multi-dimensional knowledge graph for Obsidian-style Mind Map."""
        return _get_mindmap(self, include_tags=include_tags, include_taxonomy=include_taxonomy)

    def get_tree(self) -> Dict[str, Any]:
        """Build nested category tree for UI sidebar explorer."""
        return _get_tree(self)

    def get_overview(self, max_items: int = 20, hidden: Optional[Callable[[str], bool]] = None) -> str:
        """Generate a compact, prompt-ready text inventory under 150 tokens."""
        return _get_overview(self.root_dir, max_items=max_items, hidden=hidden)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics across the wiki."""
        return _get_stats(self.root_dir)
