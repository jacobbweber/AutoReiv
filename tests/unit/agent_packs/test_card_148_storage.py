"""
Unit tests for CARD-148: Agent Pack storage manifest, pack export/import, and SQLite persistence.
"""


from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def test_sqlite_store_persists_custom_agent_storage(tmp_path):
    db_file = tmp_path / "test_autoreiv.db"
    store = SQLiteStateStore(db_path=str(db_file))

    profile = AgentProfile(
        id="custom-db-agent",
        name="Custom DB Agent",
        description="Custom DB Agent",
        system_prompt="Store custom facts in SQLite.",
        storage_enabled=True,
        storage_type="sqlite",
    )
    store.save_agent_profile(profile)

    retrieved = store.get_agent_profile("custom-db-agent")
    assert retrieved is not None
    assert retrieved.storage_enabled is True
    assert retrieved.storage_type == "sqlite"

    all_profiles = store.list_custom_agent_profiles()
    matching = [p for p in all_profiles if p.id == "custom-db-agent"]
    assert len(matching) == 1
    assert matching[0].storage_enabled is True


def test_sqlite_store_persists_agent_override_storage(tmp_path):
    db_file = tmp_path / "test_autoreiv.db"
    store = SQLiteStateStore(db_path=str(db_file))

    override = AgentCustomization(
        agent_id="assistant",
        storage_enabled=True,
        storage_type="sqlite",
    )
    store.save_agent_override(override)

    retrieved = store.get_agent_override("assistant")
    assert retrieved is not None
    assert retrieved.storage_enabled is True
    assert retrieved.storage_type == "sqlite"

    all_overrides = store.list_agent_overrides()
    matching = [o for o in all_overrides if o.agent_id == "assistant"]
    assert len(matching) == 1
    assert matching[0].storage_enabled is True


def test_agent_api_eagerly_creates_storage_db(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from src.web.app import create_app

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    app = create_app()
    client = TestClient(app)

    payload = {
        "name": "Eager Finance Tracker",
        "description": "Tracks money",
        "system_prompt": "You track money in SQLite.",
        "storage_enabled": True,
        "storage_type": "sqlite",
    }
    res = client.post("/api/agents", json=payload)
    assert res.status_code == 200
    agent_id = res.json()["agent"]["id"]
    db_file = tmp_path / "data" / "agents" / agent_id / "storage.db"  # CARD-570 layout
    assert db_file.is_file()
