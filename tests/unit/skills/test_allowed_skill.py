"""CARD-117: allowed_skill persist, prompt name+blurb, skill_view gating."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.kernel.agent_kernel import AgentKernel
from src.application.skills.user_catalog import LIST_USER_SKILL_PACKS, SKILL_VIEW, render_skill_index
from src.application.telemetry.collector import TelemetryCollector
from src.domain.agents.profiles import BUILTIN_PROFILES
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.settings.models import AgentCustomization
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

TICKED_MD = """---
name: user-provisioning
description: Runbook for creating and disabling user accounts.
---

# User provisioning

Body token ticked-runbook-secret.
"""

UNTICKED_MD = """---
name: okta-admin
description: Brochure seed that must not auto-enable.
---

# Okta brochure

Body token unticked-runbook-secret.
"""


def _write_pack(skills_root, slug, content):
    pack_dir = skills_root / slug
    pack_dir.mkdir(parents=True)
    (pack_dir / "SKILL.md").write_text(content, encoding="utf-8")


def _bootstrap(tmp_path, skills_dir):
    store = SQLiteStateStore(db_path=str(tmp_path / "autoreiv.db"))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)
    wiki_root = str(tmp_path / "wiki")
    return BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=wiki_root,
        skills_dir=str(skills_dir),
    ), store, telemetry


def test_builtin_allowed_skill_defaults_empty():
    for profile in BUILTIN_PROFILES:
        if profile.id == "autoreiv":
            assert profile.allowed_skill == ["build-agent-pack", "recommend-capability"]
        else:
            assert profile.allowed_skill == []


def test_render_skill_index_empty_allowlist_injects_nothing(tmp_path):
    skills_root = tmp_path / "skills"
    _write_pack(skills_root, "user-provisioning", TICKED_MD)
    _write_pack(skills_root, "okta-admin", UNTICKED_MD)
    (registry, _tool_reg), _store, _tel = _bootstrap(tmp_path, skills_root)
    catalog = registry.user_skill_catalog
    assert render_skill_index([], catalog) == ""
    assert render_skill_index(None, catalog) == ""
    assert render_skill_index(["user-provisioning"], None) == ""


def test_render_skill_index_ticked_name_blurb_not_body(tmp_path):
    skills_root = tmp_path / "skills"
    _write_pack(skills_root, "user-provisioning", TICKED_MD)
    _write_pack(skills_root, "okta-admin", UNTICKED_MD)
    (registry, _tool_reg), _store, _tel = _bootstrap(tmp_path, skills_root)
    catalog = registry.user_skill_catalog
    block = render_skill_index(["user-provisioning"], catalog)
    assert "user-provisioning" in block
    assert "creating and disabling user accounts" in block
    assert "okta-admin" not in block
    assert "Brochure seed" not in block
    assert "ticked-runbook-secret" not in block
    assert "unticked-runbook-secret" not in block
    assert "skill pack" not in block.lower()
    assert "list_user_skill_packs" not in block


def test_kernel_prompt_injects_ticked_not_unticked(tmp_path):
    skills_root = tmp_path / "skills"
    _write_pack(skills_root, "user-provisioning", TICKED_MD)
    _write_pack(skills_root, "okta-admin", UNTICKED_MD)
    (registry, tool_reg), store, telemetry = _bootstrap(tmp_path, skills_root)
    kernel = AgentKernel(
        gateway=None,
        tool_registry=tool_reg,
        state_store=store,
        telemetry=telemetry,
        user_skill_catalog=registry.user_skill_catalog,
    )
    ticked = AgentProfile(
        id="assistant-like",
        name="Assistant like",
        description="Has ticks",
        system_prompt="You are the assistant.",
        tone=AgentTone.DEFAULT,
        allowed_skill=["user-provisioning"],
    )
    msg = kernel._build_effective_system_message(ticked)
    assert "user-provisioning" in msg.content
    assert "creating and disabling user accounts" in msg.content
    assert "okta-admin" not in msg.content
    assert "ticked-runbook-secret" not in msg.content

    empty = AgentProfile(
        id="coding-like",
        name="Coding like",
        description="No ticks",
        system_prompt="You are coding.",
        tone=AgentTone.DEFAULT,
        allowed_skill=[],
    )
    empty_msg = kernel._build_effective_system_message(empty)
    assert "user-provisioning" not in empty_msg.content
    assert "okta-admin" not in empty_msg.content
    assert "Skills (runbooks) for this agent" not in empty_msg.content


def test_custom_agent_allowed_skill_persists(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "store.db"))
    store.initialize_db()
    profile = AgentProfile(
        id="okta-admin-agent",
        name="Okta Admin",
        description="Okta Admin is an agent",
        system_prompt="You help with identity admin tasks.",
        allowed_skill=["user-provisioning"],
    )
    store.save_agent_profile(profile)
    fetched = store.get_agent_profile("okta-admin-agent")
    assert fetched is not None
    assert fetched.allowed_skill == ["user-provisioning"]
    listed = store.list_custom_agent_profiles()
    assert listed[0].allowed_skill == ["user-provisioning"]


def test_builtin_override_allowed_skill_persists_across_get(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "store.db"))
    store.initialize_db()
    registry = BuiltinAgentRegistry(state_store=store)
    store.save_agent_override(
        AgentCustomization(
            agent_id="assistant",
            allowed_skill=["user-provisioning"],
        )
    )
    loaded = registry.get_agent("assistant")
    assert loaded.allowed_skill == ["user-provisioning"]
    coding = registry.get_agent("coding")
    assert coding.allowed_skill == []


@pytest.mark.asyncio
async def test_agents_api_persists_allowed_skill(tmp_path):
    store = SQLiteStateStore(db_path=":memory:")
    app = create_app(state_store=store)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_resp = await ac.post(
            "/api/agents",
            json={
                "id": "okta-admin-agent",
                "name": "Okta Admin",
                "description": "Identity admin agent",
                "system_prompt": "You help with identity admin tasks.",
                "allowed_tool_names": ["system_info"],
                "allowed_skill": ["user-provisioning"],
            },
        )
        assert create_resp.status_code == 200
        get_resp = await ac.get("/api/agents/okta-admin-agent")
        assert get_resp.status_code == 200
        assert get_resp.json()["allowed_skill"] == ["user-provisioning"]

        put_resp = await ac.put(
            "/api/agents/assistant",
            json={
                "name": "Assistant",
                "description": "Personal assistant",
                "system_prompt": "You are AutoReiv Assistant for daily work.",
                "allowed_tool_names": ["wiki_note_read"],
                "allowed_skill": ["user-provisioning"],
            },
        )
        assert put_resp.status_code == 200
        reload_resp = await ac.get("/api/agents/assistant")
        assert reload_resp.status_code == 200
        assert reload_resp.json()["allowed_skill"] == ["user-provisioning"]

        coding = (await ac.get("/api/agents/coding")).json()
        assert coding["allowed_skill"] == []


@pytest.mark.asyncio
async def test_skill_view_refuses_unticked_id(tmp_path):
    skills_root = tmp_path / "skills"
    _write_pack(skills_root, "user-provisioning", TICKED_MD)
    _write_pack(skills_root, "okta-admin", UNTICKED_MD)
    (registry, tool_reg), _store, _tel = _bootstrap(tmp_path, skills_root)

    agent = AgentProfile(
        id="assistant-like",
        name="Assistant like",
        description="Has disclosure tools",
        system_prompt="You are the assistant.",
        allowed_tool_names=[LIST_USER_SKILL_PACKS, SKILL_VIEW],
        allowed_skill=["user-provisioning"],
    )
    registry.register_profile(agent)

    refused = await tool_reg.execute(
        ToolCall(id="c1", name=SKILL_VIEW, arguments={"pack_id": "okta-admin"}),
        agent,
    )
    assert refused.success is True
    assert refused.output["success"] is False
    assert "not allowed" in (refused.output.get("error") or "").lower()
    assert "unticked-runbook-secret" not in str(refused.output)

    allowed = await tool_reg.execute(
        ToolCall(id="c2", name=SKILL_VIEW, arguments={"pack_id": "user-provisioning"}),
        agent,
    )
    assert allowed.success is True
    assert allowed.output["success"] is True
    assert "ticked-runbook-secret" in allowed.output["instructions"]

    listed = await tool_reg.execute(
        ToolCall(id="c3", name=LIST_USER_SKILL_PACKS, arguments={}),
        agent,
    )
    ids = {p["id"] for p in listed.output["packs"]}
    assert ids == {"user-provisioning"}


@pytest.mark.asyncio
async def test_skill_view_empty_allowlist_refuses_all(tmp_path):
    skills_root = tmp_path / "skills"
    _write_pack(skills_root, "user-provisioning", TICKED_MD)
    (_registry, tool_reg), _store, _tel = _bootstrap(tmp_path, skills_root)
    agent = AgentProfile(
        id="coding-like",
        name="Coding like",
        description="No skills",
        system_prompt="You are coding.",
        allowed_tool_names=[SKILL_VIEW],
        allowed_skill=[],
    )
    refused = await tool_reg.execute(
        ToolCall(id="c1", name=SKILL_VIEW, arguments={"pack_id": "user-provisioning"}),
        agent,
    )
    assert refused.output["success"] is False
    assert "not allowed" in (refused.output.get("error") or "").lower()
