"""
Unit tests for Socratic Agent Discovery and Scaffold Contracts [REQ-FACT-046, REQ-FACT-048].
"""

from pathlib import Path


def test_build_agent_pack_skill_contains_socratic_discovery_and_blueprint():
    skill_path = Path("platform-packs/autoreiv/skills/build-agent-pack/SKILL.md")
    assert skill_path.exists(), "build-agent-pack SKILL.md must exist in platform-packs"
    content = skill_path.read_text(encoding="utf-8")

    # Verify Socratic discovery questions
    assert "Socratic Discovery" in content
    assert "Core Specialization" in content
    assert "Environment & Execution" in content
    assert "Safety & Guardrails" in content
    assert "Initial Tool Needs" in content

    # Verify 6-section blueprint
    assert "[IDENTITY & ROLE]" in content
    assert "[DOMAIN BOUNDARIES & REFUSALS]" in content
    assert "[EXECUTION PROTOCOL]" in content
    assert "[SAFETY & APPROVALS]" in content
    assert "[TOOL USAGE RULES]" in content
    assert "[OUTPUT FORMAT]" in content


def test_seed_build_agent_pack_matches_platform_pack():
    platform_path = Path("platform-packs/autoreiv/skills/build-agent-pack/SKILL.md")
    seed_path = Path("src/infrastructure/skills/seeds/build-agent-pack/SKILL.md")
    assert seed_path.exists(), "build-agent-pack seed must exist"
    assert platform_path.read_text(encoding="utf-8") == seed_path.read_text(encoding="utf-8")


def test_developer_capability_skill_documents_scaffold_not_legacy_save():
    skill_path = Path("platform-packs/developer/skills/capability-authoring/SKILL.md")
    content = skill_path.read_text(encoding="utf-8")
    assert "scaffold_agent_pack" in content
    assert "save_agent_specification" in content
    assert "not" in content.lower() and "allowlist" in content
    assert "propose_skill" in content
    assert "commit_skill_pack" in content
