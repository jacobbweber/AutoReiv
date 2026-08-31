"""Backup and restore of the data dir [REQ-DATA-007, REQ-DATA-008]."""

import sqlite3
import zipfile
from pathlib import Path

import pytest

from src.infrastructure.data.backup import DataDirBackupService, DataDirRestoreError
from src.infrastructure.data.resolver import DataDirPaths


def _paths(root: Path) -> DataDirPaths:
    return DataDirPaths(
        root=root,
        db_path=root / "autoreiv.db",
        wiki_path=root / "wiki",
        skills_path=root / "skills",
        agents_path=root / "agents",
        job_templates_path=root / "templates" / "jobs",
    )


def _seed_tree(root: Path, marker: str = "v1") -> None:
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(root / "autoreiv.db"))
    conn.execute("CREATE TABLE IF NOT EXISTS notes (body TEXT)")
    conn.execute("DELETE FROM notes")
    conn.execute("INSERT INTO notes VALUES (?)", (marker,))
    conn.commit()
    conn.close()
    wiki = root / "wiki"
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / "inbox.md").write_text(f"wiki-{marker}", encoding="utf-8")
    pack = root / "skills" / "weekly-review"
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "SKILL.md").write_text(f"# {marker}\n", encoding="utf-8")
    (root / "settings-related.txt").write_text(f"settings-{marker}", encoding="utf-8")


def _note_body(db: Path) -> str:
    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute("SELECT body FROM notes").fetchone()
        return row[0] if row else ""
    finally:
        conn.close()


def test_backup_zip_contains_db_wiki_skills_not_checkout(tmp_path):
    data = tmp_path / "data"
    checkout = tmp_path / "repo"
    checkout.mkdir()
    (checkout / "secret.py").write_text("not-in-backup", encoding="utf-8")
    _seed_tree(data, "v1")
    (data / ".venv" / "lib").mkdir(parents=True)
    (data / ".venv" / "lib" / "x.py").write_text("venv", encoding="utf-8")

    dest = tmp_path / "out" / "backup.zip"
    result = DataDirBackupService(_paths(data)).backup(dest)
    assert result == dest
    assert dest.is_file()

    with zipfile.ZipFile(dest) as zf:
        names = set(zf.namelist())
    assert "autoreiv.db" in names
    assert "wiki/inbox.md" in names
    assert "skills/weekly-review/SKILL.md" in names
    assert "settings-related.txt" in names
    assert not any(n.startswith(".venv/") for n in names)
    assert "secret.py" not in names
    assert not any("secret.py" in n for n in names)
    with zipfile.ZipFile(dest) as zf:
        assert b"not-in-backup" not in zf.read("wiki/inbox.md")
        assert b"wiki-v1" in zf.read("wiki/inbox.md")


def test_backup_default_dest_under_backups(tmp_path):
    data = tmp_path / "data"
    _seed_tree(data)
    result = DataDirBackupService(_paths(data)).backup()
    assert result.parent == data / "backups"
    assert result.name.startswith("autoreiv-data-")
    assert result.suffix == ".zip"
    with zipfile.ZipFile(result) as zf:
        names = zf.namelist()
    assert "autoreiv.db" in names
    assert not any(n.startswith("backups/") for n in names)


def test_restore_without_confirm_is_noop(tmp_path):
    data = tmp_path / "data"
    _seed_tree(data, "live")
    dest = tmp_path / "b.zip"
    svc = DataDirBackupService(_paths(data))
    svc.backup(dest)
    (data / "wiki" / "inbox.md").write_text("changed", encoding="utf-8")
    svc.restore(dest, confirm=False)
    assert (data / "wiki" / "inbox.md").read_text(encoding="utf-8") == "changed"
    assert _note_body(data / "autoreiv.db") == "live"


def test_restore_confirmed_replaces_tree_round_trip(tmp_path):
    data = tmp_path / "data"
    _seed_tree(data, "v1")
    dest = tmp_path / "b.zip"
    svc = DataDirBackupService(_paths(data))
    svc.backup(dest)

    (data / "wiki" / "inbox.md").write_text("v2", encoding="utf-8")
    (data / "wiki" / "extra.md").write_text("should-vanish", encoding="utf-8")
    (data / "skills" / "weekly-review" / "SKILL.md").write_text("# v2\n", encoding="utf-8")
    conn = sqlite3.connect(str(data / "autoreiv.db"))
    conn.execute("UPDATE notes SET body = 'v2'")
    conn.commit()
    conn.close()

    checkout = tmp_path / "repo" / "src"
    checkout.mkdir(parents=True)
    (checkout / "keep.py").write_text("checkout", encoding="utf-8")

    svc.restore(dest, confirm=True)

    assert (data / "wiki" / "inbox.md").read_text(encoding="utf-8") == "wiki-v1"
    assert not (data / "wiki" / "extra.md").exists()
    assert (data / "skills" / "weekly-review" / "SKILL.md").read_text(encoding="utf-8") == "# v1\n"
    assert (data / "settings-related.txt").read_text(encoding="utf-8") == "settings-v1"
    assert _note_body(data / "autoreiv.db") == "v1"
    assert (checkout / "keep.py").read_text(encoding="utf-8") == "checkout"
    pre = list((data / "backups").glob("pre-restore-*.zip"))
    assert len(pre) == 1


def test_restore_missing_db_rejected_live_tree_unchanged(tmp_path):
    data = tmp_path / "data"
    _seed_tree(data, "live")
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("wiki/inbox.md", "no-db")
    svc = DataDirBackupService(_paths(data))
    with pytest.raises(DataDirRestoreError, match="missing autoreiv.db"):
        svc.restore(bad, confirm=True)
    assert _note_body(data / "autoreiv.db") == "live"
    assert (data / "wiki" / "inbox.md").read_text(encoding="utf-8") == "wiki-live"


def test_restore_path_escape_rejected(tmp_path):
    data = tmp_path / "data"
    _seed_tree(data, "live")
    bad = tmp_path / "escape.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("autoreiv.db", b"x")
        zf.writestr("../outside.txt", "nope")
    svc = DataDirBackupService(_paths(data))
    with pytest.raises(DataDirRestoreError, match="Illegal path"):
        svc.restore(bad, confirm=True)
    assert not (tmp_path / "outside.txt").exists()
    assert _note_body(data / "autoreiv.db") == "live"
