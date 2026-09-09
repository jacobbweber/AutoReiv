"""
Unit tests for Socratic Agent Discovery and Scaffold Contracts [REQ-FACT-046, REQ-FACT-048].
"""

from pathlib import Path

from src.domain.agents.profiles import AGENT_BUILDER_PROFILE


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


def test_agent_builder_profile_instructs_socratic_discovery():
    prompt = AGENT_BUILDER_PROFILE.system_prompt
    assert "Socratic" in prompt or "clarifying questions" in prompt
    assert "[IDENTITY & ROLE]" in prompt or "boundary" in prompt.lower()
