"""
Unit tests for CARD-116: Memory fields on AgentProfile, AgentPackManifest,
and database exclusion from pack zip exports.
"""

import zipfile

from src.application.agent_packs.schema import AgentPackManifest, PackMemoryConfig
from src.domain.agents.guardrails import AgentProfileGuardrail
from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization


def test_agent_profile_memory_fields_defaults():
    profile = AgentProfile(
        id="analyst-bot",
        name="Analyst Bot",
        description="Analyzes data",
        system_prompt="You are a data analyst agent.",
    )
    assert hasattr(profile, "memory_enabled")
    assert profile.memory_enabled is True
    assert hasattr(profile, "memory_retention_days")
    assert profile.memory_retention_days == 30
    assert hasattr(profile, "pinned_memory")
    assert profile.pinned_memory == ""


def test_agent_profile_guardrail_validates_memory():
    data = {
        "id": "research-bot",
        "name": "Research Bot",
        "system_prompt": "You conduct deep research.",
        "memory_enabled": True,
        "memory_retention_days": 60,
        "pinned_memory": "Never delete source URLs.",
    }
    profile = AgentProfileGuardrail.validate(data)
    assert profile.memory_enabled is True
    assert profile.memory_retention_days == 60
    assert profile.pinned_memory == "Never delete source URLs."


def test_agent_customization_memory_fields():
    custom = AgentCustomization(
        agent_id="research-bot",
        memory_enabled=False,
        memory_retention_days=14,
        pinned_memory="Always use metric units.",
    )
    assert custom.memory_enabled is False
    assert custom.memory_retention_days == 14
    assert custom.pinned_memory == "Always use metric units."


def test_agent_pack_manifest_memory_round_trip():
    manifest = AgentPackManifest(
        id="coder-bot",
        name="Coder Bot",
        system_prompt="You write Python code.",
        memory=PackMemoryConfig(
            enabled=True,
            retention_days=45,
            pinned_memory="Always use type annotations.",
        ),
    )
    assert manifest.memory_enabled is True
    assert manifest.memory_retention_days == 45
    assert manifest.pinned_memory == "Always use type annotations."


def test_export_zip_excludes_database_files(tmp_path):
    # Setup test pack folder with skill, pack.json, and a runtime database
    pack_dir = tmp_path / "packs" / "test-agent"
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "pack.json").write_text('{"id":"test-agent","name":"Test Agent"}', encoding="utf-8")

    # Create dummy database files that must NOT be exported
    (pack_dir / "test_agent_memory.db").write_bytes(b"SQLITE-MEMORY-BINARY")
    (pack_dir / "test_agent_storage.db").write_bytes(b"SQLITE-STORAGE-BINARY")
    (pack_dir / "test_agent_memory.db-wal").write_bytes(b"SQLITE-WAL")
    (pack_dir / "test_agent_memory.db-shm").write_bytes(b"SQLITE-SHM")

    # Call _zip_dir
    from src.application.agent_packs.service import _zip_dir

    zip_file = tmp_path / "test-agent.zip"
    _zip_dir(pack_dir, zip_file)

    assert zip_file.is_file()
    with zipfile.ZipFile(zip_file, "r") as zf:
        namelist = zf.namelist()
        assert "pack.json" in namelist
        # Assert databases and journals were excluded
        assert "test_agent_memory.db" not in namelist
        assert "test_agent_storage.db" not in namelist
        assert "test_agent_memory.db-wal" not in namelist
        assert "test_agent_memory.db-shm" not in namelist
