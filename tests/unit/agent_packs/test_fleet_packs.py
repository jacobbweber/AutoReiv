"""
Unit tests for Fleet Packs, FleetManifest, and Three-Tier Skill Separation [CARD-199, REQ-FLEET-010 - REQ-FLEET-015].
"""

import json
from pathlib import Path

import pytest

from src.application.agent_packs.schema import (
    PLATFORM_SKILL_TOOLS,
    FleetManifest,
)


def test_fleet_manifest_schema():
    """Verify FleetManifest schema validates properly."""
    data = {
        "schema_version": "1.0",
        "id": "homelab",
        "name": "Homelab Fleet",
        "description": "Enterprise homelab infrastructure and hypervisor management fleet.",
        "lead_agent_id": "homelab",
        "shared_skills": [
            "lookup-network-spec",
            "lookup-host-spec",
            "manage-opentofu-hyperv",
        ],
        "agent_ids": [
            "homelab",
            "homelab-architect",
            "homelab-engineer",
            "homelab-admin",
            "homelab-janitor",
        ],
    }
    manifest = FleetManifest.model_validate(data)
    assert manifest.id == "homelab"
    assert manifest.lead_agent_id == "homelab"
    assert len(manifest.shared_skills) == 3
    assert len(manifest.agent_ids) == 5


def test_platform_skill_tools_strict_core_only():
    """Verify PLATFORM_SKILL_TOOLS only contains AutoReiv platform core, not domain fleet tools [REQ-FLEET-011]."""
    # Core platform skills MUST be present
    assert "wiki" in PLATFORM_SKILL_TOOLS
    assert "coordination" in PLATFORM_SKILL_TOOLS
    assert "proposals" in PLATFORM_SKILL_TOOLS
    assert "worker" in PLATFORM_SKILL_TOOLS
    assert "planning" in PLATFORM_SKILL_TOOLS
    assert "verification" in PLATFORM_SKILL_TOOLS
    assert "sandbox" in PLATFORM_SKILL_TOOLS

    # Homelab domain tools MUST NOT be in PLATFORM_SKILL_TOOLS
    assert "lookup-network-spec" not in PLATFORM_SKILL_TOOLS
    assert "lookup-host-spec" not in PLATFORM_SKILL_TOOLS
    assert "manage-opentofu-hyperv" not in PLATFORM_SKILL_TOOLS
    assert "infrastructure" not in PLATFORM_SKILL_TOOLS


def test_homelab_consolidated_suite_structure():
    """Verify platform-packs/homelab is structured as a consolidated suite [REQ-FLEET-012]."""
    repo_root = Path(__file__).resolve().parents[3]
    homelab_dir = repo_root / "platform-packs" / "homelab"
    assert homelab_dir.is_dir()

    # 1. fleet.json exists and validates
    fleet_json_path = homelab_dir / "fleet.json"
    assert fleet_json_path.is_file(), "Missing fleet.json in platform-packs/homelab"
    fleet_data = json.loads(fleet_json_path.read_text(encoding="utf-8"))
    manifest = FleetManifest.model_validate(fleet_data)
    assert manifest.id == "homelab"

    # 2. shared_skills/ directory exists and contains the 3 shared skills
    shared_skills_dir = homelab_dir / "shared_skills"
    assert shared_skills_dir.is_dir(), "Missing shared_skills/ in platform-packs/homelab"
    for skill_name in manifest.shared_skills:
        skill_file = shared_skills_dir / skill_name / "SKILL.md"
        assert skill_file.is_file(), f"Missing shared skill runbook: {skill_file}"

    # 3. agents/ directory contains all 5 member agent pack.json files
    agents_dir = homelab_dir / "agents"
    assert agents_dir.is_dir(), "Missing agents/ in platform-packs/homelab"
    for agent_id in manifest.agent_ids:
        agent_pack_json = agents_dir / agent_id / "pack.json"
        assert agent_pack_json.is_file(), f"Missing agent pack.json for {agent_id}"
        agent_data = json.loads(agent_pack_json.read_text(encoding="utf-8"))
        assert agent_data.get("id") == agent_id
        assert agent_data.get("fleet") == "homelab"

        # homelab-architect must NOT claim id: "wiki" in its private skills array [REQ-FLEET-010]
        if agent_id == "homelab-architect":
            skill_ids = [s.get("id") if isinstance(s, dict) else s for s in agent_data.get("skills", [])]
            assert "wiki" not in skill_ids, "homelab-architect must not declare id: 'wiki' in skills list"


