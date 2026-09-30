"""CARD-523: handoff_to_agent accepts agent_id/task; a child that hits its step limit is reported incomplete with the
real turn count; {"raw": "<json>"} arguments are unwrapped; skill_view takes common aliases; the skill index shows ids."""

from types import SimpleNamespace

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.kernel.turn_limit import turn_limit_reply
from src.application.orchestration.directory_service import AgentDirectoryService
from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.application.skills.orchestration_tools import OrchestrationTools
from src.application.skills.user_catalog import UserSkillCatalog, _first_skill, render_skill_index
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile, KernelEvent, KernelEventType
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_skills.catalog import platform_pack_profile


class ChildKernel:
    def __init__(self, steps=1, text="Done: sensors read."):
        self.steps, self.text, self.calls = steps, text, []

    async def stream_turn(self, agent, session_id, user_content=None, approval_mode="ask", resume=False, **kw):
        self.calls.append({"agent": agent.id, "user_content": user_content})
        for i in range(self.steps):
            yield KernelEvent(
                event_type=KernelEventType.REACT_STATE, react={"react_state": "calling_tools", "turn_idx": i}
            )
        if self.steps >= agent.max_turns:
            yield KernelEvent(
                event_type=KernelEventType.REACT_STATE, react={"react_state": "failed", "turn_idx": agent.max_turns}
            )
        yield KernelEvent(event_type=KernelEventType.TOKEN, content=self.text)
        yield KernelEvent(event_type=KernelEventType.TURN_END, content=self.text, is_finished=True)


def _agent(*names):
    return AgentProfile(
        id="autoreiv",
        name="A",
        description="d",
        system_prompt="s",
        model="mock/m",
        allowed_skill=[f"tool:{n}" for n in names],
        max_turns=10,
    )


def _tools(tmp_path, kernel):
    store = SQLiteStateStore(db_path=tmp_path / "s.db")
    registry = BuiltinAgentRegistry(state_store=store)
    registry.register_profile(platform_pack_profile("direct"))
    registry.register_profile(platform_pack_profile("autoreiv"))
    directory = AgentDirectoryService(agent_registry=registry, state_store=store)
    engine = HandoffIsolationEngine(agent_registry=registry, state_store=store, kernel_factory=lambda p: kernel)
    return OrchestrationTools(
        directory_service=directory, handoff_engine=engine, caller_agent_id="autoreiv", session_id="sess_523"
    )


@pytest.mark.asyncio
async def test_handoff_accepts_agent_id_and_task_aliases(tmp_path):
    kernel = ChildKernel()
    out = await _tools(tmp_path, kernel).handoff_to_agent(agent_id="direct", task="Read the IPMI sensors")
    assert "Handoff Completed (direct)" in str(out)
    assert kernel.calls and kernel.calls[0]["agent"] == "direct"
    assert "Read the IPMI sensors" in kernel.calls[0]["user_content"]


@pytest.mark.asyncio
async def test_handoff_aliases_pass_the_registry_argument_check(tmp_path):
    kernel = ChildKernel()
    tools = _tools(tmp_path, kernel)
    reg = ScopedToolRegistry()
    reg.register_tool(
        name="handoff_to_agent",
        description="h",
        handler=tools.handoff_to_agent,
        parameters={"type": "object", "properties": {"target_agent_id": {"type": "string"}}},
    )
    res = await reg.execute(
        ToolCall(id="c1", name="handoff_to_agent", arguments={"agent_id": "direct", "task": "Read sensors"}),
        _agent("handoff_to_agent"),
        approval_mode="run",
    )
    assert res.success, res.error
    assert kernel.calls


@pytest.mark.asyncio
async def test_child_at_its_step_limit_is_reported_incomplete_with_real_turns(tmp_path):
    kernel = ChildKernel()
    tools = _tools(tmp_path, kernel)
    max_turns = None

    async def probe(agent, **kw):
        nonlocal max_turns
        max_turns = agent.max_turns
        kernel.steps = agent.max_turns
        kernel.text = turn_limit_reply("Listed the folder; README is left.", agent.max_turns)
        async for ev in ChildKernel.stream_turn(kernel, agent, **kw):
            yield ev

    kernel.stream_turn = probe
    out = str(await tools.handoff_to_agent(target_agent_id="direct", task_directive="Read files"))
    assert "Handoff Incomplete (direct)" in out
    assert "Status: completed" not in out
    assert f"Turns Used: {max_turns}" in out
    assert "README is left" in out


