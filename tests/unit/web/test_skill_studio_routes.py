"""CARD-497 tests 1-6: Skill Studio routes under their own names [REQ-497-001..004, D1, D4, D11]."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.gateway.models import ToolDefinition
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

SKILL_MD = """---
name: Blender Render
description: Render 3D scenes via Blender MCP
tools:
  - mcp_blender_render
---
# Blender Render
## Procedure
1. Call mcp_blender_render with output path.
"""


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    store = SQLiteStateStore(db_path=str(db_path))
    app = create_app(state_store=store)
    return app, data_dir


def _client(app) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_1_tools_studio_capabilities_shape(app_env):
    app, _ = app_env
    app.state.tool_registry.mount_mcp_tool(
        definition=ToolDefinition(
            name="mcp_blender_create_cube",
            description="Create a 3D cube in Blender",
            parameters={"type": "object", "properties": {"size": {"type": "number"}}},
        ),
        handler=lambda **kwargs: "cube_created",
    )
    async with _client(app) as ac:
        resp = await ac.get("/api/tools_studio/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tools"] > 0
    ids = {ns["id"] for ns in data["namespaces"]}
    assert "platform" in ids
    blender = next(ns for ns in data["namespaces"] if "blender" in ns["id"].lower())
    assert blender["source"] == "mcp"
    assert blender["origin_label"]
    assert any(t["name"] == "mcp_blender_create_cube" for t in blender["tools"])
    for ns in data["namespaces"]:
        for tool in ns["tools"]:
            assert {"name", "description", "parameters", "origin", "origin_label"} <= set(tool)


@pytest.mark.asyncio
async def test_2_runbook_fallback_and_model_text(app_env):
    app, _ = app_env
    payload = {
        "agent_id": "autoreiv",
        "skill_id": "blender-scene-builder",
        "skill_name": "Blender Scene Builder",
        "trigger_description": "Create and render 3D scenes in Blender",
        "intent_notes": "First create mesh, then position light, then render image.",
        "selected_tools": ["mcp_blender_create_cube"],
    }
    app.state.gateway = None
    async with _client(app) as ac:
        resp = await ac.post("/api/skill_studio/runbook", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["skill_id"] == "blender-scene-builder"
    md = body["markdown_content"]
    assert md.startswith("---")
    assert "name: Blender Scene Builder" in md
    assert "mcp_blender_create_cube" in md
    assert "def execute(" not in md

    class _Resp:
        text = "---\nname: Model Written\ndescription: x\ntools: []\n---\n# Model Written\n"

    class _Gateway:
        default_model_id = "default"

        async def complete(self, request):
            return _Resp()

    app.state.gateway = _Gateway()
    async with _client(app) as ac:
        resp = await ac.post("/api/skill_studio/runbook", json=payload)
    assert resp.status_code == 200
    assert "Model Written" in resp.json()["markdown_content"]


@pytest.mark.asyncio
async def test_3_save_binds_pins_and_uses_app_data_dir(app_env, tmp_path, monkeypatch):
    app, data_dir = app_env
    app.state.tool_registry.register_tool(
        "mcp_blender_render", "Render via Blender", {"type": "object", "properties": {}}, lambda **_k: "ok"
    )
    # D11: the route must use app.state.data_dir_paths, not a fresh resolver reading the env.
    elsewhere = tmp_path / "elsewhere"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(elsewhere))

    async with _client(app) as ac:
        resp = await ac.post(
            "/api/skill_studio/save",
            json={"agent_id": "autoreiv", "skill_id": "blender-render", "skill_content": SKILL_MD, "auto_pin": True},
        )
    assert resp.status_code == 200, resp.text
    res = resp.json()
    assert res["success"] is True
    assert res["pinned"] is True
    assert res["binding_store"] == "skill_md"  # CARD-570: the SKILL.md tools list is the binding
    assert res["tools"] == ["mcp_blender_render"]
    skill_file = data_dir / "skills" / "blender-render" / "SKILL.md"
    assert skill_file.is_file()
    assert "blender-render" in app.state.registry.get_agent("autoreiv").allowed_skill
    assert (data_dir / "agents" / "autoreiv.md").is_file()  # the pin wrote AutoReiv's user copy
    assert not elsewhere.exists() or not list(elsewhere.rglob("SKILL.md"))

    # Save without an agent brief (CARD-418) still writes to the skill store.
    async with _client(app) as ac:
        resp2 = await ac.post(
            "/api/skill_studio/save",
            json={"skill_id": "solo-skill", "skill_content": SKILL_MD.replace("Blender Render", "Solo Skill")},
        )
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["pinned"] is False
    assert Path(resp2.json()["skill_store_path"]).resolve().is_relative_to(data_dir.resolve())


@pytest.mark.asyncio
async def test_4_skills_list_and_open(app_env):
    app, data_dir = app_env
    app.state.tool_registry.register_tool(
        "mcp_blender_render", "Render via Blender", {"type": "object", "properties": {}}, lambda **_k: "ok"
    )
    async with _client(app) as ac:
        save = await ac.post("/api/skill_studio/save", json={"skill_id": "blender-render", "skill_content": SKILL_MD})
        assert save.status_code == 200, save.text
        listed = await ac.get("/api/skill_studio/skills")
        assert listed.status_code == 200
        ids = {s.get("id") for s in listed.json()["skills"]}
        assert "blender-render" in ids
        opened = await ac.get("/api/skill_studio/skills/blender-render")
        assert opened.status_code == 200
        assert "mcp_blender_render" in json.dumps(opened.json())
        missing = await ac.get("/api/skill_studio/skills/no-such-skill")
        assert missing.status_code == 404


# CARD-577: the 308 redirects from /api/agent_training_factory/* are gone; the old paths are 404 (test_6).


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/agent_training_factory/jobs"),
        ("GET", "/api/agent_training_factory/capabilities"),
        ("POST", "/api/agent_training_factory/scaffold/runbook"),
        ("GET", "/api/agent_training_factory/skills"),
        ("POST", "/api/agent_training_factory/jobs"),
        ("GET", "/api/agent_training_factory/jobs/fjob_1"),
        ("POST", "/api/agent_training_factory/jobs/fjob_1/step"),
        ("POST", "/api/agent_training_factory/jobs/fjob_1/promote"),
        ("DELETE", "/api/agent_training_factory/jobs/fjob_1"),
        ("GET", "/api/agent_training_factory/gaps"),
        ("GET", "/api/agent_training_factory/phases/instructions"),
        ("PUT", "/api/agent_training_factory/phases/intent_distill/instructions"),
        ("DELETE", "/api/agent_training_factory/phases/intent_distill/instructions"),
        ("POST", "/api/agents/autoreiv/gaps/gap_x/train"),
    ],
)
async def test_6_removed_routes_404(shared_app, method, path):
    app = shared_app  # stateless 404 check [CARD-560]
    async with _client(app) as ac:
        resp = await ac.request(method, path, json={} if method in ("POST", "PUT") else None)
    assert resp.status_code in (404, 405)
    if method == "GET":
        assert resp.status_code == 404
