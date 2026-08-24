"""
Unit tests for Settings & Agent Overrides Persistence in SQLite [REQ-SETTINGS-006, REQ-SETTINGS-005].
"""

import pytest

from src.domain.settings.models import AgentCustomization
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


def test_agent_overrides_crud(store):
    override = AgentCustomization(
        agent_id="general-assistant",
        tone="socratic",
        system_prompt="You are a Socratic tutor.",
        model="ollama/qwen2.5:32b",
        allowed_tool_names=["task_tracker_create", "task_tracker_list"],
        max_turns=15,
    )

    # Save
    store.save_agent_override(override)

    # Get
    fetched = store.get_agent_override("general-assistant")
    assert fetched is not None
    assert fetched.tone == "socratic"
    assert fetched.model == "ollama/qwen2.5:32b"
    assert fetched.max_turns == 15
    assert len(fetched.allowed_tool_names) == 2

    # List
    all_overrides = store.list_agent_overrides()
    assert len(all_overrides) == 1

    # Delete
    deleted = store.delete_agent_override("general-assistant")
    assert deleted is True
    assert store.get_agent_override("general-assistant") is None
