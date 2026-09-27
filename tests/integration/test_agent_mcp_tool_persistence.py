"""
Integration tests for CARD-381, updated for CARD-539 (ADR-0061, D2):
an MCP tool reaches an agent only through a ticked skill that binds it. A Save's tool list is ignored;
the tick persists across a simulated server restart.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.platform_packs import install_platform_agent_packs
from src.web.app import create_app


def test_mcp_tool_reaches_agent_via_ticked_skill_and_survives_reboot(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "userdata"
    data_dir.mkdir(parents=True)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(data_dir / "autoreiv.db"))  # bindings live in the app DB
    store = SQLiteStateStore(db_path=str(data_dir / "autoreiv.db"))
    store.initialize_db()
    app = create_app(state_store=store, wiki_path=str(data_dir / "wiki"))
    custom_mcp_tool = "mcp_blender_render"

    with TestClient(app) as tc:
        agent_data = tc.get("/api/agents/autoreiv").json()
        base = {"name": agent_data["name"], "system_prompt": agent_data["system_prompt"]}

        # A tool list in the payload grants nothing.
        put = tc.put(
            "/api/agents/autoreiv",
            json={**base, "allowed_tool_names": list(agent_data.get("allowed_tool_names") or []) + [custom_mcp_tool]},
        )
        assert put.status_code == 200, put.text
        assert custom_mcp_tool not in tc.get("/api/agents/autoreiv").json()["allowed_tool_names"]

        # Attaching the server (as the migration and an accepted proposal do) creates a real skill binding
        # mcp_blender_* and ticks it.
        from src.application.agent_packs.tool_attachment import apply_tool_attachment

        apply_tool_attachment(
            store, app.state.registry, app.state.tool_reg,
            {"tool": "mcp_blender_*", "agent_id": "autoreiv", "skill_id": "mcp-blender", "new_skill": True,
             "description": "Tools of the blender MCP server"},
            data_root=data_dir,
        )
        got = tc.get("/api/agents/autoreiv").json()
        assert "mcp-blender" in got["allowed_skill"]
        assert "mcp_blender_*" in got["allowed_tool_names"]

        install_platform_agent_packs(
            data_dir=data_dir,
            agent_registry=app.state.registry,
            tool_registry=app.state.tool_reg,
        )
        after = tc.get("/api/agents/autoreiv").json()
        assert "mcp-blender" in after["allowed_skill"], "the tick was wiped after a simulated reboot"
        assert "mcp_blender_*" in after["allowed_tool_names"]

        # A later Studio Save with the current version keeps the tick.
        save = tc.put("/api/agents/autoreiv", json={**base, "allowed_skill": after["allowed_skill"],
                                                    "expected_skills_version": after["skills_version"]})
        assert save.status_code == 200, save.text
        assert "mcp-blender" in tc.get("/api/agents/autoreiv").json()["allowed_skill"]
