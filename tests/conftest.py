"""
Global Pytest Configuration & Hermetic Test Environment Isolation.
Ensures no automated tests ever mutate or overwrite the production/development database (./data/autoreiv.db).
"""

import os
import tempfile
from pathlib import Path

import pytest


def pytest_configure(config):
    """Isolate data-dir env before any src.web.app import can copy-migrate live data."""
    base = Path(tempfile.mkdtemp(prefix="autoreiv-pytest-"))
    os.environ.setdefault("AUTOREIV_DATA_DIR", str(base / "data"))
    os.environ.setdefault("AUTOREIV_DB_PATH", str(base / "pytest_bootstrap.db"))
    os.environ.setdefault("AUTOREIV_WIKI_PATH", str(base / "wiki"))


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """Hermetically isolate the state database and wiki paths to temp folders for every test."""
    data_dir = str(tmp_path / "test_isolated_data")
    test_db = str(tmp_path / "test_isolated_autoreiv.db")
    test_wiki = str(tmp_path / "test_isolated_wiki")
    monkeypatch.setenv("AUTOREIV_DATA_DIR", data_dir)
    monkeypatch.setenv("AUTOREIV_DB_PATH", test_db)
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", test_wiki)
