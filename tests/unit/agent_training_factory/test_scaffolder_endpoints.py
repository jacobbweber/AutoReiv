"""Unit tests for CARD-386 3-Column Scaffolder and Capabilities Workshop endpoints."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.gateway.models import ToolDefinition
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.mark.asyncio
async def test_get_factory_capabilities(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    app = create_app(state_store=store)

    # Mount a dummy MCP tool into tool_registry to test grouping
    tool_reg = app.state.tool_registry
    tool_reg.mount_mcp_tool(
        definition=ToolDefinition(
            name="mcp_blender_create_cube",
            description="Create a 3D cube in Blender",
            parameters={"type": "object", "properties": {"size": {"type": "number"}}},
        ),
        handler=lambda **kwargs: "cube_created",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/agent_training_factory/capabilities")
        assert resp.status_code == 200
        data = resp.json()

        assert "namespaces" in data
        assert "total_tools" in data
        assert data["total_tools"] > 0

        # Verify blender MCP namespace is present
        blender_ns = next((ns for ns in data["namespaces"] if "blender" in ns["id"].lower()), None)
        assert blender_ns is not None
        assert any(t["name"] == "mcp_blender_create_cube" for t in blender_ns["tools"])


@pytest.mark.asyncio
async def test_scaffold_runbook_generation(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    app = create_app(state_store=store)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "agent_id": "autoreiv",
            "skill_id": "blender-scene-builder",
            "skill_name": "Blender Scene Builder",
            "trigger_description": "Create and render 3D scenes in Blender",
            "intent_notes": "First create mesh, then position light, then render image.",
            "selected_tools": ["mcp_blender_create_cube", "mcp_blender_render_frame"],
            "source_context": "Blender MCP server v1.2 supports headless rendering via Cycles or Eevee.",
        }
        resp = await ac.post("/api/agent_training_factory/scaffold/runbook", json=payload)
        assert resp.status_code == 200
        result = resp.json()

        assert result["skill_id"] == "blender-scene-builder"
        assert result["skill_name"] == "Blender Scene Builder"
        markdown = result["markdown_content"]

        # Verify Matt Pocock standard YAML frontmatter
        assert markdown.strip().startswith("---")
        assert "name: Blender Scene Builder" in markdown
        assert "requires_tools:" in markdown
        assert "mcp_blender_create_cube" in markdown
        assert "mcp_blender_render_frame" in markdown

        # Negative Assertion: Must NOT generate synthetic Python code files
        assert "def execute(" not in markdown
        assert "class Tool(" not in markdown


@pytest.mark.asyncio
async def test_scaffold_save_and_pin_skill(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    packs_dir = data_dir / "packs"
    packs_dir.mkdir(parents=True, exist_ok=True)
    agent_dir = packs_dir / "autoreiv"
    agent_dir.mkdir(parents=True, exist_ok=True)

    # Initial pack.json with existing skill
    initial_pack = {
        "schema_version": "1.0",
        "id": "autoreiv",
        "name": "AutoReiv Host",
        "description": "General coordinator",
        "allowed_skill": ["wiki"],
        "skills": [{"id": "wiki", "tools": ["wiki_note_create"]}],
        "allowed_tool_names": ["handoff_to_agent"],
    }
    (agent_dir / "pack.json").write_text(json.dumps(initial_pack), encoding="utf-8")

    store = SQLiteStateStore(db_path=str(db_path))
    app = create_app(state_store=store)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        save_payload = {
            "agent_id": "autoreiv",
            "skill_id": "blender-render",
            "skill_content": """---
name: Blender Render
description: Render 3D scenes via Blender MCP
requires_tools:
  - mcp_blender_render
---
# Blender Render
## Procedure
1. Call mcp_blender_render with output path.
""",
            "auto_pin": True,
        }
        resp = await ac.post("/api/agent_training_factory/scaffold/save", json=save_payload)
        assert resp.status_code == 200
        res = resp.json()
        assert res["success"] is True
        assert res["pinned"] is True

        # Verify file written to disk
        skill_file = agent_dir / "skills" / "blender-render" / "SKILL.md"
        assert skill_file.is_file()
        assert "Render 3D scenes via Blender MCP" in skill_file.read_text(encoding="utf-8")

        # Verify pack.json updated without clobbering existing skills
        updated_pack = json.loads((agent_dir / "pack.json").read_text(encoding="utf-8"))
        assert "wiki" in updated_pack["allowed_skill"]
        assert "blender-render" in updated_pack["allowed_skill"]

        # Negative Assertion: Zero Python code files written in the skill directory
        assert not list(skill_file.parent.glob("*.py"))
