"""Vault scaffolding, taxonomy scrubbing, and legacy layout migration [CARD-173, CARD-416, CARD-714]."""

from __future__ import annotations

import datetime as dt
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.domain.data_root import validate_live_data_root

from .frontmatter import FrontmatterParser
from .templates_catalog import (
    _EMPTY_SEED_TAXONOMY_REL_PATHS,
    CLEANUP_NOTE_TEMPLATE_CONTENT,
    CORE_STRUCTURED_TEMPLATES,
    NOTE_TEMPLATE_DEFAULT_CONTENT,
    SEED_TEMPLATE_GROUPS,
    TAG_AUTHORITY_DEFAULT_CONTENT,
    template_seed_group,
)

if TYPE_CHECKING:
    from .store import WikiStore

log = logging.getLogger(__name__)


def scaffold_vault(store: "WikiStore", auto_migrate: bool = True) -> None:
    """Ensure standard CARD-173 numbered taxonomy folders exist on disk and seed canonical assets."""
    validate_live_data_root(store.root_dir)
    directories = [
        store.root_dir / "00_Inbox",
        store.root_dir / "01_Notes",
        store.root_dir / "02_Resources" / "operating_manuals",
        store.root_dir / "02_Resources" / "_Templates",
        store.root_dir / "03_Archive",
    ]
    for d in directories:
        d.mkdir(parents=True, exist_ok=True)
    # Do not mkdir domain/topic trees under 01_Notes (CARD-406/416).
    # Scrub leftover empty pre-CARD-406 seed taxonomy on every scaffold.
    scrub_empty_seed_taxonomy(store.root_dir)

    # Check if legacy unnumbered directories exist, and auto-migrate them non-destructively
    if auto_migrate and any(
        (store.root_dir / p).exists()
        for p in ("inbox", "notes", "resources", "archive", "01_Projects", "02_Areas", "03_resources")
    ):
        migrate_legacy_vault(store, ensure_scaffold=False)

    # Ensure canonical Tag Authority exists
    tag_auth = store.root_dir / "02_Resources" / "_Templates" / "tag-authority.md"
    if not tag_auth.exists():
        tag_auth.write_text(TAG_AUTHORITY_DEFAULT_CONTENT, encoding="utf-8")

    # Ensure canonical note template exists
    note_tmpl = store.root_dir / "02_Resources" / "_Templates" / "note_template.md"
    if not note_tmpl.exists():
        note_tmpl.write_text(NOTE_TEMPLATE_DEFAULT_CONTENT, encoding="utf-8")

    # Ensure structured templates exist [CARD-178, REQ-WIKI-030]. CARD-603: shipped templates are seeded into
    # their group folder (the shipped agents' template folders) and never next to a copy that already exists
    # anywhere under the templates root, so an unsorted vault gets no duplicates.
    templates_dir = store.root_dir / "02_Resources" / "_Templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    existing_names = {f.name.lower() for f in templates_dir.rglob("*.md")}
    for filename, tmpl_meta in CORE_STRUCTURED_TEMPLATES.items():
        if filename.lower() in existing_names:
            continue
        group_dir = store.root_dir / SEED_TEMPLATE_GROUPS[template_seed_group(filename)]
        group_dir.mkdir(parents=True, exist_ok=True)
        (group_dir / filename).write_text(tmpl_meta["content"], encoding="utf-8")


def scrub_empty_seed_taxonomy(root_dir: Path) -> List[str]:
    """
    Idempotently remove empty pre-CARD-406 seed taxonomy dirs under 01_Notes [CARD-416].

    Only empty directories are removed (Path.rmdir). Non-empty note paths are never deleted.
    Invoked from scaffold so establish / Settings confirm_scaffold cleans leftovers.
    """
    notes_root = root_dir / "01_Notes"
    if not notes_root.is_dir():
        return []

    candidates: list[Path] = []
    seen: set[Path] = set()
    for rel in _EMPTY_SEED_TAXONOMY_REL_PATHS:
        parts = Path(rel).parts
        for depth in range(len(parts), 0, -1):
            candidate = notes_root.joinpath(*parts[:depth])
            if candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)

    candidates.sort(key=lambda p: len(p.parts), reverse=True)
    actions: List[str] = []
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        try:
            candidate.rmdir()
        except OSError:
            # Non-empty or busy — leave operator content alone.
            continue
        rel = candidate.relative_to(root_dir).as_posix()
        actions.append(f"Removed empty seed taxonomy: {rel}")
        log.info("CARD-416 scrubbed empty seed taxonomy path: %s", rel)
    return actions


