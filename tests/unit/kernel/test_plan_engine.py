"""
Unit tests for PlanAndExecuteEngine [REQ-PLAN-001, REQ-PLAN-002, REQ-ORCH-039].
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.kernel.plan_engine import PlanAndExecuteEngine
from src.domain.gateway.models import ChatMessage, CompletionRequest, Role
from src.domain.kernel.models import AgentProfile
from src.domain.planning.models import ExecutionPlan, PlanStep, StepStatus


def _agent() -> AgentProfile:
    return AgentProfile(
        id="general-assistant",
        name="General Assistant",
        description="Planner",
        system_prompt="You are General Assistant",
    )


def _kernel_with_complete(content: str) -> MagicMock:
    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(side_effect=AssertionError("planner must not call run_turn"))
    mock_kernel._resolve_model = MagicMock(return_value="qwen3.8")
    mock_kernel.gateway.complete = AsyncMock(
        return_value=MagicMock(
            message=ChatMessage(role=Role.ASSISTANT, content=content),
        )
    )
    return mock_kernel


@pytest.mark.asyncio
async def test_formulate_plan():
    mock_kernel = _kernel_with_complete(
        "```json\n"
        "{\n"
        '  "steps": [\n'
        '    {"title": "Collect system info", "description": "Run system_info"},\n'
        '    {"title": "Export wiki doc", "description": "Write markdown note"}\n'
        "  ]\n"
        "}\n"
        "```"
    )

    engine = PlanAndExecuteEngine(kernel=mock_kernel)
    plan = await engine.formulate_plan(
        agent=_agent(),
        goal="Audit server and document in wiki",
        session_id="sess_plan_1",
    )

    assert plan.goal == "Audit server and document in wiki"
    assert len(plan.steps) == 2
    assert plan.steps[0].title == "Collect system info"
    assert plan.steps[1].title == "Export wiki doc"
    mock_kernel.run_turn.assert_not_called()


@pytest.mark.asyncio
async def test_formulate_plan_does_not_mount_tools():
    """Planner is a no-tool gateway.complete [REQ-ORCH-039]."""
    mock_kernel = _kernel_with_complete(
        '{"phases": [{"name": "Discover", "success_rule": "Files listed"}, {"name": "Report", "success_rule": "Summary written"}]}'
    )
    engine = PlanAndExecuteEngine(kernel=mock_kernel)
    await engine.formulate_plan(agent=_agent(), goal="Scan and report", session_id="sess_plan_tools")

    mock_kernel.run_turn.assert_not_called()
    mock_kernel.gateway.complete.assert_awaited()
    req = mock_kernel.gateway.complete.await_args.args[0]
    assert isinstance(req, CompletionRequest)
    assert req.tools is None


@pytest.mark.asyncio
async def test_execute_plan_sequential():
    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(
        side_effect=[
            ChatMessage(role=Role.ASSISTANT, content="System info collected: CPU 20%"),
            ChatMessage(role=Role.ASSISTANT, content="Wiki note created: /docs/server.md"),
            ChatMessage(
                role=Role.ASSISTANT, content="Goal fully achieved: Server audited and documented successfully."
            ),
        ]
    )

    engine = PlanAndExecuteEngine(kernel=mock_kernel)
    plan = ExecutionPlan(
        id="plan_exec_1",
        goal="Audit and document",
        agent_id="general-assistant",
        session_id="sess_plan_exec",
        steps=[
            PlanStep(id="step_1", title="Step 1: Telemetry"),
            PlanStep(id="step_2", title="Step 2: Wiki"),
        ],
    )

    completed_plan, final_output = await engine.execute_plan(plan=plan, agent=_agent())

    assert completed_plan.is_completed is True
    assert completed_plan.steps[0].status == StepStatus.COMPLETED
    assert completed_plan.steps[1].status == StepStatus.COMPLETED
    assert "Goal fully achieved" in final_output
