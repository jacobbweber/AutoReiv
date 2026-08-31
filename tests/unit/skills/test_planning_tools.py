"""
Unit tests for PlanningTools [REQ-PLAN-003].
"""

from src.application.skills.planning_tools import PlanningTools
from src.domain.planning.models import ExecutionPlan, PlanStep, StepStatus


def test_planning_tools_operations():
    plan = ExecutionPlan(
        id="plan_test",
        goal="Configure server",
        agent_id="linux-sysadmin",
        session_id="sess_plan",
        steps=[
            PlanStep(id="step_1", title="Check CPU"),
            PlanStep(id="step_2", title="Check RAM"),
        ],
    )

    skill = PlanningTools(active_plan=plan)

    # 1. Get active plan
    res = skill.get_active_plan()
    assert res["plan_id"] == "plan_test"
    assert len(res["steps"]) == 2

    # 2. Mark step complete
    res_step = skill.mark_plan_step_completed(step_id="step_1", summary="CPU usage normal")
    assert res_step["status"] == "updated"
    assert plan.steps[0].status == StepStatus.COMPLETED
    assert plan.steps[0].result_summary == "CPU usage normal"

    # 3. Append step
    res_app = skill.append_plan_step(title="Check Disk", description="Inspect /var partition")
    assert res_app["status"] == "appended"
    assert len(plan.steps) == 3
    assert plan.steps[2].title == "Check Disk"
