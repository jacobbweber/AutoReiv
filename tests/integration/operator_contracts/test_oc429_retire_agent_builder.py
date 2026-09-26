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

from src.domain.kernel.models import AgentProfile
from src.domain.routines.manifests import SKILL_EVAL_SLEEP_ROUTINE
from src.domain.settings.models import AgentCustomization
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.platform_packs import install_platform_agent_packs


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
    names = set(developer.allowed_tool_names or [])
    for tool in (
        "propose_skill",
        "propose_tool",
        "commit_skill_pack",
        "list_available_skills_and_tools",
        "scaffold_agent_pack",
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
    assert coding_names & {"execute_code", "write_project_file", "cli_exec", "read_project_file"}


def test_oc429_boot_purges_leftover_agent_builder_row(tmp_path, monkeypatch):
    """Old profile rows are deleted. Session and job id rewrite is CARD-432."""
    from src.web.app import create_app

    user_data = (tmp_path / "user-data").resolve()
    wiki = user_data / "wiki"
    db = user_data / "autoreiv.db"
    user_data.mkdir(parents=True, exist_ok=True)
    wiki.mkdir(parents=True, exist_ok=True)
    _refuse_live(user_data)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(user_data))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki))
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "local")

    store = SQLiteStateStore(db_path=str(db))
    store.initialize_db()
    store.save_agent_profile(
        AgentProfile(
            id="agent-builder",
            name="Agent Builder",
            description="Leftover hidden builtin row.",
            system_prompt="You are a retired hidden builtin that must not boot.",
            is_builtin=True,
            show_in_chat=False,
        )
    )
    stale = SKILL_EVAL_SLEEP_ROUTINE.model_copy(update={"agent_id": "agent-builder", "enabled": False})
    store.save_routine(stale)
    assert store.get_agent_profile("agent-builder") is not None

    app = create_app(state_store=store, wiki_path=str(wiki))
    assert app.state.registry.get_agent("agent-builder") is None
    assert store.get_agent_profile("agent-builder") is None
    routine = store.get_routine("skill-eval-sleep")
    assert routine is not None
    assert routine.agent_id == "developer"
    assert routine.enabled is False

    # A row inserted after boot is still not a live agent, and the next purge removes it.
    store.save_agent_profile(
        AgentProfile(
            id="agent-builder",
            name="Agent Builder",
            description="Inserted after boot.",
            system_prompt="You are a retired hidden builtin that must not boot.",
            is_builtin=True,
        )
    )
    assert app.state.registry.get_agent("agent-builder") is None
    store.retire_agent_builder_rows()
    assert store.get_agent_profile("agent-builder") is None


def test_oc429_user_modified_developer_gains_authoring_without_prompt_rewrite(operator_client):
    client, store, wiki = operator_client
    registry = client.app.state.registry
    tools = client.app.state.tool_registry
    developer = registry.get_agent("developer")
    assert developer is not None
    prompt = f"OPERATOR PROMPT CARD-429\n{developer.system_prompt}"
    skills = [
        sid
        for sid in (developer.allowed_skill or [])
        if sid not in {"capability-authoring", "proposals", "build-agent-pack"}
    ]
    drop = {
        "propose_skill",
        "propose_tool",
        "commit_skill_pack",
        "scaffold_agent_pack",
        "list_available_skills_and_tools",
        "propose_agent_specification",
        "export_agent_pack",
        "import_agent_pack",
    }
    allowed = [name for name in (developer.allowed_tool_names or []) if name not in drop]
    pack_tools = [name for name in (developer.pack_tool_names or []) if name not in drop]
    developer.system_prompt = prompt
    developer.allowed_skill = list(skills)
    developer.allowed_tool_names = list(allowed)
    developer.pack_tool_names = list(pack_tools)
    developer.user_modified = True
    store.save_custom_agent_profile(developer)
    store.mark_agent_user_modified("developer", modified=True)
    store.save_agent_override(
        AgentCustomization(
            agent_id="developer",
            system_prompt=prompt,
            allowed_tool_names=list(allowed),
            allowed_skill=list(skills),
            pack_tool_names=list(pack_tools),
            user_modified=True,
        )
    )

    install_platform_agent_packs(wiki.parent, registry, tools)
    after = registry.get_agent("developer")
    assert after is not None
    assert after.system_prompt == prompt
    assert "capability-authoring" in (after.allowed_skill or [])
    assert "propose_skill" in (after.allowed_tool_names or [])
    assert "scaffold_agent_pack" in (after.allowed_tool_names or [])
    assert "save_agent_specification" not in (after.allowed_tool_names or [])
    assert "cli_exec" in (after.allowed_tool_names or []) or "execute_code" in (after.allowed_tool_names or [])
