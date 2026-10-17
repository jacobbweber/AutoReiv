"""CARD-688 / ADR-0065 (Slice 2): Auto-scoped agents (`*`) and session-mounted skill tools on demand."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.agent_skills.allowed_tools import (
    AUTO_SKILL_WILDCARD,
    has_auto_skill_wildcard,
    pinned_skills,
    resolve_allowed_tools,
    ticked_skills,
)
from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.agora_loader import enable_skill_tool, mount_all_enabled_skill_tools
from src.application.skills.session_skills import (
    clear_session_skill_activations,
    get_session_activated_skills,
    record_session_skill_activation,
)
from src.application.skills.user_catalog import LIST_USER_SKILLS, SKILL_VIEW, UserSkillCatalog, render_skill_index
from src.domain.gateway.models import ChatMessage, CompletionResponse, Role, ToolCall
from src.domain.kernel.models import AgentProfile
from src.infrastructure.content.store import configure, reset_store
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.guard


@pytest.fixture(autouse=True)
def _clean_state():
    clear_session_skill_activations()
    yield
    clear_session_skill_activations()
    reset_store()


def _write_agora_skill(data_root: Path, skill_id: str, tool_name: str, desc: str = "Demo skill.") -> None:
    sdir = data_root / "skills" / skill_id
    (sdir / "tools").mkdir(parents=True, exist_ok=True)
    (sdir / "SKILL.md").write_text(
        f"---\nname: {skill_id.title()}\ndescription: {desc}\n---\nUse `{tool_name}` when needed.\n",
        encoding="utf-8",
    )
    (sdir / "tools" / f"{tool_name}.py").write_text(
        f'"""Run {tool_name}."""\n\nRISK = "read_only"\n\ndef run(value: int = 1) -> dict:\n    return {{"out": value * 10}}\n',
        encoding="utf-8",
    )


def test_wildcard_expands_all_non_hidden_skills_without_manual_ticking(tmp_path: Path):
    store = configure(tmp_path)
    _write_agora_skill(tmp_path, "fresh-calc", "multiply_ten", "Fresh calculator skill.")
    enable_skill_tool(store, "fresh-calc", "multiply_ten")

    reg = ScopedToolRegistry()
    for name in (*REQUIRED_PLATFORM_TOOLS, SKILL_VIEW, LIST_USER_SKILLS):
        reg.register_tool(name=name, description=name, parameters={"type": "object", "properties": {}}, handler=lambda: {})
    mount_all_enabled_skill_tools(store, reg)

    agent = AgentProfile(
        id="auto-agent",
        name="Auto Agent",
        description="Auto agent",
        system_prompt="You are an auto-scoped agent.",
        allowed_skill=[AUTO_SKILL_WILDCARD, "wiki-knowledge"],
    )
    assert has_auto_skill_wildcard(agent) is True
    assert pinned_skills(agent) == ["wiki-knowledge"]
    ticks = ticked_skills(agent)
    assert "fresh-calc" in ticks
    assert "wiki-knowledge" in ticks
    assert AUTO_SKILL_WILDCARD not in ticks

    allowed = resolve_allowed_tools(agent)
    assert "multiply_ten" in allowed


def test_auto_scoped_agent_starts_lean_and_mounts_skill_tools_on_skill_view(tmp_path: Path):
    store = configure(tmp_path)
    _write_agora_skill(tmp_path, "alpha-skill", "alpha_calc", "Alpha skill.")
    _write_agora_skill(tmp_path, "beta-skill", "beta_calc", "Beta skill.")
    enable_skill_tool(store, "alpha-skill", "alpha_calc")
    enable_skill_tool(store, "beta-skill", "beta_calc")

    reg = ScopedToolRegistry()
    for name in (*REQUIRED_PLATFORM_TOOLS,):
        reg.register_tool(name=name, description=name, parameters={"type": "object", "properties": {}}, handler=lambda: {})
    catalog = UserSkillCatalog(skills_dir=tmp_path / "skills", tool_registry=reg)
    catalog.mount_at_bootstrap()
    mount_all_enabled_skill_tools(store, reg)

    state_store = SQLiteStateStore(db_path=":memory:")
    state_store.initialize_db()
    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=reg,
        state_store=state_store,
        telemetry=MagicMock(),
        user_skill_catalog=catalog,
    )

    # Auto-scoped agent with "alpha-skill" pinned and "*" for everything else
    agent = AgentProfile(
        id="auto-agent",
        name="Auto Agent",
        description="Auto agent",
        system_prompt="You are an auto-scoped agent.",
        allowed_skill=[AUTO_SKILL_WILDCARD, "alpha-skill"],
    )

    # 1. Before opening beta-skill: active tools include alpha_calc (pinned) + base + skill_view, NOT beta_calc
    initial_tools = {t.name for t in kernel._resolve_active_tools(agent, session_id="sess-1", history=[])}
    assert "alpha_calc" in initial_tools
    assert SKILL_VIEW in initial_tools
    assert "beta_calc" not in initial_tools

    # 2. Progressive skill index lists both alpha-skill and beta-skill for "*"
    idx = render_skill_index(agent.allowed_skill, catalog=catalog, agent_id=agent.id)
    assert "alpha-skill" in idx
    assert "beta-skill" in idx

    # 3. Activate beta-skill in session "sess-1"
    record_session_skill_activation("sess-1", "beta-skill")
    assert "beta-skill" in get_session_activated_skills("sess-1")

    after_tools = {t.name for t in kernel._resolve_active_tools(agent, session_id="sess-1", history=[])}
    assert "beta_calc" in after_tools
    assert "alpha_calc" in after_tools

    # 4. Another session ("sess-2") stays lean and isolated
    other_session_tools = {t.name for t in kernel._resolve_active_tools(agent, session_id="sess-2", history=[])}
    assert "beta_calc" not in other_session_tools


@pytest.mark.asyncio
async def test_react_turn_mounts_skill_tools_on_next_step_after_skill_view(tmp_path: Path):
    store = configure(tmp_path)
    _write_agora_skill(tmp_path, "dice-skill", "roll_magic_die", "Roll a magic die.")
    enable_skill_tool(store, "dice-skill", "roll_magic_die")

    reg = ScopedToolRegistry()
    for name in (*REQUIRED_PLATFORM_TOOLS,):
        reg.register_tool(name=name, description=name, parameters={"type": "object", "properties": {}}, handler=lambda: {})
    catalog = UserSkillCatalog(skills_dir=tmp_path / "skills", tool_registry=reg)
    catalog.mount_at_bootstrap()
    mount_all_enabled_skill_tools(store, reg)

    state_store = SQLiteStateStore(db_path=":memory:")
    state_store.initialize_db()

    gateway = MagicMock()
    sent_tool_sets: list[set[str]] = []

    async def fake_complete(req):
        offered = {t.name for t in (req.tools or [])}
        sent_tool_sets.append(offered)
        step = len(sent_tool_sets)
        if step == 1:
            # Step 1: roll_magic_die is NOT offered yet; model calls skill_view("dice-skill")
            assert "roll_magic_die" not in offered
            assert "skill_view" in offered
            return CompletionResponse(
                model="test-model",
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content="",
                    tool_calls=[ToolCall(id="tc-1", name="skill_view", arguments={"skill_id": "dice-skill"})],
                ),
            )
        if step == 2:
            # Step 2: roll_magic_die IS now offered in the same turn!
            assert "roll_magic_die" in offered
            return CompletionResponse(
                model="test-model",
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content="",
                    tool_calls=[ToolCall(id="tc-2", name="roll_magic_die", arguments={"value": 7})],
                ),
            )
        return CompletionResponse(
            model="test-model",
            message=ChatMessage(role=Role.ASSISTANT, content="Rolled 70!"),
        )

    gateway.complete = AsyncMock(side_effect=fake_complete)
    telemetry = MagicMock()
    telemetry.record_turn_span.return_value = MagicMock(id="span-1")

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=reg,
        state_store=state_store,
        telemetry=telemetry,
        user_skill_catalog=catalog,
    )

    agent = AgentProfile(
        id="auto-agent",
        name="Auto Agent",
        description="Auto agent",
        system_prompt="You are an auto-scoped agent.",
        allowed_skill=[AUTO_SKILL_WILDCARD],
    )

    reply = await kernel.run_turn(
        agent=agent,
        session_id="sess-react",
        user_content="Roll the magic die",
        save_to_history=False,
        approval_mode="run",
    )
    assert "70" in (reply.content or "")
    assert len(sent_tool_sets) == 3
    assert "roll_magic_die" not in sent_tool_sets[0]
    assert "roll_magic_die" in sent_tool_sets[1]
