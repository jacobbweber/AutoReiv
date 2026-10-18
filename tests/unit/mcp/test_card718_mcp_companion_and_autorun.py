"""CARD-718: MCP companion skill tool scoping, HITL auto-run, Capabilities Studio copy, and RCA false-positive filter."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.application.agent_skills import tool_attachment
from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.kernel.tool_registry import ScopedToolRegistry, _tool_context
from src.application.orchestration.skill_proposals import propose_skill, propose_tool
from src.application.skills.agent_builder_tools import AgentBuilderTools
from src.application.skills.agora_authoring import save_skill_file
from src.application.telemetry.rca_proposals import RcaProposalService
from src.domain.gateway.models import ToolDefinition
from src.domain.settings.models import MCPServerConfig
from src.domain.telemetry.models import TelemetrySpan
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.content import store as content_store
from src.infrastructure.mcp.companion_author import author_mcp_companion_skill
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.mcp_mount_reconcile import reconcile_saved_mcp_server


@pytest.fixture
def env(tmp_path: Path):
    data_root = tmp_path / "data"
    (data_root / "skills").mkdir(parents=True)
    (data_root / "agents").mkdir(parents=True)
    (data_root / "tools").mkdir(parents=True)
    state = SQLiteStateStore(db_path=str(tmp_path / "autoreiv.db"))
    state.initialize_db()
    cstore = content_store.configure(data_root)
    tool_reg = ScopedToolRegistry()
    content_store.set_tool_registry(tool_reg)
    content_store.set_skill_write_guard(tool_attachment.make_skill_write_guard(state))
    agent_reg = BuiltinAgentRegistry(state_store=state, master_tool_registry=tool_reg)
    yield data_root, state, cstore, tool_reg, agent_reg
    content_store.reset_store()


def test_mcp_companion_skill_writes_tools_frontmatter_and_grants_agent_access(env):
    data_root, state, cstore, tool_reg, agent_reg = env

    gamedock_tools = [
        ToolDefinition(
            name="mcp_GameDock_get_add_game_guide",
            description="START HERE to add a new game to the catalog.",
            parameters={"type": "object", "properties": {}},
        ),
        ToolDefinition(
            name="mcp_GameDock_add_catalog_entry",
            description="Add a NEW game to the catalog from YAML text.",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        ),
    ]
    for td in gamedock_tools:
        tool_reg.register_tool(
            name=td.name,
            description=td.description,
            parameters=td.parameters,
            handler=lambda **kw: {"ok": True},
        )

    skill_path = author_mcp_companion_skill(
        server_name="GameDock",
        tools=gamedock_tools,
        url="http://192.168.1.29:8100/mcp",
        data_dir=data_root,
    )
    assert skill_path is not None and skill_path.is_file()

    loaded_skill = cstore.skills.load("mcp-gamedock")
    assert loaded_skill is not None
    assert "mcp_GameDock_get_add_game_guide" in loaded_skill.tools
    assert "mcp_GameDock_add_catalog_entry" in loaded_skill.tools
    assert "mcp_GameDock_*" in loaded_skill.tools

    autoreiv = agent_reg.get_agent("autoreiv")
    allowed = resolve_allowed_tools(autoreiv)
    assert "mcp_GameDock_get_add_game_guide" in allowed
    assert "mcp_GameDock_add_catalog_entry" in allowed


@pytest.mark.asyncio
async def test_reconcile_saved_mcp_server_authors_companion_skill_and_ticks_agent(env):
    data_root, state, cstore, tool_reg, agent_reg = env

    gamedock_tools = [
        ToolDefinition(
            name="mcp_GameDock_list_catalog",
            description="List the games GameDock can deploy.",
            parameters={"type": "object", "properties": {}},
        ),
        ToolDefinition(
            name="mcp_GameDock_add_catalog_entry",
            description="Add a NEW game to the catalog from YAML text.",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        ),
    ]

    async def _mount(**kwargs):
        for td in gamedock_tools:
            tool_reg.register_tool(
                name=td.name,
                description=td.description,
                parameters=td.parameters,
                handler=lambda **kw: {"ok": True},
            )
        return gamedock_tools

    mcp_manager = SimpleNamespace(
        mount_server=AsyncMock(side_effect=_mount),
        unmount_server=AsyncMock(),
        get_mounted_servers=lambda: {"GameDock": {"tools": [t.name for t in gamedock_tools], "tool_count": 2}},
    )

    req = MCPServerConfig(
        name="GameDock",
        transport="sse",
        url="http://192.168.1.29:8100/mcp",
        enabled=True,
    )
    outcome = await reconcile_saved_mcp_server(
        mcp_manager,
        req,
        store=state,
        data_dir=data_root,
        agent_registry=agent_reg,
        agent_id="autoreiv",
    )
    assert outcome["mounted"] is True
    assert (data_root / "skills" / "mcp-gamedock" / "SKILL.md").is_file()

    autoreiv = agent_reg.get_agent("autoreiv")
    assert "mcp-gamedock" in autoreiv.allowed_skill
    allowed = resolve_allowed_tools(autoreiv)
    assert "mcp_GameDock_list_catalog" in allowed
    assert "mcp_GameDock_add_catalog_entry" in allowed

    builder = AgentBuilderTools(agent_registry=agent_reg, tool_registry=tool_reg, store=state, data_dir=data_root)
    token = _tool_context.set({"agent_id": "autoreiv", "session_id": "s-1", "offered_tools": list(allowed.ordered)})
    try:
        catalog = await builder.list_available_skills_and_tools(query="GameDock")
    finally:
        _tool_context.reset(token)

    by_name = {t["name"]: t for t in catalog["catalog_tools"]}
    assert by_name["mcp_GameDock_add_catalog_entry"]["you_can_call"] is True


@pytest.mark.asyncio
async def test_write_skill_file_keeps_already_allowed_mcp_tools_without_pending_approval(env):
    data_root, state, cstore, tool_reg, agent_reg = env

    td = ToolDefinition(
        name="mcp_GameDock_add_catalog_entry",
        description="Add a NEW game to the catalog from YAML text.",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}},
    )
    tool_reg.register_tool(name=td.name, description=td.description, parameters=td.parameters, handler=lambda **kw: {})
    author_mcp_companion_skill("GameDock", [td], url="http://192.168.1.29:8100/mcp", data_dir=data_root)

    token = _tool_context.set({"agent_id": "autoreiv", "session_id": "s-aska", "approval_mode": "run"})
    try:
        res = await save_skill_file(
            cstore,
            "aska-gamedock-catalog",
            "SKILL.md",
            "# Aska GameDock Catalog\n\nUse `mcp_GameDock_add_catalog_entry` to add Aska.\n",
            tool_registry=tool_reg,
            state_store=state,
        )
    finally:
        _tool_context.reset(token)

    assert res["saved"] is True
    loaded = cstore.skills.load("aska-gamedock-catalog")
    assert loaded is not None
    assert "mcp_GameDock_add_catalog_entry" in loaded.tools
    # Negative assertion: no pending attach_tool_to_skill approval was created for an already-allowed tool
    assert state.get_pending_approvals() == []


def test_propose_skill_and_tool_honor_autorun_mode(env):
    data_root, state, cstore, tool_reg, agent_reg = env

    token = _tool_context.set({"agent_id": "autoreiv", "session_id": "s-autorun", "approval_mode": "run"})
    try:
        skill_res = propose_skill(
            state,
            what="Skill to add Aska",
            why="Operator asked",
            how="Use mcp_GameDock_add_catalog_entry",
            where="skills/aska-gamedock-catalog/SKILL.md",
            data_dir=data_root,
            session_id="s-autorun",
            agent_id="autoreiv",
            skill_id="aska-gamedock-catalog",
        )
        tool_res = propose_tool(
            state,
            what="Tool to add Aska",
            why="Operator asked",
            how="Stub",
            where="skills/aska-gamedock-catalog/tools/add_entry.py",
            data_dir=data_root,
            session_id="s-autorun",
            agent_id="autoreiv",
            skill_id="aska-gamedock-catalog",
            tool_json={"name": "add_entry", "description": "Add", "parameters": {"type": "object"}},
        )
    finally:
        _tool_context.reset(token)

    assert skill_res["status"] == "approved"
    assert skill_res["auto_run"] is True
    assert tool_res["status"] == "approved"
    assert tool_res["auto_run"] is True
    # Negative assertion: auto-run leaves zero pending HITL cards
    assert state.get_pending_approvals(session_id="s-autorun") == []


def test_capabilities_studio_copy_replaces_tools_studio_and_rca_ignores_builtin_validation_errors(env):
    data_root, state, cstore, tool_reg, agent_reg = env
    from src.application.skills.native_tool_engineering import NativeToolEngineeringTools
    from src.infrastructure.content.runtime_tools import RuntimeToolFiles

    files = RuntimeToolFiles(data_root / "tools")
    files.save({"name": "custom_net_tool", "code": "def run(**kw):\n    return {}\n", "description": "d", "risk_level": "low"})
    refusal = tool_attachment.runtime_tool_not_enabled("custom_net_tool") or ""
    assert "Capabilities Studio" in refusal
    assert "Tools Studio" not in refusal

    nte = NativeToolEngineeringTools(state_store=state, tool_registry=tool_reg, agent_registry=agent_reg)
    nte_reg = ScopedToolRegistry()
    nte.register_tools(nte_reg)
    reg_desc = nte_reg.get_tool_definition("register_native_tool").description
    assert "Capabilities Studio" in reg_desc
    assert "Tools Studio" not in reg_desc

    # Built-in tool validation errors must NOT stage a self-repair RCA proposal
    state.save_telemetry_span(
        TelemetrySpan(
            id="sp_builtin_err_1",
            trace_id="tr_1",
            session_id="s_1",
            agent_id="autoreiv",
            span_type="tool",
            name="register_native_tool",
            status="error",
            success=False,
            error_message="Native tools cannot use the mcp_ prefix. Attach an MCP server for that lane.",
            metadata={"arguments": {"name": "mcp_GameDock_add_catalog_entry"}},
        )
    )
    state.save_telemetry_span(
        TelemetrySpan(
            id="sp_builtin_err_2",
            trace_id="tr_1",
            session_id="s_1",
            agent_id="autoreiv",
            span_type="tool",
            name="wiki_note_update",
            status="error",
            success=False,
            error_message="Tool 'wiki_note_update' was called with arguments it does not accept. Unknown: template.",
            metadata={"arguments": {"relative_path": "00_Inbox/x.md", "template": "none"}},
        )
    )
    rca = RcaProposalService(store=state, content_store=cstore)
    proposals = rca.list_proposals(min_failures=1)
    assert all(p["target_name"] not in ("register_native_tool", "wiki_note_update") for p in proposals)
