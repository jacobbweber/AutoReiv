"""CARD-429 operator contract: agent-builder is gone; Developer owns builder tools.

REQ-429-007: get_agent('agent-builder') is absent from the roster and from GET /api/agents.
REQ-429-008: Developer can use propose/commit/scaffold tools. save_agent_specification is not allowlisted.
REQ-429-009: skill-eval-sleep and skill-curator point at developer and stay paused.
REQ-429-003: shipped capability groups are labeled Platform.

Temp user-data only [ADR-0055].
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.application.agent_skills.allowed_tools import resolve_allowed_tools


def _refuse_live(user_data: Path) -> None:
    local_app = os.environ.get("LOCALAPPDATA") or ""
    if not local_app:
        return
    live_root = (Path(local_app) / "AutoReiv").resolve()
    ud = str(user_data.resolve()).replace("\\", "/").lower()
    live = str(live_root).replace("\\", "/").lower()
    assert ud != live and not ud.startswith(live + "/"), f"operator contracts must not use live user-data: {user_data}"


@pytest.mark.skip(reason="Capability authoring / MCP building is on no agent (CARD-571 Toolsmith builds native tools only)")
def test_oc429_developer_owns_builder_tools_and_agent_builder_is_absent(operator_client):
    client, store, wiki = operator_client
    _refuse_live(wiki.parent)
    registry = client.app.state.registry

    listed = client.get("/api/agents")
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json()}
    assert "agent-builder" not in ids
    assert registry.get_agent("agent-builder") is None
    missing = client.get("/api/agents/agent-builder")
    assert missing.status_code == 404
    rejected = client.post(
        "/api/agents",
        json={
            "id": "agent-builder",
            "name": "Agent Builder",
            "description": "must not return",
            "system_prompt": "This must not become a live agent again.",
        },
    )
    assert rejected.status_code == 422

    developer = registry.get_agent("developer")
    assert developer is not None
    names = set(resolve_allowed_tools(developer))
    for tool in (
        "propose_skill",
        "propose_tool",
        "commit_skill",
        "list_available_skills_and_tools",
    ):
        assert tool in names, tool
    assert "save_agent_specification" not in names
    assert "capability-authoring" in (developer.allowed_skill or [])
    assert (wiki.parent / "packs" / "developer" / "skills" / "capability-authoring" / "SKILL.md").is_file()

    routines = {row["id"]: row for row in client.get("/api/routines").json()}
    assert routines["skill-eval-sleep"]["agent_id"] == "developer"
    assert routines["skill-eval-sleep"]["enabled"] is False
    assert routines["skill-curator"]["agent_id"] == "developer"
    assert routines["skill-curator"]["enabled"] is False

    caps = client.get("/api/tools_studio/capabilities").json()
    group_names = [ns["name"] for ns in caps["namespaces"]]
    assert "Built-in Primitives" not in group_names
    assert not any(str(name).startswith("Dynamic:") for name in group_names)
    platform = next(ns for ns in caps["namespaces"] if ns["id"] == "platform")
    assert platform["name"] == "Platform"
    assert platform["origin_label"] == "Platform"
    assert any(tool["name"] == "propose_skill" for tool in platform["tools"])

    visible = client.app.state.kernel._resolve_active_tools(
        developer,
        "propose a skill for backups",
    )
    visible_names = {tool.name for tool in visible}
    assert "propose_skill" in visible_names
    coding = client.app.state.kernel._resolve_active_tools(
        developer,
        "fix the pytest in src/foo.py",
    )
    coding_names = {tool.name for tool in coding}
    assert "propose_skill" not in coding_names
    code_tools = {"execute_code", "write_project_file", "cli_exec", "read_project_file"}
    code_tools |= {"patch_project_file", "run_project_checks", "search_project"}  # CARD-562
    assert coding_names & code_tools




