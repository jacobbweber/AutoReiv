"""
Integration tests for Agent Forge REST API [REQ-FORGE-006].
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def app():
    store = SQLiteStateStore(db_path=":memory:")
    return create_app(state_store=store)


@pytest.mark.asyncio
async def test_agent_forge_crud_api(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Get Skills Catalog
        cat_resp = await ac.get("/api/skills/catalog")
        assert cat_resp.status_code == 200
        cat = cat_resp.json()
        assert "tools" in cat
        assert "purposes" in cat

        # 2. List Agents
        list_resp = await ac.get("/api/agents")
        assert list_resp.status_code == 200
        agents = list_resp.json()
        ids = {a["id"] for a in agents}
        assert {"assistant", "autoreiv", "agent-builder"} <= ids
        assert "coding" not in ids
        assert "conductor" not in ids
        assert "review" not in ids
        ab = next(a for a in agents if a["id"] == "agent-builder")
        assert ab["show_in_chat"] is False
        ar = next(a for a in agents if a["id"] == "autoreiv")
        assert ar["show_in_chat"] is True

        # 3. Create Custom Agent
        new_agent = {
            "id": "security-auditor",
            "name": "Security Auditor",
            "description": "SOC2 compliance & vulnerability scanning",
            "system_prompt": "You audit code and infrastructure for CVEs.",
            "purpose": "reasoning",
            "tone": "technical",
            "avatar_icon": "shield-alert",
            "model": "default",
            "allowed_tool_names": ["system_info", "verify_telemetry_consistency"],
            "max_turns": 10,
        }
        create_resp = await ac.post("/api/agents", json=new_agent)
        assert create_resp.status_code == 200
        assert create_resp.json()["status"] == "created"

        # 4. Get Agent by ID
        get_resp = await ac.get("/api/agents/security-auditor")
        assert get_resp.status_code == 200
        agent_data = get_resp.json()
        assert agent_data["name"] == "Security Auditor"
        assert agent_data["purpose"] == "reasoning"
        assert agent_data["avatar_icon"] == "shield-alert"

        # 5. Update Agent
        update_payload = {
            "name": "Lead Security Auditor",
            "description": "SOC2 compliance lead",
            "system_prompt": "You lead security audits.",
            "purpose": "reasoning",
            "tone": "technical",
            "avatar_icon": "shield",
            "model": "default",
            "allowed_tool_names": ["system_info"],
            "max_turns": 15,
        }
        put_resp = await ac.put("/api/agents/security-auditor", json=update_payload)
        assert put_resp.status_code == 200
        assert put_resp.json()["status"] == "updated"

        # 6. Delete Custom Agent
        del_resp = await ac.delete("/api/agents/security-auditor")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

        # 7. Cannot delete built-in agent
        bad_del = await ac.delete("/api/agents/assistant")
        assert bad_del.status_code == 400


@pytest.mark.asyncio
async def test_custom_agent_purpose_persists(app):
    """Forge save of custom agent purpose must survive reload."""
    from src.domain.kernel.models import AgentProfile

    app.state.registry.register_custom_agent(
        AgentProfile(
            id="custom-worker",
            name="Custom Worker",
            description="Worker agent",
            system_prompt="Worker agent",
            purpose="task_execution",
            is_builtin=False,
        )
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        get_resp = await ac.get("/api/agents/custom-worker")
        assert get_resp.status_code == 200
        worker = get_resp.json()
        assert worker["is_builtin"] is False
        put_resp = await ac.put(
            "/api/agents/custom-worker",
            json={
                "name": worker["name"],
                "description": worker.get("description") or "",
                "system_prompt": worker["system_prompt"],
                "purpose": "general",
                "tone": worker.get("tone") or "default",
                "avatar_icon": worker.get("avatar_icon") or "bot",
                "model": worker.get("model") or "default",
                "allowed_tool_names": worker.get("allowed_tool_names") or [],
                "max_turns": worker.get("max_turns") or 10,
            },
        )
        assert put_resp.status_code == 200
        reload_resp = await ac.get("/api/agents/custom-worker")
        assert reload_resp.status_code == 200
        assert reload_resp.json()["purpose"] == "general"


@pytest.mark.asyncio
async def test_custom_agent_provider_persists(app):
    """Forge save of custom agent provider and model must survive reload [CARD-153]."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        new_agent = {
            "id": "deepseek-specialist",
            "name": "DeepSeek Specialist",
            "description": "Uses DeepSeek provider",
            "system_prompt": "You are a specialist using DeepSeek.",
            "provider": "deepseek",
            "model": "deepseek-coder",
            "tone": "technical",
            "avatar_icon": "bot",
            "allowed_tool_names": [],
            "max_turns": 10,
        }
        create_resp = await ac.post("/api/agents", json=new_agent)
        assert create_resp.status_code == 200
        assert create_resp.json()["status"] == "created"

        get_resp = await ac.get("/api/agents/deepseek-specialist")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["provider"] == "deepseek"
        assert data["model"] == "deepseek-coder"

        # Update provider and model
        update_payload = {
            "name": "DeepSeek Specialist",
            "description": "Updated description",
            "system_prompt": "You are a specialist using OpenAI.",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "tone": "technical",
            "avatar_icon": "bot",
            "allowed_tool_names": [],
            "max_turns": 10,
        }
        put_resp = await ac.put("/api/agents/deepseek-specialist", json=update_payload)
        assert put_resp.status_code == 200

        reload_resp = await ac.get("/api/agents/deepseek-specialist")
        assert reload_resp.status_code == 200
        reloaded = reload_resp.json()
        assert reloaded["provider"] == "openai"
        assert reloaded["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_builtin_agent_provider_override_persists(app):
    """Builtin agent override can customize provider and model [CARD-153]."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        get_resp = await ac.get("/api/agents/assistant")
        assert get_resp.status_code == 200
        asst = get_resp.json()
        assert asst["is_platform_pack"] is True
        assert asst["provider"] == "default"

        update_payload = {
            "name": asst["name"],
            "description": asst.get("description") or "",
            "system_prompt": asst["system_prompt"],
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "tone": asst.get("tone") or "default",
            "avatar_icon": asst.get("avatar_icon") or "bot",
            "allowed_tool_names": asst.get("allowed_tool_names") or [],
            "max_turns": asst.get("max_turns") or 10,
        }
        put_resp = await ac.put("/api/agents/assistant", json=update_payload)
        assert put_resp.status_code == 200

        reload_resp = await ac.get("/api/agents/assistant")
        assert reload_resp.status_code == 200
        reloaded = reload_resp.json()
        assert reloaded["provider"] == "anthropic"
        assert reloaded["model"] == "claude-3-5-sonnet"

        # Verify true builtin agent (agent-builder) saves provider override to agent_overrides table
        ab_resp = await ac.get("/api/agents/agent-builder")
        assert ab_resp.status_code == 200
        ab_data = ab_resp.json()
        assert ab_data["is_builtin"] is True
        assert ab_data["provider"] == "default"

        ab_update = {
            "name": ab_data["name"],
            "description": ab_data.get("description") or "",
            "system_prompt": ab_data["system_prompt"],
            "provider": "lmstudio",
            "model": "qwen2.5-coder",
            "tone": ab_data.get("tone") or "default",
            "avatar_icon": ab_data.get("avatar_icon") or "bot",
            "allowed_tool_names": ab_data.get("allowed_tool_names") or [],
            "max_turns": ab_data.get("max_turns") or 10,
        }
        ab_put = await ac.put("/api/agents/agent-builder", json=ab_update)
        assert ab_put.status_code == 200

        ab_reload = await ac.get("/api/agents/agent-builder")
        assert ab_reload.status_code == 200
        assert ab_reload.json()["provider"] == "lmstudio"
        assert ab_reload.json()["model"] == "qwen2.5-coder"


@pytest.mark.asyncio
async def test_agent_builder_show_in_chat_false_despite_stale_override(app):
    """Stale agent_overrides show_in_chat=1 must not surface Agent Builder in Chat."""
    from src.domain.settings.models import AgentCustomization

    app.state.store.save_agent_override(
        AgentCustomization(agent_id="agent-builder", show_in_chat=True)
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        list_resp = await ac.get("/api/agents")
        assert list_resp.status_code == 200
        by_id = {a["id"]: a for a in list_resp.json()}
        assert "agent-builder" in by_id
        assert by_id["agent-builder"]["show_in_chat"] is False
        get_resp = await ac.get("/api/agents/agent-builder")
        assert get_resp.status_code == 200
        assert get_resp.json()["show_in_chat"] is False


@pytest.mark.asyncio
async def test_platform_agents_chat_visibility(app):
    """Platform agents assistant and autoreiv are show_in_chat=True, agent-builder is False."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        listed = {a["id"]: a for a in (await ac.get("/api/agents")).json()}
        assert listed["assistant"]["show_in_chat"] is True
        assert listed["autoreiv"]["show_in_chat"] is True
        assert listed["agent-builder"]["show_in_chat"] is False
