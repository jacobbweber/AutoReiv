"""
Planning Tools [REQ-PLAN-003].
Exposes dynamic plan modification tools to autonomous agents.
"""

from typing import Any, Dict, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.planning.models import ExecutionPlan, PlanStep, StepStatus


class PlanningTools:
    """Tool group exposing in-flight plan modification and tracking tools."""

    def __init__(self, active_plan: Optional[ExecutionPlan] = None):
        self.active_plan = active_plan

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register planning tools into ScopedToolRegistry."""
        registry.register_tool(
            name="get_active_plan",
            description="Retrieve the current execution plan and status of all milestones.",
            parameters={"type": "object", "properties": {}},
            handler=self.get_active_plan,
        )

        registry.register_tool(
            name="mark_plan_step_completed",
            description="Mark a specific plan step as completed with a summary of findings.",
            parameters={
                "type": "object",
                "properties": {
                    "step_id": {"type": "string", "description": "ID of the completed plan step"},
                    "summary": {"type": "string", "description": "Key outcome or findings from this step"},
                },
                "required": ["step_id", "summary"],
            },
            handler=self.mark_plan_step_completed,
        )

        registry.register_tool(
            name="append_plan_step",
            description="Dynamically append a new sub-step to the active execution plan.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short title of the new milestone step"},
                    "description": {"type": "string", "description": "Detailed instructions for the new step"},
                },
                "required": ["title"],
            },
            handler=self.append_plan_step,
        )

    def get_active_plan(self) -> Dict[str, Any]:
        """Fetch current plan state."""
        if not self.active_plan:
            return {"status": "no_active_plan", "steps": []}

        return {
            "status": "active",
            "plan_id": self.active_plan.id,
            "goal": self.active_plan.goal,
            "is_completed": self.active_plan.is_completed,
            "steps": [s.model_dump() for s in self.active_plan.steps],
        }

    def mark_plan_step_completed(self, step_id: str, summary: str) -> Dict[str, Any]:
        """Update step status to COMPLETED."""
        if not self.active_plan:
            return {"status": "error", "error": "No active plan found"}

        for step in self.active_plan.steps:
            if step.id == step_id:
                step.status = StepStatus.COMPLETED
                step.result_summary = summary
                return {"status": "updated", "step_id": step_id, "step": step.model_dump()}

        return {"status": "error", "error": f"Step '{step_id}' not found in active plan"}

    def append_plan_step(self, title: str, description: str = "") -> Dict[str, Any]:
        """Add a step to the active plan."""
        if not self.active_plan:
            return {"status": "error", "error": "No active plan found"}

        new_id = f"step_{len(self.active_plan.steps) + 1}"
        new_step = PlanStep(
            id=new_id,
            title=title,
            description=description,
            status=StepStatus.PENDING,
        )
        self.active_plan.steps.append(new_step)
        return {"status": "appended", "step": new_step.model_dump()}
