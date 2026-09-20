"""
CARD-388: Restore Developer and Tutor as unified platform agent packs.
Tests [REQ-388-001] through [REQ-388-006].
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.application.agent_packs.schema import (
    CHAT_HIDDEN_BY_ID,
    CHAT_SHOWN_BY_ID,
    PLATFORM_PACK_IDS,
    AgentPackManifest,
    is_platform_pack,
    is_visible_in_chat,
)
from src.domain.agents.profiles import (
    LEGACY_AGENT_ALIASES,
    canonical_agent_id,
)
from src.infrastructure.skills.platform_packs import (
    ALL_PLATFORM_PACK_IDS,
    RETIRED_PLATFORM_PACK_IDS,
    cleanup_orphaned_platform_packs,
    platform_packs_root,
)
from src.web.app import app
from tests.unit.agent_packs.catalog import load_platform_manifest, platform_pack_profile


def test_req_388_001_factory_seeds_exist():
    """[REQ-388-001] Factory seeds exist under platform-packs/ for developer and tutor."""
    root = platform_packs_root()
    for agent_id in ("developer", "tutor"):
        pack_dir = root / agent_id
        manifest_path = pack_dir / "pack.json"
        assert manifest_path.is_file(), f"Expected manifest at {manifest_path}"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = AgentPackManifest.model_validate(data)
        assert manifest.id == agent_id
        assert manifest.show_in_chat is True


def test_req_388_002_api_returns_developer_and_tutor():
    """[REQ-388-002] GET /api/agents returns developer and tutor with show_in_chat: true."""
    client = TestClient(app)
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert isinstance(agents, list)
    agent_map = {a["id"]: a for a in agents}

    assert "developer" in agent_map
    assert agent_map["developer"]["name"] == "Developer"
    assert agent_map["developer"]["show_in_chat"] is True

    assert "tutor" in agent_map
    assert agent_map["tutor"]["name"] == "Tutor"
    assert agent_map["tutor"]["show_in_chat"] is True


def test_req_388_003_platform_pack_registry_membership():
    """[REQ-388-003] developer and tutor are unified platform packs and chat-visible."""
    for agent_id in ("developer", "tutor"):
        assert agent_id in PLATFORM_PACK_IDS
        assert agent_id in ALL_PLATFORM_PACK_IDS
        assert is_platform_pack(agent_id)
        assert agent_id not in CHAT_HIDDEN_BY_ID
        assert agent_id in CHAT_SHOWN_BY_ID
        assert is_visible_in_chat({"id": agent_id, "show_in_chat": True}) is True


def test_req_388_004_skills_and_purposes():
    """[REQ-388-004] developer and tutor have designated skills and purpose."""
    dev = load_platform_manifest("developer")
    assert dev.purpose == "task_execution"
    assert "sdlc-engineering" in {s.id for s in dev.skills}

    dev_profile = platform_pack_profile("developer")
    assert "sdlc-engineering" in dev_profile.allowed_skill
    assert "cli_exec" in dev_profile.allowed_tool_names

    tutor = load_platform_manifest("tutor")
    assert tutor.purpose == "reasoning"
    assert "socratic-tutoring" in {s.id for s in tutor.skills}

    tutor_profile = platform_pack_profile("tutor")
    assert "socratic-tutoring" in tutor_profile.allowed_skill
    assert "wiki_note_read" in tutor_profile.allowed_tool_names


def test_req_388_006_negative_assertions_no_aliasing_no_retirement(tmp_path: Path):
    """[REQ-388-006] Negative assertions:

    - developer and tutor are NOT in LEGACY_AGENT_ALIASES.
    - canonical_agent_id does NOT redirect developer or tutor to autoreiv.
    - developer and tutor are NOT in RETIRED_PLATFORM_PACK_IDS.
    - retire_legacy_agent_packs does NOT delete developer or tutor packs.
    """
    assert "developer" not in LEGACY_AGENT_ALIASES
    assert "tutor" not in LEGACY_AGENT_ALIASES

    assert canonical_agent_id("developer") == "developer"
    assert canonical_agent_id("tutor") == "tutor"

    assert "developer" not in RETIRED_PLATFORM_PACK_IDS
    assert "tutor" not in RETIRED_PLATFORM_PACK_IDS

    # Create dummy user packs directory
    packs_dir = tmp_path / "packs"
    packs_dir.mkdir(parents=True)
    dev_dir = packs_dir / "developer"
    dev_dir.mkdir()
    (dev_dir / "pack.json").write_text("{}", encoding="utf-8")
    tutor_dir = packs_dir / "tutor"
    tutor_dir.mkdir()
    (tutor_dir / "pack.json").write_text("{}", encoding="utf-8")

    # Run cleanup_orphaned_platform_packs
    cleanup_orphaned_platform_packs(packs_path=packs_dir)

    # Assert developer and tutor directories remain intact
    assert dev_dir.is_dir()
    assert tutor_dir.is_dir()
    assert (dev_dir / "pack.json").is_file()
    assert (tutor_dir / "pack.json").is_file()


def test_req_388_007_unified_agent_pack_primitive_and_healing(tmp_path: Path):
    """[REQ-388-007] Drops platform vs custom distinction:

    - Legacy purpose: 'code' automatically normalizes to task_execution without failing validation.
    - install_platform_agent_packs heals legacy on-disk pack.json files.
    - Delete protection is restricted to core system agents (autoreiv, agent-builder);
      all other agent packs can be deleted.
    """
    from src.application.agent_packs.schema import AgentPackManifest
    from src.domain.agents.guardrails import AgentProfileGuardrail
    from src.domain.kernel.models import AgentOrigin
    from src.infrastructure.agents.registry import BuiltinAgentRegistry
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.infrastructure.skills.platform_packs import install_platform_agent_packs

    # 1. Validation handles purpose: "code" gracefully
    legacy_manifest_data = {
        "id": "developer",
        "name": "Developer",
        "purpose": "code",
        "system_prompt": "Code prompt",
    }
    manifest = AgentPackManifest.model_validate(legacy_manifest_data)
    assert manifest.purpose == "task_execution"

    guardrail_profile = AgentProfileGuardrail.validate(legacy_manifest_data)
    assert guardrail_profile.purpose.value == "task_execution"
    assert guardrail_profile.origin == AgentOrigin.PACK

    # 2. Disk healing in install_platform_agent_packs
    data_dir = tmp_path / "user_data"
    packs_dir = data_dir / "packs"
    packs_dir.mkdir(parents=True)
    dev_pack = packs_dir / "developer"
    dev_pack.mkdir()
    (dev_pack / "pack.json").write_text(
        json.dumps({"id": "developer", "name": "Developer", "purpose": "code", "origin": "platform"}),
        encoding="utf-8",
    )

    store = SQLiteStateStore(db_path=data_dir / "database" / "autoreiv.db")
    registry = BuiltinAgentRegistry(state_store=store)

    install_platform_agent_packs(
        data_dir=data_dir,
        agent_registry=registry,
    )

    # Verify disk was healed
    healed_data = json.loads((dev_pack / "pack.json").read_text(encoding="utf-8"))
    assert healed_data["purpose"] == "task_execution"
    dev_agent = registry.get_agent("developer")
    assert dev_agent is not None
    assert dev_agent.origin == AgentOrigin.PACK

    # 3. Deletion rules: autoreiv and agent-builder protected, others deletable
    assert registry.delete_custom_agent("autoreiv") is False
    assert registry.delete_custom_agent("agent-builder") is False

    # Seed an agent pack and verify it CAN be deleted
    seeded_profile = AgentProfileGuardrail.validate(
        {"id": "developer", "name": "Developer", "system_prompt": "Developer assistant for coding tasks"}
    )
    registry.register_profile(seeded_profile)
    assert registry.get_agent("developer") is not None
    assert registry.delete_custom_agent("developer") is True
    assert registry.get_agent("developer") is None

