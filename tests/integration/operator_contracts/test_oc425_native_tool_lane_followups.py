"""CARD-425 operator contract: user-modified developer allowlist and legacy pack tools.

REQ-425-001: a user_modified developer gains native-tool-engineering plus
register_native_tool / plan_native_folder without a prompt rewrite or allowlist wipe.
REQ-425-002: packs/<id>/tools/*.py stays an in-process legacy loader and is not
catalogued as Native custom (source native_custom).

Temp user-data only [ADR-0055].
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from starlette.testclient import TestClient

from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization, MCPServerConfig
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.platform_packs import install_platform_agent_packs
from src.web.app import create_app

NATIVE_SKILL = "native-tool-engineering"
NATIVE_TOOLS = ("register_native_tool", "plan_native_folder")
KEPT_TOOL = "operator_keep_tool"
REMOVED_TOOL = "cli_exec"
MCP_NAME = "desk-425"
PROMPT_MARK = "OPERATOR PROMPT CARD-425"


def _refuse_live(user_data: Path) -> None:
    local_app = os.environ.get("LOCALAPPDATA") or ""
    if not local_app:
        return
    live_root = (Path(local_app) / "AutoReiv").resolve()
    ud = str(user_data.resolve()).replace("\\", "/").lower()
    live = str(live_root).replace("\\", "/").lower()
    assert ud != live and not ud.startswith(live + "/"), f"operator contracts must not use live user-data: {user_data}"


def _names(servers) -> list[str]:
    found = []
    for server in servers or []:
        found.append(server.name if hasattr(server, "name") else server.get("name"))
    return found


def test_oc425_user_modified_developer_gains_native_skill_without_clobber(operator_client):
    """REQ-425-001. Additive grant only. Prompt, other tools, and MCP servers stay."""
    client, store, wiki = operator_client
    registry = client.app.state.registry
    tools = client.app.state.tool_registry
    user_data = wiki.parent

    developer = registry.get_agent("developer")
    assert developer is not None
    prompt = f"{PROMPT_MARK}\n{developer.system_prompt}"
    allowed = [
        name for name in (developer.allowed_tool_names or []) if name not in NATIVE_TOOLS and name != REMOVED_TOOL
    ]
    assert REMOVED_TOOL not in allowed
    allowed.append(KEPT_TOOL)
    skills = [sid for sid in (developer.allowed_skill or []) if sid != NATIVE_SKILL]
    skills.append("operator-custom-skill")
    pack_tools = [name for name in (developer.pack_tool_names or []) if name not in NATIVE_TOOLS]
    mcp = [MCPServerConfig(name=MCP_NAME, command=["python", "-c", "pass"], enabled=True)]

    developer.system_prompt = prompt
    developer.allowed_tool_names = list(allowed)
    developer.allowed_skill = list(skills)
    developer.pack_tool_names = list(pack_tools)
    developer.mcp_servers = list(mcp)
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
            mcp_servers=list(mcp),
            user_modified=True,
        )
    )

    install_platform_agent_packs(user_data, registry, tools)

    after = registry.get_agent("developer")
    assert after is not None
    assert after.system_prompt == prompt
    assert PROMPT_MARK in after.system_prompt
    assert NATIVE_SKILL in (after.allowed_skill or [])
    assert "operator-custom-skill" in (after.allowed_skill or [])
    for name in NATIVE_TOOLS:
        assert name in (after.allowed_tool_names or [])
        assert name in (after.pack_tool_names or [])
        assert name in tools
    assert KEPT_TOOL in (after.allowed_tool_names or [])
    assert REMOVED_TOOL not in (after.allowed_tool_names or []), "REQ-425-001 FAIL: unrelated removed tool was restored"
    assert MCP_NAME in _names(after.mcp_servers)
    assert bool(after.user_modified) is True
    assert (after.allowed_skill or []).count(NATIVE_SKILL) == 1
    assert (after.allowed_tool_names or []).count("register_native_tool") == 1

    stored = store.get_agent_profile("developer")
    assert stored is not None
    assert stored.system_prompt == prompt
    assert NATIVE_SKILL in (stored.allowed_skill or [])
    assert KEPT_TOOL in (stored.allowed_tool_names or [])
    assert REMOVED_TOOL not in (stored.allowed_tool_names or [])
    assert MCP_NAME in _names(stored.mcp_servers)

    override = store.get_agent_override("developer")
    assert override is not None
    assert override.system_prompt == prompt
    assert NATIVE_SKILL in (override.allowed_skill or [])
    assert KEPT_TOOL in (override.allowed_tool_names or [])
    assert REMOVED_TOOL not in (override.allowed_tool_names or [])
    assert MCP_NAME in _names(override.mcp_servers)
    assert bool(override.user_modified) is True

    install_platform_agent_packs(user_data, registry, tools)
    again = registry.get_agent("developer")
    assert again is not None
    assert (again.allowed_skill or []).count(NATIVE_SKILL) == 1
    assert (again.allowed_tool_names or []).count("register_native_tool") == 1
    assert again.system_prompt == prompt

    # Grant is once. A later removal stays removed [ADR-0056].
    raw = store.get_agent_profile("developer")
    assert raw is not None
    raw.allowed_skill = [sid for sid in (raw.allowed_skill or []) if sid != NATIVE_SKILL]
    raw.allowed_tool_names = [name for name in (raw.allowed_tool_names or []) if name not in NATIVE_TOOLS]
    raw.pack_tool_names = [name for name in (raw.pack_tool_names or []) if name not in NATIVE_TOOLS]
    raw.system_prompt = prompt
    raw.user_modified = True
    store.save_custom_agent_profile(raw)
    override.allowed_skill = list(raw.allowed_skill)
    override.allowed_tool_names = list(raw.allowed_tool_names)
    override.pack_tool_names = list(raw.pack_tool_names)
    override.system_prompt = prompt
    override.user_modified = True
    store.save_agent_override(override)

    install_platform_agent_packs(user_data, registry, tools)
    final = registry.get_agent("developer")
    assert final is not None
    assert NATIVE_SKILL not in (final.allowed_skill or []), (
        "REQ-425-001 FAIL: removed native-tool-engineering was re-added after the grant"
    )
    assert "register_native_tool" not in (final.allowed_tool_names or [])
    assert "plan_native_folder" not in (final.allowed_tool_names or [])
    assert final.system_prompt == prompt
    assert KEPT_TOOL in (final.allowed_tool_names or [])
    assert MCP_NAME in _names(final.mcp_servers)


def test_oc425_pack_py_bootstrap_is_not_native_custom(tmp_path, monkeypatch):
    """REQ-425-002. packs/<id>/tools/*.py must not claim source=native_custom."""
    user_data = (tmp_path / "user-data").resolve()
    wiki = user_data / "wiki"
    db = user_data / "autoreiv.db"
    user_data.mkdir(parents=True, exist_ok=True)
    wiki.mkdir(parents=True, exist_ok=True)
    _refuse_live(user_data)

    tool_file = user_data / "packs" / "widget" / "tools" / "widget_ping.py"
    tool_file.parent.mkdir(parents=True, exist_ok=True)
    tool_file.write_text(
        "def widget_ping(action='status', **kwargs):\n"
        '    """Legacy in-process pack tool."""\n'
        "    return {'marker': 'IN_PROCESS', 'action': action, 'details': kwargs}\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(user_data))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki))
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "local")

    store = SQLiteStateStore(db_path=str(db))
    store.initialize_db()
    app = create_app(state_store=store, wiki_path=str(wiki))
    with TestClient(app) as client:
        registry = client.app.state.tool_registry
        assert "widget_ping" in registry
        assert registry.get_tool_origin("widget_ping") == "legacy_pack_tool"
        assert registry.get_tool_origin("widget_ping") != "native_custom"

        response = client.get("/api/agent_training_factory/capabilities")
        assert response.status_code == 200, response.text
        namespaces = response.json()["namespaces"]
        matches = []
        for namespace in namespaces:
            for tool in namespace.get("tools") or []:
                if tool.get("name") == "widget_ping":
                    matches.append((namespace, tool))
        assert len(matches) == 1
        namespace, tool = matches[0]
        assert namespace["source"] == "legacy_pack_tool"
        assert namespace["source"] != "native_custom"
        assert namespace["origin_label"] == "Legacy pack tool"
        assert namespace["origin_label"] != "Native custom"
        assert tool["origin"] == "legacy_pack_tool"
        assert tool["origin"] != "native_custom"
        assert tool["origin_label"] == "Legacy pack tool"
        assert tool["origin_label"] != "Native custom"

        stored = store.get_setting("native_custom_tools")
        names = []
        if isinstance(stored, list):
            names = [row.get("name") for row in stored if isinstance(row, dict)]
        assert "widget_ping" not in names

        agent = AgentProfile(
            id="widget",
            name="Widget",
            description="Widget",
            system_prompt="Widget",
            allowed_tool_names=["widget_ping"],
        )
        result = asyncio.run(
            registry.execute(
                ToolCall(id="c1", name="widget_ping", arguments={"action": "status"}),
                agent,
            )
        )
        assert result.success is True
        assert result.output["marker"] == "IN_PROCESS"
