"""Wiki note curation, archiving, moving, deletion, and empty-folder pruning [CARD-744]."""

from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .frontmatter import (
    FrontmatterParser,
    WikiNoteMeta,
    compute_context_tokens,
    compute_word_count,
)
from .templates_catalog import _SLUG_CLEAN_PATTERN

if TYPE_CHECKING:
    from .store import WikiStore

_PROTECTED_TOP_FOLDERS = frozenset(
    {
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
)

_PRUNABLE_ROOT_PREFIXES = frozenset({"00_inbox", "inbox", "01_notes", "notes"})


def _is_protected_template_path(root_dir: Path, path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(root_dir.resolve()).as_posix().lower()
    except Exception:
        rel = str(path).replace("\\", "/").lower()
    return (
        rel.startswith("02_resources/_templates/")
        or rel.startswith("02_resources/templates/")
        or rel.startswith("resources/templates/")
        or rel.endswith("/tag-authority.md")
        or rel == "tag-authority.md"
    )


def prune_empty_parents(root_dir: Path, start_dir: Path) -> List[str]:
    """Remove empty intermediate directories under 00_Inbox/ or 01_Notes/, never top-level vault folders [CARD-744]."""
    pruned: List[str] = []
    root_resolved = root_dir.resolve()
    try:
        cur = start_dir.resolve()
    except Exception:
        return pruned

    while cur != root_resolved and root_resolved in cur.parents:
        rel = cur.relative_to(root_resolved).as_posix()
        parts = [p for p in rel.split("/") if p]
        if len(parts) <= 1:
            # Never delete top-level vault roots (00_Inbox, 01_Notes, 02_Resources, 03_Archive).
            break
        if parts[0].lower() not in _PRUNABLE_ROOT_PREFIXES:
            break
        if not cur.is_dir():
            cur = cur.parent
            continue
        try:
            if any(cur.iterdir()):
                break
            cur.rmdir()
            pruned.append(rel)
        except OSError:
            break
        cur = cur.parent

    return pruned


def archive_note(
    store: "WikiStore",
    relative_path: str,
    reason: str = "archived",
    preserve_source: bool = False,
) -> Dict[str, Any]:
    """Safely archive a note to 03_Archive/<slug>_<timestamp>.md and prune empty source folders [CARD-409, CARD-744]."""
    store.scaffold()
    target_path = store._resolve_safe_path(relative_path)
    if target_path is None or not target_path.is_file():
        return {"success": False, "error": f"Note '{relative_path}' not found."}

    raw_text = target_path.read_text(encoding="utf-8", errors="replace")
    meta, body = FrontmatterParser.parse(raw_text)
    meta_dict = meta.model_dump()
    meta_dict["status"] = "archived"
    meta_dict["archived_at"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if reason:
        meta_dict["archive_reason"] = reason

    archive_dir = store.root_dir / "03_Archive"
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

    pruned_dirs: List[str] = []
    if not preserve_source:
        source_parent = target_path.parent
        target_path.unlink(missing_ok=True)
        pruned_dirs = prune_empty_parents(store.root_dir, source_parent)

    rel_dest = str(dest_path.relative_to(store.root_dir)).replace("\\", "/")
    return {
        "success": True,
        "source_path": relative_path.replace("\\", "/"),
        "archive_path": rel_dest,
        "title": updated_meta.title,
        "status": "archived",
        "pruned_dirs": pruned_dirs,
    }


def organize_note(
    store: "WikiStore",
    source_path: str,
    target_domain: str,
    target_topic: str,
    document_type: str = "atomic_note",
    summary: Optional[str] = None,
    tags: Optional[List[str]] = None,
    new_title: Optional[str] = None,
) -> Dict[str, Any]:
    """Move a note (e.g. from 00_Inbox/ to 01_Notes/<domain>/<topic>/) and hydrate frontmatter."""
    source_file = store._resolve_safe_path(source_path)
    if not source_file or not source_file.is_file():
        return {"success": False, "error": f"Source note '{source_path}' does not exist."}

    raw_text = source_file.read_text(encoding="utf-8", errors="replace")
    meta, body = FrontmatterParser.parse(raw_text)
    meta_dict = meta.model_dump()

    safe_domain = _SLUG_CLEAN_PATTERN.sub("_", (target_domain or "general").lower()).strip("_")
    safe_topic = _SLUG_CLEAN_PATTERN.sub("_", (target_topic or "general").lower()).strip("_")
    slug = source_file.stem

    target_folder = "01_Notes" if (store.root_dir / "01_Notes").exists() else "notes"
    target_rel = f"{target_folder}/{safe_domain}/{safe_topic}/{slug}.md"
    target_file = store._resolve_safe_path(target_rel)
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

    pruned_dirs: List[str] = []
    if source_file.resolve() != target_file.resolve():
        source_parent = source_file.parent
        source_file.unlink(missing_ok=True)
        pruned_dirs = prune_empty_parents(store.root_dir, source_parent)

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
        "pruned_dirs": pruned_dirs,
    }


def move_note(
    store: "WikiStore",
    source_path: str,
    destination_path: Optional[str] = None,
    domain: Optional[str] = None,
    topic: Optional[str] = None,
    new_title: Optional[str] = None,
    update_frontmatter: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Move or rename a note under 00_Inbox/ or 01_Notes/, update frontmatter, and prune empty source folders [CARD-744]."""
    source_file = store._resolve_safe_path(source_path)
    if source_file is None:
        return {"success": False, "error": "Path traversal detected: source path is outside wiki root."}
    if not source_file.is_file():
        return {"success": False, "error": f"Source note '{source_path}' not found."}
    if _is_protected_template_path(store.root_dir, source_file):
        return {
            "success": False,
            "error": "Templates under 02_Resources/_Templates/ cannot be moved with wiki_note_move.",
        }

    raw_text = source_file.read_text(encoding="utf-8", errors="replace")
    meta, body = FrontmatterParser.parse(raw_text)
    meta_dict = meta.model_dump()

    if destination_path:
        clean_dest = str(destination_path).replace("\\", "/").strip().lstrip("/")
        if not clean_dest.lower().endswith(".md"):
            clean_dest = f"{clean_dest}.md"
        dest_file = store._resolve_safe_path(clean_dest)
        if dest_file is None:
            return {"success": False, "error": "Path traversal detected: destination path is outside wiki root."}
    elif domain or topic:
        safe_domain = _SLUG_CLEAN_PATTERN.sub("_", (domain or meta_dict.get("domain") or "general").lower()).strip("_")
        safe_topic = _SLUG_CLEAN_PATTERN.sub("_", (topic or meta_dict.get("topic") or "general").lower()).strip("_")
        target_folder = "01_Notes" if (store.root_dir / "01_Notes").exists() else "notes"
        clean_dest = f"{target_folder}/{safe_domain}/{safe_topic}/{source_file.name}"
        dest_file = store._resolve_safe_path(clean_dest)
        if dest_file is None:
            return {"success": False, "error": "Invalid destination path."}
    else:
        return {"success": False, "error": "destination_path (or domain and topic) is required."}

    if _is_protected_template_path(store.root_dir, dest_file):
        return {
            "success": False,
            "error": "Templates under 02_Resources/_Templates/ cannot be targeted with wiki_note_move.",
        }

    dest_rel = dest_file.resolve().relative_to(store.root_dir.resolve()).as_posix()
    dest_parts = [p for p in dest_rel.split("/") if p]
    if len(dest_parts) >= 4 and dest_parts[0].lower() in ("01_notes", "notes"):
        inferred_domain = _SLUG_CLEAN_PATTERN.sub("_", (domain or dest_parts[1]).lower()).strip("_")
        inferred_topic = _SLUG_CLEAN_PATTERN.sub("_", (topic or dest_parts[2]).lower()).strip("_")
        meta_dict["domain"] = inferred_domain
        meta_dict["topic"] = inferred_topic
        meta_dict["category"] = "notes"
        if meta_dict.get("status") == "inbox":
            meta_dict["status"] = "final"
    else:
        if domain:
            meta_dict["domain"] = _SLUG_CLEAN_PATTERN.sub("_", domain.lower()).strip("_")
        if topic:
            meta_dict["topic"] = _SLUG_CLEAN_PATTERN.sub("_", topic.lower()).strip("_")

    if new_title:
        meta_dict["title"] = new_title
    if update_frontmatter:
        meta_dict.update(update_frontmatter)
    meta_dict["last_updated"] = dt.datetime.now().strftime("%Y-%m-%d")
    meta_dict["word_count"] = compute_word_count(body)
    meta_dict["context_tokens"] = compute_context_tokens(body)

    updated_meta = WikiNoteMeta.model_validate(meta_dict)
    full_text = FrontmatterParser.dump(updated_meta, body)

    dest_file.parent.mkdir(parents=True, exist_ok=True)
    dest_file.write_text(full_text, encoding="utf-8")

    source_rel = source_file.resolve().relative_to(store.root_dir.resolve()).as_posix()
    pruned_dirs: List[str] = []
    if source_file.resolve() != dest_file.resolve():
        source_parent = source_file.parent
        source_file.unlink(missing_ok=True)
        pruned_dirs = prune_empty_parents(store.root_dir, source_parent)

    return {
        "success": True,
        "source_path": source_rel,
        "destination_path": dest_rel,
        "target_path": dest_rel,
        "title": updated_meta.title,
        "domain": updated_meta.domain,
        "topic": updated_meta.topic,
        "pruned_dirs": pruned_dirs,
    }


def remove_note(store: "WikiStore", relative_path: str, reason: str = "deleted") -> Dict[str, Any]:
    """Delete a note under 00_Inbox/ or 01_Notes/ and prune any now-empty parent directories [CARD-744]."""
    target_path = store._resolve_safe_path(relative_path)
    if target_path is None:
        return {"success": False, "error": "Path traversal detected: target path is outside wiki root."}
    if _is_protected_template_path(store.root_dir, target_path):
        return {
            "success": False,
            "error": "Templates under 02_Resources/_Templates/ cannot be deleted with wiki_note_delete.",
        }
    if not target_path.is_file():
        return {"success": False, "error": f"Note '{relative_path}' not found."}

    rel_norm = target_path.resolve().relative_to(store.root_dir.resolve()).as_posix()
    parent_dir = target_path.parent
    target_path.unlink()
    pruned_dirs = prune_empty_parents(store.root_dir, parent_dir)
    return {
        "success": True,
        "deleted_path": rel_norm,
        "path": rel_norm,
        "pruned_dirs": pruned_dirs,
        "reason": reason or "deleted",
    }


def delete_note(store: "WikiStore", relative_path: str) -> bool:
    """Delete a note from disk and prune empty parent directories under 00_Inbox/ or 01_Notes/."""
    res = remove_note(store, relative_path)
    return bool(res.get("success"))


def delete_folder(store: "WikiStore", relative_path: str) -> Dict[str, Any]:
    """Delete a subfolder from the wiki vault, strictly guarding root folders [REQ-WIKI-024, REQ-WIKI-025]."""
    clean_rel = (relative_path or "").replace("\\", "/").strip().strip("/")
    clean_lower = clean_rel.lower()

    if not clean_rel or clean_lower in _PROTECTED_TOP_FOLDERS:
        return {
            "success": False,
            "error": f"Cannot delete protected root vault folder '{relative_path}'.",
        }

    target_path = store._resolve_safe_path(clean_rel)
    if target_path is None:
        return {"success": False, "error": "Path traversal detected: target path is outside wiki root."}

    resolved_str = str(target_path.resolve())
    root_str = str(store.root_dir.resolve())
    if resolved_str == root_str:
        return {"success": False, "error": "Cannot delete protected root vault directory."}

    for root_name in ["00_Inbox", "01_Notes", "02_Resources", "03_Archive", "inbox", "notes", "resources", "archive"]:
        if resolved_str == str((store.root_dir / root_name).resolve()):
            return {
                "success": False,
                "error": f"Cannot delete protected root vault folder '{relative_path}'.",
            }

    if not target_path.exists() or not target_path.is_dir():
        return {"success": False, "error": f"Folder '{relative_path}' not found."}

    try:
        parent_dir = target_path.parent
        shutil.rmtree(target_path)
        pruned_dirs = prune_empty_parents(store.root_dir, parent_dir)
        return {"success": True, "path": clean_rel, "pruned_dirs": pruned_dirs}
    except Exception as e:
        return {"success": False, "error": f"Failed to delete folder '{clean_rel}': {e}"}
