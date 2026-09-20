"""Integration lifecycle test for CARD-386 3-Column Scaffolder and Capabilities Workshop."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.gateway.models import ToolDefinition
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.mark.asyncio
async def test_scaffolder_full_lifecycle_existing_and_new_agents(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    app = create_app(state_store=store)

    # 1. Mount external MCP tool (e.g. Blender)
    tool_reg = app.state.tool_registry
    tool_reg.mount_mcp_tool(
        definition=ToolDefinition(
            name="mcp_blender_render_frame",
            description="Render a single frame in Blender MCP",
            parameters={
                "type": "object",
                "properties": {
                    "scene": {"type": "string"},
                    "camera": {"type": "string"},
                },
                "required": ["scene"],
            },
        ),
        handler=lambda **kwargs: "rendered_ok",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 2. Inspect capabilities
        caps_resp = await ac.get("/api/agent_training_factory/capabilities")
        assert caps_resp.status_code == 200
        caps = caps_resp.json()
        assert caps["total_tools"] > 0
        blender_ns = next((ns for ns in caps["namespaces"] if "blender" in ns["id"].lower()), None)
        assert blender_ns is not None

        # 3. Scaffold a tool-assisted skill for existing agent 'autoreiv'
        runbook_req = {
            "agent_id": "autoreiv",
            "skill_id": "blender-render-frame",
            "skill_name": "Blender Render Frame",
            "trigger_description": "Render a single 3D frame via Blender MCP",
            "intent_notes": "Validate camera exists before triggering headless render.",
            "selected_tools": ["mcp_blender_render_frame"],
            "source_context": "Blender Cycles engine requires GPU device configured.",
        }
        gen_resp = await ac.post("/api/agent_training_factory/scaffold/runbook", json=runbook_req)
        assert gen_resp.status_code == 200
        gen_data = gen_resp.json()
        assert "requires_tools:" in gen_data["markdown_content"]
        assert "mcp_blender_render_frame" in gen_data["markdown_content"]

        # 4. Save and auto-pin skill to 'autoreiv'
        save_req = {
            "agent_id": "autoreiv",
            "skill_id": "blender-render-frame",
            "skill_content": gen_data["markdown_content"],
            "auto_pin": True,
        }
        save_resp = await ac.post("/api/agent_training_factory/scaffold/save", json=save_req)
        assert save_resp.status_code == 200
        save_data = save_resp.json()
        assert save_data["success"] is True
        assert save_data["pinned"] is True

        # 5. Verify reflection in agent profile & pack.json
        autoreiv_pack_json = data_dir / "packs" / "autoreiv" / "pack.json"
        assert autoreiv_pack_json.is_file()
        pack_manifest = json.loads(autoreiv_pack_json.read_text(encoding="utf-8"))
        assert "blender-render-frame" in pack_manifest["allowed_skill"]

        # 6. Verify dynamic tool scoping resolves the MCP tool when the skill is active
        agent_profile = app.state.registry.get_agent("autoreiv")
        assert agent_profile is not None
        scoped_tools = tool_reg.get_tools_for_agent(agent_profile, active_skills=["blender-render-frame"])
        scoped_names = [t.name for t in scoped_tools]
        assert "mcp_blender_render_frame" in scoped_names

        # 7. Scaffold a brand-new agent with pure knowledge skill (no tools)
        new_agent_runbook_req = {
            "agent_id": "math-tutor",
            "skill_id": "socratic-algebra",
            "skill_name": "Socratic Algebra",
            "trigger_description": "Guide students through algebra via Socratic inquiry",
            "intent_notes": "Never provide direct answers; ask guiding diagnostic questions.",
            "selected_tools": [],
            "source_context": "Pedagogy guidelines for high school algebra.",
        }
        new_gen_resp = await ac.post("/api/agent_training_factory/scaffold/runbook", json=new_agent_runbook_req)
        assert new_gen_resp.status_code == 200

        new_save_req = {
            "agent_id": "math-tutor",
            "agent_name": "Math Tutor",
            "role_persona": "Patient Socratic teacher for algebra concepts.",
            "model": "default",
            "skill_id": "socratic-algebra",
            "skill_content": new_gen_resp.json()["markdown_content"],
            "auto_pin": True,
        }
        new_save_resp = await ac.post("/api/agent_training_factory/scaffold/save", json=new_save_req)
        assert new_save_resp.status_code == 200

        # Verify new pack directory and files
        math_pack_dir = data_dir / "packs" / "math-tutor"
        assert math_pack_dir.is_dir()
        assert (math_pack_dir / "pack.json").is_file()
        assert (math_pack_dir / "skills" / "socratic-algebra" / "SKILL.md").is_file()

        # Negative assertions
        assert not list(math_pack_dir.glob("*.py"))
        assert not list((math_pack_dir / "skills" / "socratic-algebra").glob("*.py"))
