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

    # All 7 platform skill primitives must ALWAYS be present in Platform Skills & Tools
    expected_platform_skills = {
        "wiki",
        "coordination",
        "proposals",
        "worker",
        "planning",
        "verification",
        "sandbox",
    }
    assert expected_platform_skills.issubset(returned_ids), f"Missing platform skills: {expected_platform_skills - returned_ids}"


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
