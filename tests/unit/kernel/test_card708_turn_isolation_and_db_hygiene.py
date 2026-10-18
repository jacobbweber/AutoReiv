"""CARD-708: AgentKernel turn state isolation, AgentMemoryRepository schema caching, atomic save_message sequence_num, and bounded past_chat_search."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

from src.application.chat.past_chat_search import _fetch_store_rows, search_past_chats
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionResponse, Role, ToolCall
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.guard


@pytest.mark.asyncio
async def test_nested_turn_does_not_clobber_parent_turn_state(tmp_path: Path):
    """When a parent turn executes a tool that runs a nested child turn on the same AgentKernel, parent turn state must not be overwritten."""
    store = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)
    tool_reg = ScopedToolRegistry()

    parent_agent = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Parent",
        system_prompt="Parent system prompt",
        model="ollama/qwen3.8:latest",
        allowed_skill=["*"],
        memory_enabled=False,
    )
    child_agent = AgentProfile(
        id="tutor",
        name="Tutor",
        description="Child",
        system_prompt="Child system prompt",
        model="ollama/qwen3.8:latest",
        allowed_skill=["quiz-turn"],
        memory_enabled=False,
    )

    class _FakeGateway:
        def __init__(self):
            self.call_count = 0

        async def complete(self, req):
            self.call_count += 1
            if self.call_count == 1:
                # Parent step 1: invoke skill_view tool
                return CompletionResponse(
                    model=req.model,
                    message=ChatMessage(
                        role=Role.ASSISTANT,
                        content="",
                        tool_calls=[ToolCall(id="tc_1", name="skill_view", arguments={})],
                    ),
                )
            if self.call_count == 2:
                # Child turn inside skill_view
                return CompletionResponse(
                    model=req.model,
                    message=ChatMessage(role=Role.ASSISTANT, content="Child finished work."),
                )
            # Parent step 2: finishes turn
            return CompletionResponse(
                model=req.model,
                message=ChatMessage(role=Role.ASSISTANT, content="Parent finished after child."),
            )

    gateway = _FakeGateway()
    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=tool_reg,
        state_store=store,
        telemetry=telemetry,
        data_dir=str(tmp_path),
    )

    observed_parent_cap_ids_after_child = []
    observed_parent_planning_after_child = []

    async def _handoff_sim():
        # Simulate parent state before child runs
        kernel._turn_matched_capability_ids = ["parent-locked-cap"]
        kernel._turn_planning_phase = True
        kernel._ace_tool_errors = [{"tool_name": "prior_parent_tool", "error": "parent error"}]
        # Run nested child turn on the SAME kernel instance
        store.create_session(session_id="child_sess", agent_id="tutor", title="Child")
        await kernel.run_turn(agent=child_agent, session_id="child_sess", user_content="Do child task")
        return {"status": "completed"}

    tool_reg.register_tool(
        name="skill_view",
        description="Simulate subagent handoff",
        parameters={"type": "object", "properties": {}},
        handler=_handoff_sim,
    )

    orig_turn_tools = kernel._turn_tools_and_system_message

    def _spy_turn_tools(agent, user_content, history, session_id=None):
        if session_id == "parent_sess" and len(history) > 1:
            observed_parent_cap_ids_after_child.append(kernel._turn_matched_capability_ids)
            observed_parent_planning_after_child.append(kernel._turn_planning_phase)
        return orig_turn_tools(agent, user_content, history, session_id=session_id)

    kernel._turn_tools_and_system_message = _spy_turn_tools

    store.create_session(session_id="parent_sess", agent_id="autoreiv", title="Parent")
    reply = await kernel.run_turn(
        agent=parent_agent,
        session_id="parent_sess",
        user_content="Run parent",
        approval_mode="run",
    )
    assert "Parent finished after child." in reply.content
    assert observed_parent_cap_ids_after_child == [["parent-locked-cap"]]
    assert observed_parent_planning_after_child == [True]


def test_agent_memory_repository_caches_schema_init_per_db_path(tmp_path: Path):
    """Repeated initialize_schema() calls on the same existing memory.db must not re-run DDL or deactivate_short_lived_facts on every step."""
    db_file = tmp_path / "agents" / "autoreiv" / "memory.db"
    repo1 = AgentMemoryRepository(db_path=db_file)
    repo1.initialize_schema()

    repo2 = AgentMemoryRepository(db_path=db_file)
    with patch.object(AgentMemoryRepository, "deactivate_short_lived_facts") as mock_deactivate:
        repo2.initialize_schema()
        repo2.initialize_schema()
        assert mock_deactivate.call_count == 0, "initialize_schema() should be cached once DB is initialized"


def test_concurrent_save_message_produces_unique_monotonic_sequence_numbers(tmp_path: Path):
    """Concurrent save_message calls to the same session must never collide on sequence_num."""
    store = SQLiteStateStore(db_path=str(tmp_path / "seq.db"))
    store.initialize_db()
    store.create_session(session_id="race_sess", agent_id="autoreiv", title="Race")

    def _write_one(idx: int):
        store.save_message(
            session_id="race_sess",
            agent_id="autoreiv",
            message=ChatMessage(role=Role.USER, content=f"msg-{idx}"),
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_write_one, range(24)))

    conn = store._get_connection()
    try:
        rows = conn.execute(
            "SELECT sequence_num FROM messages WHERE session_id = 'race_sess' ORDER BY sequence_num ASC"
        ).fetchall()
        seq_nums = [r[0] for r in rows]
    finally:
        conn.close()

    assert len(seq_nums) == 24
    assert seq_nums == list(range(1, 25)), f"Duplicate or out-of-order sequence numbers: {seq_nums}"


def test_past_chat_search_bounds_sql_fetch_and_filters_session_and_tokens(tmp_path: Path):
    """_fetch_store_rows must push session exclusion, agent filter, token filters, and LIMIT down to SQL."""
    store = SQLiteStateStore(db_path=str(tmp_path / "chats.db"))
    store.initialize_db()
    store.create_session(session_id="s_current", agent_id="autoreiv", title="Current")
    store.create_session(session_id="s_past", agent_id="autoreiv", title="Past")

    store.save_message("s_current", "autoreiv", ChatMessage(role=Role.USER, content="orchid current session"))
    for i in range(25):
        store.save_message("s_past", "autoreiv", ChatMessage(role=Role.USER, content=f"unrelated filler line {i}"))
    store.save_message("s_past", "autoreiv", ChatMessage(role=Role.USER, content="orchid deployment port 8770"))

    rows = _fetch_store_rows(
        store,
        tokens=["orchid"],
        exclude_session_id="s_current",
        agent_id="autoreiv",
        limit=10,
    )
    assert len(rows) == 1
    assert rows[0]["session_id"] == "s_past"
    assert "orchid deployment port 8770" in rows[0]["content"]

    res = search_past_chats(
        store,
        "orchid deployment",
        current_session_id="s_current",
        agent_id="autoreiv",
    )
    assert res["success"] is True
    assert res["match_count"] == 1
    assert res["hits"][0]["session_id"] == "s_past"
