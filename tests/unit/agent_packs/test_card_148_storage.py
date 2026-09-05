"""
Unit tests for CARD-148: Agent Pack storage manifest, pack export/import, and SQLite persistence.
"""

import json
from pathlib import Path

from src.application.agent_packs.schema import AgentPackManifest, PackStorageConfig
from src.application.agent_packs.service import AgentPackService
from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def test_agent_pack_manifest_storage_serialization():
    manifest = AgentPackManifest(
        id="finance-specialist",
        name="Finance Specialist",
        description="Tracks transactions",
        system_prompt="Manage personal finances.",
        storage=PackStorageConfig(enabled=True, type="sqlite"),
    )
    assert manifest.storage is not None
    assert manifest.storage.enabled is True
    assert manifest.storage.type == "sqlite"
    assert manifest.storage_enabled is True
    assert manifest.storage_type == "sqlite"

    dumped = manifest.model_dump()
    assert dumped["storage"]["enabled"] is True
    assert dumped["storage"]["type"] == "sqlite"

    # Test roundtrip from raw JSON
    raw_json = json.dumps(dumped)
    reloaded = AgentPackManifest.model_validate_json(raw_json)
    assert reloaded.storage.enabled is True
    assert reloaded.storage_enabled is True


def test_manifest_from_profile_preserves_storage():
    profile = AgentProfile(
        id="ledger-agent",
        name="Ledger Agent",
        description="A ledger agent",
        system_prompt="Manage books.",
        storage_enabled=True,
        storage_type="sqlite",
    )
    service = AgentPackService(data_dir=Path("/fake/data"))
    manifest = service.manifest_from_profile(profile)
    assert manifest.storage is not None
    assert manifest.storage.enabled is True
    assert manifest.storage.type == "sqlite"
    assert manifest.storage_enabled is True


def test_export_and_import_pack_preserves_storage(tmp_path):
    # Setup state store and registry
    db_file = tmp_path / "test_autoreiv.db"
    store = SQLiteStateStore(db_path=str(db_file))

    profile = AgentProfile(
        id="storage-tracker",
        name="Storage Tracker",
        description="Tracks storage",
        system_prompt="You track things in SQLite.",
        storage_enabled=True,
        storage_type="sqlite",
    )
    store.save_agent_profile(profile)

    registry = BuiltinAgentRegistry(profiles=[], state_store=store)
    registry.register_custom_agent(profile)

    service = AgentPackService(data_dir=tmp_path, agent_registry=registry, store=store)

    # Export
    exported_folder = service.export_folder("storage-tracker")
    manifest_path = exported_folder / "pack.json"
    assert manifest_path.is_file()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data.get("storage", {}).get("enabled") is True
    assert manifest_data.get("storage", {}).get("type") == "sqlite"

    # Import under fresh service / into registry
    imported_profile = service.import_path(exported_folder)
    assert imported_profile.id == "storage-tracker"
    assert imported_profile.storage_enabled is True
    assert imported_profile.storage_type == "sqlite"


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
    snake_id = agent_id.replace("-", "_")

    db_file = tmp_path / "data" / "packs" / agent_id / f"{snake_id}_storage.db"
    assert db_file.is_file()
