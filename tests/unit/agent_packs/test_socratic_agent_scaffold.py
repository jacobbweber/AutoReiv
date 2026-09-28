"""
Unit tests for Socratic Agent Discovery and Scaffold Contracts [REQ-FACT-046, REQ-FACT-048].
"""

from pathlib import Path


def test_seed_build_agent_pack_matches_platform_pack():
    platform_path = Path("platform-packs/autoreiv/skills/build-agent-pack/SKILL.md")
    seed_path = Path("src/infrastructure/skills/seeds/build-agent-pack/SKILL.md")
    assert seed_path.exists(), "build-agent-pack seed must exist"
    assert platform_path.read_text(encoding="utf-8") == seed_path.read_text(encoding="utf-8")

