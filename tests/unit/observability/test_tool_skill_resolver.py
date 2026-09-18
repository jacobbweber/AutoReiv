"""
Unit tests for Tool-to-Skill Resolver & Runbook Patch Synthesizer [CARD-354 / REQ-OBS-011].
"""

from pathlib import Path

import pytest

from src.domain.observability.models import (
    FrictionIncident,
    FrictionSignatureType,
    RunbookRecommendation,
)
from src.domain.observability.tool_skill_resolver import ToolSkillResolver


@pytest.fixture
def temp_data_dir(tmp_path: Path):
    data_dir = tmp_path / "user_data"
    data_dir.mkdir()
    # Create platform skills in user data
    skills_dir = data_dir / "skills"
    skills_dir.mkdir()
    wiki_dir = skills_dir / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "SKILL.md").write_text(
        "---\nname: wiki\ndescription: Wiki notes\ntools:\n  - wiki_note_read\n  - wiki_note_create\n  - list_wiki_templates\n---\n# Wiki SOP\n\n## Procedure\nCreate notes.\n\n## Common Pitfalls & Forbidden Paths\n- Do not use absolute paths.\n",
        encoding="utf-8",
    )
    return data_dir


def test_resolve_builtin_platform_tools(temp_data_dir: Path):
    resolver = ToolSkillResolver(data_dir=temp_data_dir)
    res = resolver.resolve_tool_to_skill(agent_id="autoreiv", tool_name="list_wiki_templates")
    assert res is not None
    skill_id, skill_rel_path = res
    assert skill_id == "wiki"
    assert "wiki/SKILL.md" in skill_rel_path.replace("\\", "/")


def test_resolve_custom_pack_skill(temp_data_dir: Path):
    pack_dir = temp_data_dir / "packs" / "git-agent" / "skills" / "git-ops"
    pack_dir.mkdir(parents=True)
    (pack_dir / "SKILL.md").write_text(
        "---\nname: git-ops\ndescription: Git actions\ntools:\n  - git_status\n  - git_commit\n---\n# Git SOP\n\n## Common Pitfalls & Forbidden Paths\n- Never force push.\n",
        encoding="utf-8",
    )

    resolver = ToolSkillResolver(data_dir=temp_data_dir)
    res = resolver.resolve_tool_to_skill(agent_id="git-agent", tool_name="git_status")
    assert res is not None
    skill_id, skill_rel_path = res
    assert skill_id == "git-ops"
    assert "packs/git-agent/skills/git-ops/SKILL.md" in skill_rel_path.replace("\\", "/")


def test_synthesize_recommendation_redundant_verification(temp_data_dir: Path):
    resolver = ToolSkillResolver(data_dir=temp_data_dir)
    incident = FrictionIncident(
        id="fric_123",
        session_id="sess_1",
        agent_id="autoreiv",
        tool_name="list_wiki_templates",
        signature=FrictionSignatureType.REDUNDANT_VERIFICATION,
        evidence="Redundant verification: list_wiki_templates executed immediately after wiki_template_create.",
        severity="medium",
    )

    rec = resolver.synthesize_recommendation(incident)
    assert rec is not None
    assert rec.remedy_kind == "runbook_patch"
    assert rec.skill_id == "wiki"
    assert "list_wiki_templates" in rec.proposed_patch
    assert "Common Pitfalls" in rec.proposed_patch or "Forbidden" in rec.proposed_patch or "Do not" in rec.proposed_patch


def test_synthesize_recommendation_payload_bloat_with_limit(temp_data_dir: Path):
    resolver = ToolSkillResolver(data_dir=temp_data_dir)
    # Tool known to support pagination / limit
    incident = FrictionIncident(
        id="fric_456",
        session_id="sess_2",
        agent_id="autoreiv",
        tool_name="wiki_note_search",
        signature=FrictionSignatureType.PAYLOAD_BLOAT,
        evidence="Tool wiki_note_search returned 14000 bytes.",
        payload_bytes=14000,
        severity="medium",
    )

    rec = resolver.synthesize_recommendation(incident)
    assert rec is not None
    assert rec.remedy_kind == "runbook_patch"
    assert "limit" in rec.proposed_patch.lower() or "pagination" in rec.proposed_patch.lower()


