from fastapi.testclient import TestClient

from src.web.app import app


def test_platform_skills_permanence_in_catalog():
    """Verify that all PLATFORM_SKILL_IDS are permanently returned in /api/skills/catalog [CARD-201, REQ-SKILL-022]."""
    client = TestClient(app)
    res = client.get("/api/skills/catalog")
    assert res.status_code == 200
    data = res.json()
    platform_skills = data.get("platform_skills", [])
    returned_ids = {s["id"] for s in platform_skills}

    # All 7 platform skill primitives must ALWAYS be present in Platform Skills & Tools and ONLY those 7
    expected_platform_skills = {
        "wiki",
        "coordination",
        "proposals",
        "worker",
        "planning",
        "verification",
        "sandbox",
    }
    assert returned_ids == expected_platform_skills, f"Platform skills mismatch: {returned_ids ^ expected_platform_skills}"


def test_coordination_skill_contains_fleet_delegation_tool():
    """Verify that Agent Coordination platform skill includes delegate_to_fleet_agent [CARD-201]."""
    client = TestClient(app)
    res = client.get("/api/skills/catalog")
    assert res.status_code == 200
    data = res.json()
    platform_skills = {s["id"]: s for s in data.get("platform_skills", [])}
    coordination = platform_skills.get("coordination")
    assert coordination is not None, "Coordination platform skill missing"
    tool_names = {t["name"] for t in coordination.get("tools", [])}
    assert "delegate_to_fleet_agent" in tool_names
    assert "lookup_agents" in tool_names
    assert "handoff_to_agent" in tool_names


def test_pack_skills_payload_excludes_platform_skills():
    """Verify that _pack_skills_payload never returns platform skills in Box 2 [CARD-201]."""
    from src.application.agent_packs.schema import AgentPackManifest, PackSkill
    from src.web.routers.agents import _pack_skills_payload

    manifest = AgentPackManifest(
        schema_version="2.0.0",
        id="test-agent",
        name="Test Agent",
        description="Test description",
        skills=[
            PackSkill(id="wiki", tools=[]),
            PackSkill(id="coordination", tools=[]),
            PackSkill(id="custom-domain-skill", tools=["custom_tool"]),
        ],
        allowed_skill=["wiki", "coordination", "custom-domain-skill"],
    )
    payload = _pack_skills_payload(manifest)
    returned_skill_ids = [s["id"] for s in payload.get("pack_skills", [])]
    assert "wiki" not in returned_skill_ids
    assert "coordination" not in returned_skill_ids
    assert returned_skill_ids == ["custom-domain-skill"]

