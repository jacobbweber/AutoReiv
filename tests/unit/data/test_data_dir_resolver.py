"""Resolver order, layout, and copy-migrate [REQ-DATA-001 - REQ-DATA-006]."""

import json
import sqlite3
from pathlib import Path

import pytest

from src.infrastructure.data.resolver import (
    DataDirMigrationError,
    DataDirResolver,
    bootstrap_data_dir,
)


def _clear_path_env(monkeypatch):
    monkeypatch.delenv("AUTOREIV_DATA_DIR", raising=False)
    monkeypatch.delenv("AUTOREIV_DB_PATH", raising=False)
    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)


def _seed_checkout(checkout: Path) -> None:
    data = checkout / "data"
    data.mkdir(parents=True)
    (data / "autoreiv.db").write_bytes(b"LIVE-DB-BYTES")
    wiki = data / "wiki"
    wiki.mkdir()
    (wiki / "inbox").mkdir()
    (wiki / "inbox" / "welcome.md").write_text("welcome from checkout", encoding="utf-8")


def test_env_wins_over_setting_and_default(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "from-env"))
    resolver = DataDirResolver(
        setting_data_dir=str(tmp_path / "from-setting"),
        checkout_root=tmp_path / "co",
        local_appdata=tmp_path / "la",
        home=tmp_path / "home",
        in_docker=False,
    )
    paths = resolver.resolve()
    assert paths.root == tmp_path / "from-env"
    assert paths.db_path == tmp_path / "from-env" / "autoreiv.db"
    assert paths.wiki_path == tmp_path / "from-env" / "wiki"
    assert paths.skills_path == tmp_path / "from-env" / "skills"