def test_legacy_loose_homelab_folders_removed():
    """Verify loose homelab specialist folders at platform-packs/ root are removed in favor of agents/ [REQ-FLEET-012]."""
    repo_root = Path(__file__).resolve().parents[3]
    platform_packs = repo_root / "platform-packs"
    assert not (platform_packs / "homelab-architect").exists(), "Legacy folder homelab-architect should be moved under homelab/agents/"
    assert not (platform_packs / "homelab-engineer").exists(), "Legacy folder homelab-engineer should be moved under homelab/agents/"
    assert not (platform_packs / "homelab-admin").exists(), "Legacy folder homelab-admin should be moved under homelab/agents/"
    assert not (platform_packs / "homelab-janitor").exists(), "Legacy folder homelab-janitor should be moved under homelab/agents/"


@pytest.mark.asyncio
async def test_skills_catalog_exposes_fleet_skills_and_wiki(tmp_path, monkeypatch):
    """Verify GET /api/skills/catalog restores wiki and isolates fleet_skills [REQ-FLEET-010, REQ-FLEET-011]."""
    from httpx import ASGITransport, AsyncClient

    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    store = SQLiteStateStore(db_path=str(tmp_path / "api.db"))
    app = create_app(state_store=store)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/skills/catalog")
        assert res.status_code == 200
        data = res.json()

        # 1. Wiki must be present in platform_skills [REQ-FLEET-010]
        platform_skill_ids = [s["id"] for s in data.get("platform_skills", [])]
        assert "wiki" in platform_skill_ids, "wiki must be in platform_skills"

        # 2. Homelab skills must NOT be in platform_skills [REQ-FLEET-011]
        assert "lookup-network-spec" not in platform_skill_ids
        assert "lookup-host-spec" not in platform_skill_ids
        assert "manage-opentofu-hyperv" not in platform_skill_ids

        # 3. fleet_skills must contain homelab shared skills [REQ-FLEET-013]
        fleet_skills = data.get("fleet_skills", {})
        assert "homelab" in fleet_skills
        homelab_skill_ids = [s["id"] for s in fleet_skills["homelab"]]
        assert "lookup-network-spec" in homelab_skill_ids
        assert "lookup-host-spec" in homelab_skill_ids
        assert "manage-opentofu-hyperv" in homelab_skill_ids


def test_agent_pack_service_imports_fleet_suite(tmp_path):
    """Verify AgentPackService.import_path imports a fleet suite and registers all member agents [REQ-FLEET-015]."""
    from src.application.agent_packs.service import AgentPackService
    from src.infrastructure.agents.registry import BuiltinAgentRegistry

    repo_root = Path(__file__).resolve().parents[3]
    homelab_suite = repo_root / "platform-packs" / "homelab"

    registry = BuiltinAgentRegistry()
    service = AgentPackService(data_dir=tmp_path, agent_registry=registry)

    lead_profile = service.import_path(homelab_suite)
    assert lead_profile.id == "homelab"
    assert lead_profile.fleet == "homelab"

    # All 5 specialists must be registered in the agent registry
    assert registry.get_agent("homelab") is not None
    assert registry.get_agent("homelab-architect") is not None
    assert registry.get_agent("homelab-engineer") is not None
    assert registry.get_agent("homelab-admin") is not None
    assert registry.get_agent("homelab-janitor") is not None

