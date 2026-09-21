"""
Unit tests for Wiki Note Archive and Backup to Archive [CARD-409].
"""

from pathlib import Path

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore


@pytest.fixture
def temp_store(tmp_path: Path) -> WikiStore:
    store = WikiStore(root_dir=tmp_path / "wiki")
    store.scaffold()
    return store


def test_archive_note_moves_to_archive_directory(temp_store: WikiStore):
    # 1. Create a note in inbox
    filed = temp_store.file_note(
        title="Test Archivable Note",
        content="This note should be moved to 03_Archive.",
        domain="general",
        topic="testing",
        category="inbox",
    )
    assert filed["success"] is True
    rel_path = filed["path"]
    assert (temp_store.root_dir / rel_path).exists()

    # 2. Archive the note
    archived = temp_store.archive_note(rel_path, reason="superseded by newer note")
    assert archived["success"] is True
    assert "archive_path" in archived
    assert archived["archive_path"].startswith("03_Archive/")

    # 3. Source file should be deleted (moved)
    assert not (temp_store.root_dir / rel_path).exists()

    # 4. Archive file exists and has updated metadata
    archived_file = temp_store.root_dir / archived["archive_path"]
    assert archived_file.exists()
    content = archived_file.read_text(encoding="utf-8")
    assert "status: archived" in content
    assert "archive_reason: superseded by newer note" in content
    assert "This note should be moved to 03_Archive." in content


def test_archive_note_preserve_source_for_backups(temp_store: WikiStore):
    # Create a note
    filed = temp_store.file_note(
        title="Note To Backup",
        content="Initial content version 1.",
        domain="engineering",
        topic="specs",
        category="notes",
    )
    rel_path = filed["path"]

    # Backup without deleting source
    backup_res = temp_store.archive_note(rel_path, reason="Backup before update", preserve_source=True)
    assert backup_res["success"] is True
    # Source still exists
    assert (temp_store.root_dir / rel_path).exists()
    # Backup also exists in 03_Archive/
    backup_file = temp_store.root_dir / backup_res["archive_path"]
    assert backup_file.exists()
    assert "Backup before update" in backup_file.read_text(encoding="utf-8")


def test_write_note_with_backup_to_archive(temp_store: WikiStore):
    # 1. Create original note in 01_Notes/
    filed = temp_store.file_note(
        title="Architecture Decision",
        content="Initial decision v1.",
        domain="systems",
        topic="architecture",
        category="notes",
    )
    rel_path = filed["path"]

    # 2. Update note with backup_to_archive=True
    updated = temp_store.write_note(
        relative_path=rel_path,
        content="Revised decision v2 with new template.",
        update_frontmatter={"summary": "Revised summary."},
        backup_to_archive=True,
    )
    assert updated["success"] is True

    # 3. Target note has new content
    new_content = (temp_store.root_dir / rel_path).read_text(encoding="utf-8")
    assert "Revised decision v2 with new template." in new_content

    # 4. 03_Archive/ has the backup
    archive_dir = temp_store.root_dir / "03_Archive"
    archive_files = list(archive_dir.glob("*.md"))
    assert len(archive_files) >= 1
    backup_texts = [f.read_text(encoding="utf-8") for f in archive_files]
    assert any("Initial decision v1." in txt for txt in backup_texts)


def test_wiki_tools_register_wiki_note_archive(tmp_path: Path):
    tools = WikiTools(wiki_root=tmp_path / "wiki")
    registry = ScopedToolRegistry()
    tools.register_tools(registry)

    assert "wiki_note_archive" in registry._tools
    assert "wiki_template_list" in registry._tools
    assert "wiki_template_read" in registry._tools

    # Verify pruned aliases are NOT in registry
    assert "list_wiki_templates" not in registry._tools
    assert "get_wiki_template" not in registry._tools
