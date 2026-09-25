"""
Global Pytest Configuration & Hermetic Test Environment Isolation.
Ensures no automated tests ever mutate or overwrite the production/development database (./data/autoreiv.db).
"""

import os
import tempfile
from pathlib import Path

import pytest


def _load_smoke_guard():
    """Shared live-data guard from scripts/smoke_server.py [CARD-467]."""
    import importlib.util

    script = Path(__file__).resolve().parents[1] / "scripts" / "smoke_server.py"
    spec = importlib.util.spec_from_file_location("autoreiv_smoke_server", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def isolate_pytest_data_env(environ=None, base=None):
    """Force every AutoReiv data path to a temp tree, whatever the shell already set [CARD-467].

    ``setdefault`` was a no-op when the shell had the live ``AUTOREIV_DATA_DIR``, so the
    import-time ``src.web.app.app`` bootstrapped against live AppData packs (CARD-455).
    """
    environ = os.environ if environ is None else environ
    base = Path(tempfile.mkdtemp(prefix="autoreiv-pytest-")) if base is None else Path(base)
    environ["AUTOREIV_DATA_DIR"] = str(base / "data")
    environ["AUTOREIV_DB_PATH"] = str(base / "pytest_bootstrap.db")
    environ["AUTOREIV_WIKI_PATH"] = str(base / "wiki")
    environ.pop("AUTOREIV_BACKUP_DIR", None)
    return base


def live_appdata_problems(environ=None):
    """Messages for any resolved data path that lands in live user data (empty = safe)."""
    from src.infrastructure.data.resolver import DataDirResolver

    guard = _load_smoke_guard()
    environ = os.environ if environ is None else environ
    resolved = DataDirResolver().resolve()
    paths = {
        "root": resolved.root,
        "db_path": resolved.db_path,
        "wiki_path": resolved.wiki_path,
        "packs_path": resolved.packs_path,
        "skills_path": resolved.skills_path,
        "backups_path": resolved.backups_path,
    }
    return guard.live_data_problems(paths, guard.live_data_roots(environ))


def pytest_configure(config):
    """Isolate data-dir env before any src.web.app import can bootstrap or migrate live data."""
    isolate_pytest_data_env()
    problems = live_appdata_problems()
    if problems:
        pytest.exit(
            "CARD-467: refusing to run tests against live AutoReiv data:\n  " + "\n  ".join(problems),
            returncode=3,
        )


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """Hermetically isolate the state database and wiki paths to temp folders for every test."""
    data_dir = str(tmp_path / "test_isolated_data")
    test_db = str(tmp_path / "test_isolated_autoreiv.db")
    test_wiki = str(tmp_path / "test_isolated_wiki")
    monkeypatch.setenv("AUTOREIV_DATA_DIR", data_dir)
    monkeypatch.setenv("AUTOREIV_DB_PATH", test_db)
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", test_wiki)
