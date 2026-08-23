"""
Unit tests for Planning Domain Models [REQ-PLAN-001].
"""

from src.domain.planning.models import ExecutionPlan, PlanStep, StepStatus


def test_plan_step_lifecycle():
    step = PlanStep(
        id="step_1",
        title="Inspect host system metrics",
        description="Run system_info to collect telemetry",
    )
    assert step.status == StepStatus.PENDING
    assert step.result_summary is None

    step.status = StepStatus.IN_PROGRESS
    assert step.status == StepStatus.IN_PROGRESS

    step.status = StepStatus.COMPLETED
    step.result_summary = "Host CPU load 23%, RAM 16GB healthy"
    step.duration_ms = 450.0
    assert step.status == StepStatus.COMPLETED
    assert step.duration_ms == 450.0


def test_execution_plan_validation():
    step1 = PlanStep(id="s1", title="Step 1")
    step2 = PlanStep(id="s2", title="Step 2")

    plan = ExecutionPlan(
        id="plan_101",
        goal="Audit server and backup logs",
        agent_id="general-assistant",
        session_id="sess_123",
        steps=[step1, step2],
    )

    assert plan.goal == "Audit server and backup logs"
    assert len(plan.steps) == 2
    assert plan.is_completed is False