@pytest.mark.asyncio
async def test_completed_handoff_reports_real_turn_count(tmp_path):
    out = str(await _tools(tmp_path, ChildKernel(steps=3)).handoff_to_agent(target_agent_id="direct", task="x"))
    assert "Handoff Completed" in out and "Turns Used: 3" in out


@pytest.mark.asyncio
async def test_raw_json_arguments_are_unwrapped():
    seen = []

    def ask_clarification(question):
        seen.append(question)
        return {"status": "clarification_requested", "question": question}

    reg = ScopedToolRegistry()
    reg.register_tool(
        name="ask_clarification",
        description="a",
        handler=ask_clarification,
        parameters={"type": "object", "properties": {"question": {"type": "string"}}},
    )
    res = await reg.execute(
        ToolCall(id="c1", name="ask_clarification", arguments={"raw": '{"question": "Which host?"}'}),
        _agent("ask_clarification"),
        approval_mode="run",
    )
    assert res.success and seen == ["Which host?"]


@pytest.mark.asyncio
async def test_raw_is_left_alone_for_a_tool_that_takes_raw_and_for_non_json():
    got = []
    reg = ScopedToolRegistry()
    reg.register_tool(
        name="echo",
        description="e",
        handler=lambda raw: got.append(raw) or raw,
        parameters={"type": "object", "properties": {"raw": {"type": "string"}}},
    )
    await reg.execute(
        ToolCall(id="c1", name="echo", arguments={"raw": '{"a": 1}'}), _agent("echo"), approval_mode="run"
    )
    assert got == ['{"a": 1}']

    def q(question):
        return question

    reg.register_tool(
        name="q",
        description="q",
        handler=q,
        parameters={"type": "object", "properties": {"question": {"type": "string"}}},
    )
    res = await reg.execute(
        ToolCall(id="c2", name="q", arguments={"raw": "not json"}), _agent("q"), approval_mode="run"
    )
    assert not res.success and "Unknown: raw" in res.error


@pytest.mark.parametrize(
    "value,expected",
    [
        (["agent-authoring", "x"], "agent-authoring"),
        ("['agent-authoring', 'coding']", "agent-authoring"),
        ('["agent-authoring"]', "agent-authoring"),
        ("agent-authoring", "agent-authoring"),
        (None, ""),
    ],
)
def test_first_skill(value, expected):
    assert _first_skill(value) == expected


@pytest.mark.parametrize(
    "kw",
    [
        {"skill_name": "wiki_tasks"},
        {"id": "wiki_tasks"},
        {"name": "wiki_tasks"},
        {"skills": "['wiki_tasks']"},
        {"skill_id": "wiki_tasks"},
    ],
)
def test_skill_view_aliases(kw):
    cat = UserSkillCatalog.__new__(UserSkillCatalog)
    cat._allowed_skill_ids_for_current_agent = lambda: {"wiki_tasks"}
    cat.load_body = lambda sid: {"success": True, "id": sid}
    cat.record_skill_use = lambda sid: None
    assert cat.skill_view(**kw) == {"success": True, "id": "wiki_tasks"}


def test_skill_view_without_any_id_explains():
    cat = UserSkillCatalog.__new__(UserSkillCatalog)
    cat._allowed_skill_ids_for_current_agent = lambda: None
    out = cat.skill_view()
    assert out["success"] is False and "skill_id" in out["error"]


def test_skill_index_shows_the_id_next_to_the_name():
    manifest = SimpleNamespace(id="wiki_tasks", name="Weekly work logs", description="Log the week.")
    same = SimpleNamespace(id="coding", name="coding", description="")
    catalog = SimpleNamespace(list_manifests=lambda: [manifest, same])
    text = render_skill_index(["wiki_tasks", "coding"], catalog=catalog)
    assert "- Weekly work logs (id: wiki_tasks): Log the week." in text
    assert "- coding" in text and "(id: coding)" not in text
