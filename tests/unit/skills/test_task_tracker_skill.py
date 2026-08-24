"""
Unit tests for Task Tracker Skill [REQ-AGENTS-002].
"""

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.task_tracker_skill import TaskTrackerSkill
from src.domain.agents.profiles import GENERAL_ASSISTANT_PROFILE
from src.domain.gateway.models import ToolCall
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.fixture
def skill(store):
    return TaskTrackerSkill(store=store)


def test_task_crud_direct_methods(skill):
    # 1. Create task
    t1 = skill.create_task(title="Deploy to Nimo PC", priority="high", due_date="2026-08-25")
    assert t1["id"] is not None
    assert t1["title"] == "Deploy to Nimo PC"
    assert t1["status"] == "pending"
    assert t1["priority"] == "high"

    # 2. List tasks
    pending = skill.list_tasks(status="pending")
    assert len(pending) == 1
    assert pending[0]["title"] == "Deploy to Nimo PC"

    # 3. Update status
    updated = skill.update_task_status(task_id=t1["id"], status="completed")
    assert updated["status"] == "completed"

    # 4. Filter by status
    pending_after = skill.list_tasks(status="pending")
    assert len(pending_after) == 0

    completed = skill.list_tasks(status="completed")
    assert len(completed) == 1

    # 5. Delete task
    del_res = skill.delete_task(task_id=t1["id"])
    assert del_res["success"] is True
    assert len(skill.list_tasks()) == 0


@pytest.mark.asyncio
async def test_task_tracker_registered_tool_execution(store, skill):
    registry = ScopedToolRegistry()
    skill.register_tools(registry)

    # General Assistant is authorized for task_tracker tools
    call = ToolCall(
        id="call_t1",
        name="task_tracker_create",
        arguments={"title": "Review SDLC specs", "priority": "medium"},
    )
    result = await registry.execute(call, GENERAL_ASSISTANT_PROFILE)

    assert result.success is True
    assert result.output["title"] == "Review SDLC specs"

    # List tasks via tool
    list_call = ToolCall(id="call_t2", name="task_tracker_list", arguments={})
    list_res = await registry.execute(list_call, GENERAL_ASSISTANT_PROFILE)
    assert list_res.success is True
    assert len(list_res.output) == 1