def test_synthesize_recommendation_payload_bloat_factory_escalation(temp_data_dir: Path):
    resolver = ToolSkillResolver(data_dir=temp_data_dir)
    # Unknown/native tool that has no pagination
    incident = FrictionIncident(
        id="fric_789",
        session_id="sess_3",
        agent_id="autoreiv",
        tool_name="raw_hardware_dump",
        signature=FrictionSignatureType.PAYLOAD_BLOAT,
        evidence="Tool raw_hardware_dump returned 25000 bytes.",
        payload_bytes=25000,
        severity="high",
    )

    rec = resolver.synthesize_recommendation(incident)
    assert rec is not None
    assert rec.remedy_kind == "factory_escalation"
    assert "Factory" in rec.summary or "Factory" in rec.proposed_patch


def test_apply_recommendation_to_user_data_skill(temp_data_dir: Path):
    resolver = ToolSkillResolver(data_dir=temp_data_dir)
    skill_file = temp_data_dir / "skills" / "wiki" / "SKILL.md"

    rec = RunbookRecommendation(
        id="rec_999",
        agent_id="autoreiv",
        skill_id="wiki",
        skill_path="skills/wiki/SKILL.md",
        friction_type=FrictionSignatureType.REDUNDANT_VERIFICATION,
        summary="Prevent redundant template verification.",
        proposed_patch="- Do not invoke list_wiki_templates immediately after wiki_template_create.",
        remedy_kind="runbook_patch",
        status="pending",
    )

    success = resolver.apply_recommendation(rec)
    assert success is True

    updated_content = skill_file.read_text(encoding="utf-8")
    assert "- Do not invoke list_wiki_templates immediately after wiki_template_create." in updated_content
    # Frontmatter must be preserved
    assert "name: wiki" in updated_content
    assert "## Procedure" in updated_content


def test_resolve_pack_json_skills_mapping(temp_data_dir: Path):
    dev_dir = temp_data_dir / "packs" / "developer"
    skills_dir = dev_dir / "skills" / "build"
    skills_dir.mkdir(parents=True)
    (dev_dir / "pack.json").write_text(
        '{"id": "developer", "skills": [{"id": "build", "name": "Build", "tools": ["write_project_file"]}]}',
        encoding="utf-8",
    )
    (skills_dir / "SKILL.md").write_text(
        "---\nname: Build\ndescription: Build stuff\n---\n# Build SOP\n\n## Pitfalls\n- Existing pitfall.\n",
        encoding="utf-8",
    )

    resolver = ToolSkillResolver(data_dir=temp_data_dir)
    res = resolver.resolve_tool_to_skill(agent_id="developer", tool_name="write_project_file")
    assert res is not None
    skill_id, rel_path = res
    assert skill_id == "build"
    assert rel_path.replace("\\", "/") == "packs/developer/skills/build/SKILL.md"


def test_apply_recommendation_to_pitfalls_heading(temp_data_dir: Path):
    dev_dir = temp_data_dir / "packs" / "developer" / "skills" / "build"
    dev_dir.mkdir(parents=True, exist_ok=True)
    skill_file = dev_dir / "SKILL.md"
    skill_file.write_text(
        "---\nname: Build\n---\n# Build\n\n## Pitfalls\n\n- Existing pitfall.\n",
        encoding="utf-8",
    )

    resolver = ToolSkillResolver(data_dir=temp_data_dir)
    rec = RunbookRecommendation(
        id="rec_pitfall",
        agent_id="developer",
        skill_id="build",
        skill_path="packs/developer/skills/build/SKILL.md",
        friction_type=FrictionSignatureType.REDUNDANT_VERIFICATION,
        summary="Prevent redundant read after write.",
        proposed_patch="- Do not invoke read_project_file immediately after write_project_file.",
        remedy_kind="runbook_patch",
        status="pending",
    )

    success = resolver.apply_recommendation(rec)
    assert success is True

    text = skill_file.read_text(encoding="utf-8")
    assert "- Do not invoke read_project_file immediately after write_project_file." in text
    assert "- Existing pitfall." in text

    # Idempotent re-apply
    assert resolver.apply_recommendation(rec) is True
    # Count occurrences of proposed_patch
    assert text.count(rec.proposed_patch) == 1
