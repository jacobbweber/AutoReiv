"""
Unit tests for Settings & Agent Overrides Persistence in SQLite [REQ-SETTINGS-006, REQ-SETTINGS-005].
"""

import pytest

from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


def test_settings_key_value_crud(store):
    # Set setting
    store.set_setting("llm_providers", {"ollama": {"url": "http://192.168.1.100:11434"}})

    # Get setting
    val = store.get_setting("llm_providers")
    assert val is not None
    assert val["ollama"]["url"] == "http://192.168.1.100:11434"

    # Default fallback
    assert store.get_setting("nonexistent_key", default="fallback") == "fallback"