def migrate_legacy_vault(store: "WikiStore", ensure_scaffold: bool = True) -> Dict[str, Any]:
    """
    Migrate legacy unnumbered (inbox, notes, resources, archive) or old 0X_ folders
    into the standardized CARD-173 numbered layout:
    00_Inbox/, 01_Notes/, 02_Resources/, 03_Archive/.
    """
    if ensure_scaffold:
        store.scaffold(auto_migrate=False)
    actions: List[str] = []
    migrated_files = 0
    root_dir = store.root_dir

    # 1. Legacy inbox/ -> 00_Inbox/
    legacy_inbox = root_dir / "inbox"
    inbox_dest = root_dir / "00_Inbox"
    if legacy_inbox.exists() and legacy_inbox.is_dir():
        for f in list(legacy_inbox.rglob("*.md")):
            target = inbox_dest / f.name
            if not target.exists():
                shutil.move(str(f), str(target))
                actions.append(f"Moved {f.name} to 00_Inbox/")
                migrated_files += 1
            else:
                if f.resolve() != target.resolve():
                    if f.read_text(encoding="utf-8", errors="replace") == target.read_text(encoding="utf-8", errors="replace"):
                        f.unlink(missing_ok=True)
                    else:
                        safe_name = f"{f.stem}_migrated_{int(dt.datetime.now().timestamp())}{f.suffix}"
                        safe_target = inbox_dest / safe_name
                        shutil.move(str(f), str(safe_target))
                        actions.append(f"Moved {f.name} to 00_Inbox/{safe_name}")
                        migrated_files += 1
        if legacy_inbox.exists() and not any(legacy_inbox.iterdir()):
            shutil.rmtree(legacy_inbox, ignore_errors=True)

    # 2. Legacy notes/ -> 01_Notes/
    legacy_notes = root_dir / "notes"
    notes_dest = root_dir / "01_Notes"
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
                if f.resolve() != target.resolve():
                    if f.read_text(encoding="utf-8", errors="replace") == target.read_text(encoding="utf-8", errors="replace"):
                        f.unlink(missing_ok=True)
                    else:
                        safe_name = f"{f.stem}_migrated_{int(dt.datetime.now().timestamp())}{f.suffix}"
                        safe_target = target.parent / safe_name
                        shutil.move(str(f), str(safe_target))
                        actions.append(f"Moved {rel_inside} to 01_Notes/{safe_name}")
                        migrated_files += 1
        if legacy_notes.exists():
            for d in sorted(legacy_notes.rglob("*"), reverse=True):
                if d.is_dir():
                    try:
                        d.rmdir()
                    except Exception:
                        pass
            if not any(legacy_notes.iterdir()):
                shutil.rmtree(legacy_notes, ignore_errors=True)

    # 3. Legacy resources/ -> 02_Resources/
    legacy_resources = root_dir / "resources"
    resources_dest = root_dir / "02_Resources"
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
    legacy_archive = root_dir / "archive"
    archive_dest = root_dir / "03_Archive"
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
        legacy_dir = root_dir / legacy_name
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


