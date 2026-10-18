"""CARD-707: Lifecycle and data safety regression tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.application.system.update_service import UpdateService
from src.domain.security.vault import CredentialVault
from src.infrastructure.content.store import ContentStore, is_known_tool, reset_store, set_tool_registry
from src.infrastructure.data.resolver import BLED_AGENT_SKILL_IDS, prune_bled_platform_skills
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.guard


def test_shipped_skills_never_in_bled_agent_skill_ids_and_user_copies_survive_prune(tmp_path: Path):
    """User copies of shipped skills (platform-health, session-inspect, etc.) must survive prune_bled_platform_skills."""
    repo_platform_skills = Path(__file__).resolve().parents[3] / "platform" / "skills"
    shipped_ids = {p.parent.name for p in repo_platform_skills.glob("*/SKILL.md")}
    assert "platform-health" in shipped_ids
    assert "session-inspect" in shipped_ids
    overlap = shipped_ids & set(BLED_AGENT_SKILL_IDS)
    assert overlap == set(), f"Shipped platform skills must never be in BLED_AGENT_SKILL_IDS: {overlap}"

    # Create user customizations of platform-health and session-inspect plus a true bled skill
    data_root = tmp_path / "data"
    store = ContentStore(data_root=data_root)
    store.skills.save(
        "platform-health",
        {"name": "Platform Health", "description": "Custom", "tools": ["inspect_system_health"]},
        "Custom user platform-health runbook.\n",
    )
    store.skills.save(
        "session-inspect",
        {"name": "Session Inspect", "description": "Custom", "tools": ["inspect_session_history"]},
        "Custom user session-inspect runbook.\n",
    )
    bled_dir = data_root / "skills" / "hyperv-networking"
    bled_dir.mkdir(parents=True)
    (bled_dir / "SKILL.md").write_text("---\nname: Old Bled\n---\n", encoding="utf-8")

    pruned = prune_bled_platform_skills(data_root / "skills")
    assert "hyperv-networking" in pruned
    assert not bled_dir.exists()

    # Negative assertion: user copies of shipped skills were NOT deleted
    assert "platform-health" not in pruned
    assert "session-inspect" not in pruned
    assert (data_root / "skills" / "platform-health" / "SKILL.md").is_file()
    assert (data_root / "skills" / "session-inspect" / "SKILL.md").is_file()
    loaded = store.skills.load("platform-health")
    assert loaded is not None and loaded.source == "user"
    assert "Custom user platform-health runbook." in loaded.body


def test_credential_vault_resolves_data_dir_and_fails_loudly_on_unwritable_key(tmp_path: Path, monkeypatch):
    """CredentialVault must default to DataDirResolver root (not ~/.autoreiv) and fail if key cannot be persisted."""
    data_dir = tmp_path / "live_data"
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir(parents=True)
    monkeypatch.delenv("AUTOREIV_DATA_DIR", raising=False)
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    from types import SimpleNamespace

    from src.infrastructure.data.resolver import DataDirResolver

    monkeypatch.setattr(
        DataDirResolver,
        "resolve",
        lambda self: SimpleNamespace(root=data_dir),
    )

    vault = CredentialVault()
    ct, nonce = vault.encrypt("top-secret-value")
    assert (data_dir / ".vault_key").is_file()
    # Negative assertion: never wrote to ~/.autoreiv
    assert not (fake_home / ".autoreiv" / ".vault_key").exists()

    vault_reloaded = CredentialVault()
    assert vault_reloaded.decrypt(ct, nonce) == "top-secret-value"

    # If key file write fails, CredentialVault must raise instead of silently using an ephemeral in-memory key
    unwritable_dir = tmp_path / "valid_parent"
    unwritable_dir.mkdir(parents=True)
    key_as_dir = unwritable_dir / ".vault_key"
    key_as_dir.mkdir(parents=True)  # path.is_file() is False, path.parent.mkdir() succeeds, path.write_bytes() raises IsADirectoryError
    with pytest.raises(OSError):
        CredentialVault(key_file=key_as_dir)


def test_is_known_tool_fails_closed_when_registry_raises():
    """is_known_tool must return False (fail closed) if get_tool_definition raises an unexpected error."""

    class _BrokenRegistry:
        def get_tool_definition(self, name: str):
            raise RuntimeError("registry corrupted")

    set_tool_registry(_BrokenRegistry())
    try:
        assert is_known_tool("any_tool_name") is False
    finally:
        reset_store()


def test_update_service_snapshot_database_uses_online_sqlite_backup_including_wal(tmp_path: Path):
    """_snapshot_database must capture uncommitted WAL frames via SQLite online backup API."""
    data_dir = tmp_path / "data"
    db_dir = data_dir / "database"
    db_dir.mkdir(parents=True)
    db_file = db_dir / "autoreiv.db"

    store = SQLiteStateStore(db_path=str(db_file))
    store.initialize_db()

    # Keep a live WAL connection open so frames remain in the -wal file and are not checkpointed on close
    live_conn = sqlite3.connect(str(db_file))
    try:
        live_conn.execute("PRAGMA journal_mode = WAL;")
        live_conn.execute("PRAGMA wal_autocheckpoint = 0;")
        live_conn.execute(
            "INSERT OR REPLACE INTO settings (key, value_json) VALUES ('wal_only_key', '{\"status\": \"in_wal_frame\"}')"
        )
        live_conn.commit()

        svc = UpdateService(
            state_store=store,
            repo_root=str(tmp_path),
            data_dir=str(data_dir),
        )
        snap_path = svc._snapshot_database()
        assert snap_path is not None
        assert Path(snap_path).is_file()

        # Verify the snapshot is a valid standalone SQLite database containing the WAL-committed setting
        conn = sqlite3.connect(snap_path)
        try:
            row = conn.execute("SELECT value_json FROM settings WHERE key = 'wal_only_key'").fetchone()
            assert row is not None, "Snapshot missed WAL frames because it used shutil.copy2 instead of sqlite3.backup()"
            assert "in_wal_frame" in row[0]
        finally:
            conn.close()
    finally:
        live_conn.close()

