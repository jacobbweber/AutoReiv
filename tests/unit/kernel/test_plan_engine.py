"""
Unit tests for PlanAndExecuteEngine [REQ-PLAN-001, REQ-PLAN-002].
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.kernel.plan_engine import PlanAndExecuteEngine
from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import AgentProfile
from src.domain.planning.models import ExecutionPlan, PlanStep, StepStatus


@pytest.mark.asyncio
async def test_formulate_plan():
    mock_kernel = MagicMock()
    # LLM returns structured JSON plan decomposition
    mock_kernel.run_turn = AsyncMock(
        return_value=ChatMessage(
            role=Role.ASSISTANT,
            content=(
                "```json\n"
                "{\n"
                '  "steps": [\n'
                '    {"title": "Collect system info", "description": "Run system_info"},\n'
                '    {"title": "Export wiki doc", "description": "Write markdown note"}\n'
                "  ]\n"
                "}\n"
                "```"
            ),
        )
    )

    engine = PlanAndExecuteEngine(kernel=mock_kernel)
    agent = AgentProfile(
        id="general-assistant",
        name="General Assistant",
        description="Planner",
        system_prompt="You are General Assistant",
    )

    plan = await engine.formulate_plan(
        agent=agent,
        goal="Audit server and document in wiki",
        session_id="sess_plan_1",
    )

    assert plan.goal == "Audit server and document in wiki"
    assert len(plan.steps) == 2
    assert plan.steps[0].title == "Collect system info"
    assert plan.steps[1].title == "Export wiki doc"


@pytest.mark.asyncio
async def test_execute_plan_sequential():
    mock_kernel = MagicMock()
    # Step 1 execution, Step 2 execution, Final synthesis
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
    agent = AgentProfile(
        id="general-assistant",
        name="General Assistant",
        description="Planner",
        system_prompt="You are General Assistant",
    )

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

    completed_plan, final_output = await engine.execute_plan(plan=plan, agent=agent)

    assert completed_plan.is_completed is True
    assert completed_plan.steps[0].status == StepStatus.COMPLETED
    assert completed_plan.steps[1].status == StepStatus.COMPLETED
    assert "Goal fully achieved" in final_output