def cleanup_vault(store: "WikiStore") -> Dict[str, Any]:
    """
    Clean up misplaced templates, organize weekly worklogs to 01_Notes/weekly/,
    and ensure canonical templates live in 02_Resources/_Templates/ [CARD-173, CARD-406].
    """
    store.scaffold()
    actions: List[str] = []
    root_dir = store.root_dir

    # 1. Clean misplaced templates inside legacy notes/
    notes_dir = root_dir / "notes"
    if notes_dir.exists():
        for f in list(notes_dir.rglob("*.md")):
            f_name = f.name.lower()
            parent_name = f.parent.name.lower()
            if "template" in f_name or "templates" == parent_name:
                f.unlink(missing_ok=True)
                actions.append(f"Deleted misplaced template: {f.name}")

    # 2. Relocate legacy weekly logs to 01_Notes/weekly/
    legacy_weekly = root_dir / "notes" / "weekly"
    ops_worklog = root_dir / "01_Notes" / "weekly"
    if legacy_weekly.exists() and legacy_weekly.is_dir():
        ops_worklog.mkdir(parents=True, exist_ok=True)
        for f in list(legacy_weekly.glob("*.md")):
            dest = ops_worklog / f.name
            if not dest.exists():
                f.rename(dest)
                actions.append(f"Moved weekly note to 01_Notes/weekly: {f.name}")
            else:
                f.unlink(missing_ok=True)
        try:
            legacy_weekly.rmdir()
        except Exception:
            pass

    # 3. Clean legacy unnumbered directories via migrate_legacy_vault
    migration = migrate_legacy_vault(store, ensure_scaffold=False)
    actions.extend(migration.get("actions", []))

    # Clean up empty legacy notes/ tree if left behind
    notes_dir = root_dir / "notes"
    if notes_dir.exists():
        for d in sorted(notes_dir.rglob("*"), reverse=True):
            if d.is_dir():
                try:
                    d.rmdir()
                except Exception:
                    pass
        try:
            notes_dir.rmdir()
        except Exception:
            pass

    # 4. Ensure single canonical template in 02_Resources/_Templates/note_template.md
    tmpl_dir = root_dir / "02_Resources" / "_Templates"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    canonical_tmpl = tmpl_dir / "note_template.md"
    if not canonical_tmpl.exists():
        canonical_tmpl.write_text(CLEANUP_NOTE_TEMPLATE_CONTENT, encoding="utf-8")
        actions.append("Created canonical template at 02_Resources/_Templates/note_template.md")

    return {"success": True, "actions": actions}


def list_templates(store: "WikiStore", folder: Optional[str] = None) -> List[Dict[str, Any]]:
    """List structured note templates (in ``folder`` when given) [REQ-WIKI-031, CARD-603]."""
    store.scaffold()
    results = []
    for file in store._template_files(folder):
        slug = file.stem.replace("_", "-")
        content = file.read_text(encoding="utf-8", errors="replace")
        meta, _ = FrontmatterParser.parse(content)
        title = meta.title if meta.title and meta.title != "Untitled Note" else slug.replace("-", " ").title()
        description = meta.summary or "Structured note template."
        results.append({
            "slug": slug,
            "title": title,
            "description": description,
            "path": str(file.relative_to(store.root_dir)).replace("\\", "/"),
            "tags": meta.tags or [],
        })
    return results


