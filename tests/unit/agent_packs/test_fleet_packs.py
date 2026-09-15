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
    assert "sandbox" in PLATFORM_SKILL_TOOLS
    assert "planning" not in PLATFORM_SKILL_TOOLS
    assert "verification" not in PLATFORM_SKILL_TOOLS

    # Homelab domain tools MUST NOT be in PLATFORM_SKILL_TOOLS
    assert "lookup-network-spec" not in PLATFORM_SKILL_TOOLS
    assert "lookup-host-spec" not in PLATFORM_SKILL_TOOLS
    assert "manage-opentofu-hyperv" not in PLATFORM_SKILL_TOOLS
    assert "infrastructure" not in PLATFORM_SKILL_TOOLS


def test_homelab_not_shipped_as_platform_packs():
    """CARD-294: homelab* are user-data packs — not under platform-packs/ seed set."""
    from src.infrastructure.skills.platform_packs import ALL_PLATFORM_PACK_IDS, PLATFORM_PACK_IDS

    repo_root = Path(__file__).resolve().parents[3]
    platform_packs = repo_root / "platform-packs"
    assert PLATFORM_PACK_IDS == ("assistant", "autoreiv", "developer", "wiki")
    assert ALL_PLATFORM_PACK_IDS == PLATFORM_PACK_IDS
    for agent_id in ("homelab", "homelab-architect", "homelab-engineer", "homelab-admin", "homelab-janitor"):
        assert agent_id not in ALL_PLATFORM_PACK_IDS
        assert not (platform_packs / agent_id).exists(), f"{agent_id} must not ship as platform pack"


@pytest.mark.asyncio
async def test_skills_catalog_exposes_fleet_skills_and_wiki(tmp_path, monkeypatch):
    """Verify GET /api/skills/catalog restores wiki and returns all platform skills [CARD-201, REQ-FLEET-010]."""
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

        # 1. Wiki must be present in platform_skills [REQ-FLEET-010, CARD-201]
        platform_skill_ids = [s["id"] for s in data.get("platform_skills", [])]
        assert "wiki" in platform_skill_ids, "wiki must be in platform_skills"
        assert "coordination" in platform_skill_ids, "coordination must be in platform_skills"

        # 2. Homelab skills must NOT be in platform_skills
        assert "lookup-network-spec" not in platform_skill_ids
        assert "lookup-host-spec" not in platform_skill_ids
        assert "manage-opentofu-hyperv" not in platform_skill_ids


def test_agent_pack_service_imports_fleet_suite(tmp_path):
    """Verify AgentPackService.import_path imports a fleet suite if fleet.json is provided [REQ-FLEET-015]."""
    from src.application.agent_packs.service import AgentPackService
    from src.infrastructure.agents.registry import BuiltinAgentRegistry

    # Create synthetic fleet suite in tmp_path
    suite_dir = tmp_path / "test-fleet"
    suite_dir.mkdir(parents=True)
    fleet_json = {
        "schema_version": "1.0",
        "id": "test-fleet",
        "name": "Test Fleet",
        "description": "Test fleet suite.",
        "lead_agent_id": "test-lead",
        "shared_skills": [],
        "agent_ids": ["test-lead", "test-worker"],
    }
    (suite_dir / "fleet.json").write_text(json.dumps(fleet_json), encoding="utf-8")

    agents_dir = suite_dir / "agents"
    agents_dir.mkdir()
    for aid in ("test-lead", "test-worker"):
        a_dir = agents_dir / aid
        a_dir.mkdir()
        (a_dir / "pack.json").write_text(
            json.dumps({
                "schema_version": "1.1",
                "id": aid,
                "name": aid.title(),
                "description": f"Test agent {aid}",
                "system_prompt": f"You are {aid}.",
                "fleet": "test-fleet",
            }),
            encoding="utf-8",
        )

    registry = BuiltinAgentRegistry()
    service = AgentPackService(data_dir=tmp_path / "data", agent_registry=registry)

    lead_profile = service.import_path(suite_dir)
    assert lead_profile.id == "test-lead"
    assert lead_profile.fleet == "test-fleet"

    # Both specialists must be registered in the agent registry
    assert registry.get_agent("test-lead") is not None
    assert registry.get_agent("test-worker") is not None

def test_developer_build_skill_is_tracked():
    """CARD-294: skills/build must ship; /build/ gitignore must not hide it."""
    import subprocess
    from pathlib import Path

    skill = Path("platform-packs/developer/skills/build/SKILL.md")
    assert skill.is_file(), "developer build skill missing from seed"
    tracked = subprocess.check_output(
        ["git", "ls-files", "--", str(skill).replace("\\", "/")],
        text=True,
    ).strip()
    assert tracked.endswith("SKILL.md"), f"build skill not tracked: {tracked!r}"
    # exit 1 from check-ignore means NOT ignored
    proc = subprocess.run(
        ["git", "check-ignore", "-v", str(skill).replace("\\", "/")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1, f"build skill is ignored: {proc.stdout or proc.stderr}"


def test_sqlite_default_db_is_under_user_data(monkeypatch, tmp_path):
    """CARD-294: default SQLite path is user data database/, not checkout ./data/."""
    monkeypatch.delenv("AUTOREIV_DB_PATH", raising=False)
    monkeypatch.delenv("AUTOREIV_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from src.infrastructure.memory.connection import SQLiteConnectionManager

    mgr = SQLiteConnectionManager()
    assert "database" in mgr.db_path.replace("\\", "/")
    assert "./data/" not in mgr.db_path.replace("\\", "/")
    assert str(tmp_path) in mgr.db_path or "AutoReiv" in mgr.db_path

