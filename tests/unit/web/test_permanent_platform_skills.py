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

    # All core platform skill primitives must ALWAYS be present in Platform Skills & Tools
    expected_platform_skills = {
        "wiki_tasks",
        "wiki-knowledge",
        "wiki-inbox",
        "wiki-curation",
        "coordination",
        "proposals",
        "worker",
        "sandbox",
        "sqlite-storage",
    }
    # CARD-570: the catalog lists every shipped skill (platform/skills); the core primitives are always there.
    assert expected_platform_skills <= returned_ids, f"missing: {expected_platform_skills - returned_ids}"


def test_coordination_skill_contains_core_handoff_tools():
    """Verify that Agent Coordination platform skill includes core handoff tools and prunes legacy fleet tool [CARD-201, CARD-376]."""
    client = TestClient(app)
    res = client.get("/api/skills/catalog")
    assert res.status_code == 200
    data = res.json()
    platform_skills = {s["id"]: s for s in data.get("platform_skills", [])}
    coordination = platform_skills.get("coordination")
    assert coordination is not None, "Coordination platform skill missing"
    tool_names = {t["name"] for t in coordination.get("tools", [])}
    assert "lookup_agents" in tool_names
    assert "handoff_to_agent" in tool_names
    assert "propose_followup" in tool_names
    assert "delegate_to_fleet_agent" not in tool_names