def get_template(store: "WikiStore", slug: str, folder: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a specific structured template by its slug or filename [REQ-WIKI-031, CARD-603]."""
    store.scaffold()
    target_slug = str(slug or "").lower().replace("_", "-").replace(".md", "")
    for file in store._template_files(folder):
        file_slug = file.stem.replace("_", "-").lower()
        if file_slug == target_slug:
            content = file.read_text(encoding="utf-8", errors="replace")
            meta, body = FrontmatterParser.parse(content)
            title = meta.title if meta.title and meta.title != "Untitled Note" else file_slug.replace("-", " ").title()
            description = meta.summary or "Structured note template."
            return {
                "slug": file_slug,
                "title": title,
                "description": description,
                "path": str(file.relative_to(store.root_dir)).replace("\\", "/"),
                "content": body.strip(),
                "raw_template": content,
                "tags": meta.tags or [],
            }
    return None


def create_template(
    store: "WikiStore",
    slug: str,
    title: str,
    description: str,
    content: str,
    tags: Optional[List[str]] = None,
    folder: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new structured note template strictly under the templates directory [CARD-349, CARD-603]."""
    clean_slug = store._clean_template_slug(slug)
    if not clean_slug:
        return {"success": False, "error": "Invalid or empty template slug."}

    if folder is not None:
        store.scaffold()
        templates_dir = store.template_folder_dir(folder)
        if templates_dir is None:
            return {"success": False, "error": f"Template folder '{folder}' is not a folder inside the wiki vault."}
        templates_dir.mkdir(parents=True, exist_ok=True)
    else:
        templates_dir = store._resolve_templates_dir(create=True)
    target_file = templates_dir / f"{clean_slug}.md"
    rel_path = str(target_file.relative_to(store.root_dir)).replace("\\", "/")
    if folder is None and not target_file.exists():
        for existing in store._template_files(None):
            if existing.stem.replace("_", "-").lower() == clean_slug:
                target_file = existing
                rel_path = str(existing.relative_to(store.root_dir)).replace("\\", "/")
                break

    if target_file.exists():
        return {
            "success": False,
            "error": f"Template with slug '{clean_slug}' already exists at '{rel_path}'. Use wiki_template_update to modify existing templates.",
            "path": rel_path,
        }

    clean_tags = list(tags) if tags is not None else ["wiki", "template"]
    if "template" not in clean_tags:
        clean_tags.append("template")

    clean_title = (title or "").strip() or clean_slug.replace("-", " ").title()
    clean_desc = (description or "").strip() or "Structured note template."

    meta_dict = {
        "uid": dt.datetime.now().strftime("%Y%m%d-%H%M%S"),
        "title": clean_title,
        "document_type": "template",
        "type": "template",
        "summary": clean_desc,
        "description": clean_desc,
        "tags": clean_tags,
        "domain": "general",
        "topic": "template",
        "status": "template",
        "created_at": dt.datetime.now().strftime("%Y-%m-%d"),
        "last_updated": dt.datetime.now().strftime("%Y-%m-%d"),
        "schema_version": "1.0",
    }

    body = (content or "").strip()
    serialized = FrontmatterParser.dump(meta_dict, body)
    if "type: template" not in serialized:
        serialized = serialized.replace("document_type: template", "document_type: template\ntype: template")

    target_file.write_text(serialized, encoding="utf-8")
    return {
        "success": True,
        "slug": clean_slug,
        "title": clean_title,
        "path": rel_path,
    }


def update_template(
    store: "WikiStore",
    slug: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
    folder: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing structured note template [CARD-349, CARD-603]."""
    clean_slug = store._clean_template_slug(slug)
    if not clean_slug:
        return {"success": False, "error": "Invalid or empty template slug."}

    store.scaffold()
    target_file: Optional[Path] = None
    for file in store._template_files(folder):
        if file.stem.replace("_", "-").lower() == clean_slug:
            target_file = file
            break

    if target_file is None or not target_file.exists():
        return {
            "success": False,
            "error": f"Template with slug '{clean_slug}' not found. Use wiki_template_create to author new templates.",
        }

    raw_text = target_file.read_text(encoding="utf-8", errors="replace")
    meta, existing_body = FrontmatterParser.parse(raw_text)
    meta_dict = meta.model_dump()
    meta_dict["type"] = "template"
    meta_dict["document_type"] = "template"

    if title is not None:
        meta_dict["title"] = title.strip()
    if description is not None:
        meta_dict["summary"] = description.strip()
        meta_dict["description"] = description.strip()
    if tags is not None:
        meta_dict["tags"] = list(tags)

    meta_dict["last_updated"] = dt.datetime.now().strftime("%Y-%m-%d")

    new_body = content.strip() if content is not None else existing_body.strip()
    serialized = FrontmatterParser.dump(meta_dict, new_body)
    if "type: template" not in serialized:
        serialized = serialized.replace("document_type: template", "document_type: template\ntype: template")

    target_file.write_text(serialized, encoding="utf-8")
    rel_path = str(target_file.relative_to(store.root_dir)).replace("\\", "/")
    return {
        "success": True,
        "slug": clean_slug,
        "title": meta_dict.get("title", clean_slug),
        "path": rel_path,
    }
