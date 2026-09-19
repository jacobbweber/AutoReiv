"""
Regression tests for CARD-381:
Preserve Platform Pack MCP Tools and Custom Grants Across Server Restarts and Reconciliation.
"""

import json
from pathlib import Path

from src.application.telemetry.collector import TelemetryCollector
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.platform_packs import install_platform_agent_packs


def test_reboot_does_not_wipe_custom_mcp_tools_card_381(tmp_path: Path):
    """
    Negative assertion: Re-running install_platform_agent_packs on server boot
    MUST NOT wipe operator-added MCP tools from allowed_tool_names for platform packs.
    """
    db_path = tmp_path / "autoreiv.db"
    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    telemetry = TelemetryCollector(store=store)
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True)
    wiki_root = str(tmp_path / "wiki")

    # 1. Initial bootstrap
    registry, tool_registry = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=wiki_root,
        skills_dir=str(skills_dir),
    )

    agent = registry.get_agent("autoreiv")
    assert agent is not None
    initial_tools = list(agent.allowed_tool_names or [])

    # 2. Operator adds custom MCP tools to AutoReiv
    custom_mcp_tool = "mcp_blender_render"
    custom_mcp_tool_2 = "mcp_github_create_issue"
    updated_tools = initial_tools + [custom_mcp_tool, custom_mcp_tool_2]

    agent.allowed_tool_names = updated_tools
    store.save_custom_agent_profile(agent)

    # Also simulate writing to user data packs/autoreiv/pack.json
    dest_pack_json = tmp_path / "packs" / "autoreiv" / "pack.json"
    if dest_pack_json.is_file():
        with open(dest_pack_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["allowed_tool_names"] = updated_tools
        with open(dest_pack_json, "w", encoding="utf-8") as f:
            json.dump(data, f)

    # Verify state in SQLite before reboot
    persisted = store.get_agent_profile("autoreiv")
    assert persisted is not None
    assert custom_mcp_tool in persisted.allowed_tool_names

    # 3. Simulate Server Reboot: Run install_platform_agent_packs again
    data_dir = tmp_path
    install_platform_agent_packs(
        data_dir=data_dir,
        agent_registry=registry,
        tool_registry=tool_registry,
    )

    # 4. Fetch agent post-boot
    post_boot_agent = registry.get_agent("autoreiv")
    assert post_boot_agent is not None

    # NEGATIVE ASSERTION: Factory re-seeding must NOT have wiped operator-selected MCP tools
    assert custom_mcp_tool in post_boot_agent.allowed_tool_names, (
        f"Defect CARD-381: {custom_mcp_tool} was clobbered by install_platform_agent_packs on boot!"
    )
    assert custom_mcp_tool_2 in post_boot_agent.allowed_tool_names

    # Verify user data pack.json was not overwritten with factory seed
    if dest_pack_json.is_file():
        with open(dest_pack_json, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert custom_mcp_tool in saved_data.get("allowed_tool_names", []), (
            "Defect CARD-381: dest/pack.json allowed_tool_names was overwritten by repo factory seed!"
        )
