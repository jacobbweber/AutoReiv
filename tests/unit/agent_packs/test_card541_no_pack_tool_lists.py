"""CARD-541 guard: packs carry no flat tool lists; tools come only from the nested skills (ADR-0061)."""

from __future__ import annotations

import json
from pathlib import Path

from src.application.agent_packs.schema import LEGACY_TOOL_LIST_KEYS, AgentPackManifest
from src.infrastructure.skills.platform_packs import refresh_live_pack_json_skill_projection, seed_pack_tools

PACKS = sorted(Path("platform-packs").glob("*/pack.json"))


def test_shipped_platform_packs_have_no_tool_lists():
    assert PACKS
    for path in PACKS:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert not set(LEGACY_TOOL_LIST_KEYS) & set(data), path


def test_the_manifest_has_no_tool_list_fields_and_never_writes_one():
    assert not set(LEGACY_TOOL_LIST_KEYS) & set(AgentPackManifest.model_fields)
    m = AgentPackManifest.model_validate(
        {"id": "a", "name": "A", "skills": [{"id": "s", "tools": ["t1"]}], "pack_tool_names": ["t1", "t2"],
         "allowed_tool_names": ["t3"]}
    )
    assert m.pack_tool_names == ["t1"]
    assert m.ignored_tool_lists == ["pack_tool_names", "allowed_tool_names"]
    assert not set(LEGACY_TOOL_LIST_KEYS) & set(m.model_dump(mode="json"))


def test_seed_tools_come_from_the_nested_skills():
    data = json.loads(Path("platform-packs/tutor/pack.json").read_text(encoding="utf-8"))
    tools = seed_pack_tools(data)
    assert "education_quiz_next" in tools and len(tools) == len(set(tools))


def test_live_pack_json_loses_a_stale_tool_list_on_refresh(tmp_path):
    (tmp_path / "pack.json").write_text(json.dumps({"id": "x", "skills": [], "pack_tool_names": ["old"]}), encoding="utf-8")
    assert refresh_live_pack_json_skill_projection(tmp_path, {"id": "x", "skills": []}) is True
    assert "pack_tool_names" not in json.loads((tmp_path / "pack.json").read_text(encoding="utf-8"))