def test_setting_wins_over_platform_default(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    resolver = DataDirResolver(
        setting_data_dir=str(tmp_path / "from-setting"),
        checkout_root=tmp_path / "co",
        local_appdata=tmp_path / "la",
        home=tmp_path / "home",
        in_docker=False,
    )
    paths = resolver.resolve()
    assert paths.root == tmp_path / "from-setting"


def test_windows_platform_default(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    resolver = DataDirResolver(
        checkout_root=tmp_path / "co",
        local_appdata=tmp_path / "la",
        home=tmp_path / "home",
        in_docker=False,
        os_name="nt",
    )
    paths = resolver.resolve()
    assert paths.root == tmp_path / "la" / "AutoReiv"
    assert "Projects" not in str(paths.root)


def test_posix_platform_default(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    resolver = DataDirResolver(
        checkout_root=tmp_path / "co",
        local_appdata=tmp_path / "la",
        home=tmp_path / "home",
        in_docker=False,
        os_name="posix",
    )
    paths = resolver.resolve()
    assert paths.root == tmp_path / "home" / ".autoreiv"


def test_docker_platform_default(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    resolver = DataDirResolver(
        checkout_root=tmp_path / "co",
        local_appdata=tmp_path / "la",
        home=tmp_path / "home",
        in_docker=True,
    )
    paths = resolver.resolve()
    assert paths.root == Path("/data")


def test_layout_derived_paths(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "tree"))
    resolver = DataDirResolver(checkout_root=tmp_path / "co", in_docker=False)
    paths = resolver.resolve()
    resolver.ensure_layout(paths)
    assert paths.db_path == paths.root / "autoreiv.db"
    assert paths.wiki_path == paths.root / "wiki"
    assert paths.skills_path == paths.root / "skills"
    assert paths.agents_path == paths.root / "agents"
    assert paths.job_templates_path == paths.root / "templates" / "jobs"
    assert paths.wiki_path.is_dir()
    assert paths.skills_path.is_dir()
    assert paths.agents_path.is_dir()
    assert paths.job_templates_path.is_dir()


def test_explicit_db_and_wiki_env_win(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "tree"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "custom.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "custom-wiki"))
    resolver = DataDirResolver(checkout_root=tmp_path / "co", in_docker=False)
    paths = resolver.resolve()
    assert paths.root == tmp_path / "tree"
    assert paths.db_path == tmp_path / "custom.db"
    assert paths.wiki_path == tmp_path / "custom-wiki"
    assert paths.skills_path == tmp_path / "tree" / "skills"


def test_legacy_checkout_env_is_not_explicit_override(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    checkout = tmp_path / "co"
    dest = tmp_path / "dest"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(dest))
    monkeypatch.setenv("AUTOREIV_DB_PATH", "./data/autoreiv.db")
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", "./data/wiki")
    resolver = DataDirResolver(checkout_root=checkout, in_docker=False)
    paths = resolver.resolve()
    assert paths.db_path == dest / "autoreiv.db"
    assert paths.wiki_path == dest / "wiki"


def test_peek_setting_from_platform_default_db(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    la = tmp_path / "la"
    default_root = la / "AutoReiv"
    default_root.mkdir(parents=True)
    db = default_root / "autoreiv.db"
    custom = tmp_path / "custom-from-setting"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value_json TEXT, updated_at TEXT)")
    conn.execute(
        "INSERT INTO settings (key, value_json, updated_at) VALUES (?, ?, ?)",
        ("data_dir", json.dumps(str(custom)), ""),
    )
    conn.commit()
    conn.close()
    resolver = DataDirResolver(
        checkout_root=tmp_path / "co",
        local_appdata=la,
        home=tmp_path / "home",
        in_docker=False,
        os_name="nt",
    )
    paths = resolver.resolve()
    assert paths.root == custom


def test_migrate_copies_checkout_data_into_empty_dest(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    checkout = tmp_path / "co"
    dest = tmp_path / "dest"
    _seed_checkout(checkout)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(dest))
    resolver = DataDirResolver(checkout_root=checkout, in_docker=False)
    paths = resolver.resolve()
    resolver.ensure_layout(paths)
    resolver.migrate_if_needed(paths)
    assert paths.db_path.read_bytes() == b"LIVE-DB-BYTES"
    assert (paths.wiki_path / "inbox" / "welcome.md").read_text(encoding="utf-8") == "welcome from checkout"
    assert (checkout / "data" / "autoreiv.db").read_bytes() == b"LIVE-DB-BYTES"
    assert (checkout / "data" / "wiki" / "inbox" / "welcome.md").exists()


def test_migrate_does_not_overwrite_populated_dest(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    checkout = tmp_path / "co"
    dest = tmp_path / "dest"
    _seed_checkout(checkout)
    dest.mkdir()
    (dest / "autoreiv.db").write_bytes(b"DEST-DB")
    (dest / "wiki").mkdir()
    (dest / "wiki" / "keep.md").write_text("keep me", encoding="utf-8")
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(dest))
    resolver = DataDirResolver(checkout_root=checkout, in_docker=False)
    paths = resolver.resolve()
    resolver.migrate_if_needed(paths)
    assert (dest / "autoreiv.db").read_bytes() == b"DEST-DB"
    assert (dest / "wiki" / "keep.md").read_text(encoding="utf-8") == "keep me"
    assert not (dest / "wiki" / "inbox" / "welcome.md").exists()
    assert (checkout / "data" / "autoreiv.db").read_bytes() == b"LIVE-DB-BYTES"


def test_migrate_failed_copy_does_not_create_empty_dest_db(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    checkout = tmp_path / "co"
    dest = tmp_path / "dest"
    _seed_checkout(checkout)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(dest))

    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("src.infrastructure.data.resolver.shutil.copy2", boom)
    resolver = DataDirResolver(checkout_root=checkout, in_docker=False)
    paths = resolver.resolve()
    resolver.ensure_layout(paths)
    with pytest.raises(DataDirMigrationError):
        resolver.migrate_if_needed(paths)
    assert not (dest / "autoreiv.db").exists()
    assert (checkout / "data" / "autoreiv.db").read_bytes() == b"LIVE-DB-BYTES"


def test_migrate_uses_explicit_live_env_as_source(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    checkout = tmp_path / "co"
    checkout.mkdir()
    live_db = tmp_path / "elsewhere" / "live.db"
    live_db.parent.mkdir()
    live_db.write_bytes(b"ENV-LIVE")
    dest = tmp_path / "dest"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(dest))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(live_db))
    resolver = DataDirResolver(checkout_root=checkout, in_docker=False)
    paths = resolver.resolve()
    assert paths.db_path == live_db
    resolver.ensure_layout(paths)
    resolver.migrate_if_needed(paths)
    assert (dest / "autoreiv.db").read_bytes() == b"ENV-LIVE"
    assert live_db.read_bytes() == b"ENV-LIVE"


def test_bootstrap_does_not_touch_live_checkout_when_isolated(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    checkout = tmp_path / "co"
    _seed_checkout(checkout)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "isolated-data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "isolated.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "isolated-wiki"))
    paths = bootstrap_data_dir(checkout_root=checkout)
    assert not (tmp_path / "isolated-data" / "autoreiv.db").exists()
    assert (checkout / "data" / "autoreiv.db").read_bytes() == b"LIVE-DB-BYTES"
    assert paths.db_path == tmp_path / "isolated.db"


def test_docker_compose_is_one_volume():
    text = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "AUTOREIV_DATA_DIR=/data" in text
    assert "./data/autoreiv.db:/data/autoreiv.db" not in text
    assert "./data/wiki:/data/wiki" not in text
    assert "autoreiv-data:/data" in text


def test_env_example_documents_data_dir():
    text = Path(".env.example").read_text(encoding="utf-8")
    assert "AUTOREIV_DATA_DIR" in text


def test_absolute_checkout_env_is_not_explicit_override(tmp_path, monkeypatch):
    _clear_path_env(monkeypatch)
    checkout = tmp_path / "co"
    dest = tmp_path / "dest"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(dest))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(checkout / "data" / "autoreiv.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(checkout / "data" / "wiki"))
    resolver = DataDirResolver(checkout_root=checkout, in_docker=False)
    paths = resolver.resolve()
    assert paths.db_path == dest / "autoreiv.db"
    assert paths.wiki_path == dest / "wiki"

