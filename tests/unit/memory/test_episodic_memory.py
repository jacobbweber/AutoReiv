"""
Unit tests for Episodic Fact Memory [REQ-MEMORY-003].
"""

import pytest

from src.application.skills.memory_skill import EpisodicMemorySkill
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


def test_save_and_get_episodic_facts(store):
    store.save_fact(
        entity="user",
        key="preferred_os",
        value="Ubuntu 24.04 CLI",
        confidence=1.0,
        source_session_id="sess_123",
    )
    store.save_fact(
        entity="user",
        key="target_hardware",
        value="Nimo Mini PC 2L 128GB",
        confidence=1.0,
    )

    facts = store.get_facts(entity="user")
    assert len(facts) == 2
    fact_dict = {f["key"]: f["value"] for f in facts}
    assert fact_dict["preferred_os"] == "Ubuntu 24.04 CLI"
    assert fact_dict["target_hardware"] == "Nimo Mini PC 2L 128GB"


def test_update_and_delete_episodic_fact(store):
    store.save_fact(entity="system", key="log_level", value="DEBUG")
    facts = store.get_facts(entity="system")
    assert facts[0]["value"] == "DEBUG"

    # Update
    store.save_fact(entity="system", key="log_level", value="INFO")
    facts = store.get_facts(entity="system")
    assert len(facts) == 1
    assert facts[0]["value"] == "INFO"

    # Delete
    store.delete_fact(entity="system", key="log_level")
    facts = store.get_facts(entity="system")
    assert len(facts) == 0


def test_episodic_memory_skill(store):
    skill = EpisodicMemorySkill(store=store)

    # Tool save
    res = skill.save_fact(entity="user", key="timezone", value="America/New_York")
    assert res["status"] == "saved"

    # Tool get
    facts = skill.get_facts(entity="user")
    assert len(facts) == 1
    assert facts[0]["key"] == "timezone"
    assert facts[0]["value"] == "America/New_York"
