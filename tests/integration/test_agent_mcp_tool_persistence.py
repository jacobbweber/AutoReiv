"""
Integration tests for CARD-381:
Verify PUT /api/agents/{agent_id} synchronizes user-data pack.json and preserves
operator-selected MCP tools across simulated server restarts.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.platform_packs import install_platform_agent_packs
from src.web.app import create_app


def test_put_agent_persists_mcp_tools_and_pack_json_across_reboot_card_381(tmp_path: Path, monkeypatch):
    """
    CARD-381: Updating an agent with custom MCP tools via PUT /api/agents/{agent_id}
    must persist the tool selection to user data pack.json and survive server restart.
    """
    data_dir = tmp_path / "userdata"
    data_dir.mkdir(parents=True)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))

    db_path = data_dir / "autoreiv.db"
    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    wiki_path = str(data_dir / "wiki")

    app = create_app(
        state_store=store,
        wiki_path=wiki_path,
    )

    with TestClient(app) as tc:
        # 1. Fetch current autoreiv agent
        res = tc.get("/api/agents/autoreiv")
        assert res.status_code == 200
        agent_data = res.json()
        current_tools = agent_data.get("allowed_tool_names", [])

        # 2. Add an MCP tool to autoreiv
        custom_mcp_tool = "mcp_blender_render"
        new_tools = list(current_tools) + [custom_mcp_tool]
        payload = {
            "allowed_tool_names": new_tools,
            "name": agent_data["name"],
            "system_prompt": agent_data["system_prompt"],
        }

        put_res = tc.put("/api/agents/autoreiv", json=payload)
        assert put_res.status_code == 200

        # Verify immediate response
        get_res = tc.get("/api/agents/autoreiv")
        assert get_res.status_code == 200
        assert custom_mcp_tool in get_res.json()["allowed_tool_names"]

        # 3. Verify user data pack.json was synchronized
        user_pack_json = data_dir / "packs" / "autoreiv" / "pack.json"
        assert user_pack_json.is_file(), f"Expected user pack.json at {user_pack_json}"
        with open(user_pack_json, "r", encoding="utf-8") as f:
            pack_content = json.load(f)
        assert custom_mcp_tool in pack_content.get("allowed_tool_names", []), (
            "Defect CARD-381: PUT /api/agents/autoreiv failed to persist allowed_tool_names to pack.json!"
        )

        # 4. Simulate server reboot: run install_platform_agent_packs
        install_platform_agent_packs(
            data_dir=data_dir,
            agent_registry=app.state.registry,
            tool_registry=app.state.tool_reg,
        )

        # 5. Verify post-boot survival
        post_reboot_res = tc.get("/api/agents/autoreiv")
        assert post_reboot_res.status_code == 200
        assert custom_mcp_tool in post_reboot_res.json()["allowed_tool_names"], (
            f"Defect CARD-381: {custom_mcp_tool} was wiped after simulated server reboot!"
        )
