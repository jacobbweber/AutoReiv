"""CARD-429 / CARD-725 operator contract: agent-builder and developer are gone; AutoReiv owns builder tools.

REQ-429-007: get_agent('agent-builder') and retired coding agents are absent from the roster and GET /api/agents.
REQ-429-008: AutoReiv can use propose/commit/write_skill_file tools via capability-authoring. save_agent_specification is not allowlisted.
REQ-429-009: (CARD-636) skill-eval-sleep and skill-curator are retired; skill eval runs in the nightly auditor.
REQ-429-003: shipped capabilities in /api/capabilities/tree include capability-authoring and its tools.

Temp user-data only [ADR-0055, ADR-0066].
"""

from __future__ import annotations

import os
from pathlib import Path

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.infrastructure.content.store import REPO_PLATFORM


def _refuse_live(user_data: Path) -> None:
    local_app = os.environ.get("LOCALAPPDATA") or ""
    if not local_app:
        return
    live_root = (Path(local_app) / "AutoReiv").resolve()
    ud = str(user_data.resolve()).replace("\\", "/").lower()
    live = str(live_root).replace("\\", "/").lower()
    assert ud != live and not ud.startswith(live + "/"), f"operator contracts must not use live user-data: {user_data}"


def test_oc429_developer_owns_builder_tools_and_agent_builder_is_absent(operator_client):
    client, store, wiki = operator_client
    _refuse_live(wiki.parent)
    registry = client.app.state.registry

    listed = client.get("/api/agents")
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json()}
    for retired_id in ("agent-builder", "developer", "toolsmith", "architect"):
        assert retired_id not in ids
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

    autoreiv = registry.get_agent("autoreiv")
    assert autoreiv is not None
    names = set(resolve_allowed_tools(autoreiv))
    for tool in (
        "propose_skill",
        "propose_tool",
        "commit_skill",
        "list_available_skills_and_tools",
        "write_skill_file",
    ):
        assert tool in names, tool
    assert "save_agent_specification" not in names
    assert "capability-authoring" in (autoreiv.allowed_skill or [])
    assert (REPO_PLATFORM / "skills" / "capability-authoring" / "SKILL.md").is_file()

    routines = {row["id"]: row for row in client.get("/api/routines").json()}
    assert "skill-eval-sleep" not in routines
    assert "skill-curator" not in routines

    tree_res = client.get("/api/capabilities/tree?agent_id=autoreiv")
    assert tree_res.status_code == 200
    tree = tree_res.json()
    skills_by_id = {s["id"]: s for s in tree.get("skills") or []}
    assert "capability-authoring" in skills_by_id
    cap_skill = skills_by_id["capability-authoring"]
    assert cap_skill.get("source") == "shipped"
    cap_tools = set(cap_skill.get("declared_tools") or [])
    assert "propose_skill" in cap_tools
    assert "write_skill_file" in cap_tools

    visible = client.app.state.kernel._resolve_active_tools(
        autoreiv,
        "propose a skill for backups",
    )
    visible_names = {tool.name for tool in visible}
    assert "propose_skill" in visible_names
    assert "write_skill_file" in visible_names
    assert "save_agent_specification" not in visible_names

    tutor = registry.get_agent("tutor")
    assert tutor is not None
    tutor_tools = client.app.state.kernel._resolve_active_tools(
        tutor,
        "propose a skill for backups",
    )
    tutor_names = {tool.name for tool in tutor_tools}
    assert "propose_skill" not in tutor_names
    assert "skill_view" in tutor_names
