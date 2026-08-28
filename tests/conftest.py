"""
Global Pytest Configuration & Hermetic Test Environment Isolation.
Ensures no automated tests ever mutate or overwrite the production/development database (./data/autoreiv.db).
"""

import pytest


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """Hermetically isolate the state database and wiki paths to temp folders for every test."""
    test_db = str(tmp_path / "test_isolated_autoreiv.db")
    test_wiki = str(tmp_path / "test_isolated_wiki")
    monkeypatch.setenv("AUTOREIV_DB_PATH", test_db)
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", test_wiki)
