"""
Plan-and-Execute Graph Engine [REQ-PLAN-001, REQ-PLAN-002].
Deconstructs complex goals into sequential step DAGs and executes them with progress tracking.
"""

import json
import logging
import re
import time
import uuid
from typing import Any, Callable, List, Optional, Tuple

from src.domain.kernel.models import AgentProfile
from src.domain.planning.models import ExecutionPlan, PlanStep, StepStatus

logger = logging.getLogger(__name__)


class PlanAndExecuteEngine:
    """
    Formulates structured execution milestone DAGs and sequentially dispatches steps through the AgentKernel.
    """

    def __init__(self, kernel: Any):
        self.kernel = kernel

    async def formulate_plan(
        self,
        agent: AgentProfile,
        goal: str,
        session_id: str,
    ) -> ExecutionPlan:
        """
        Deconstruct a complex user goal into an ordered list of 2 to 7 structured PlanSteps.
        """
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        prompt = (
            "You are AutoReiv's Planning Engine. Decompose the following user goal into 2 to 6 "
            "concrete, sequential execution milestone steps.\n\n"
            f"GOAL: {goal}\n\n"
            "Output ONLY a valid JSON object with the following schema (no markdown, or inside ```json block):\n"
            "{\n"
            '  "steps": [\n'
            '    {"title": "Short title of step 1", "description": "Specific action/tool to run"},\n'
            '    {"title": "Short title of step 2", "description": "Specific action/tool to run"}\n'
            "  ]\n"
            "}"
        )

        reply = await self.kernel.run_turn(
            agent=agent,
            session_id=session_id,
            user_content=prompt,
            save_to_history=False,
        )

        steps = self._parse_steps_from_response(reply.content)
        return ExecutionPlan(
            id=plan_id,
            goal=goal,
            agent_id=agent.id,
            session_id=session_id,
            steps=steps,
        )

    def _parse_steps_from_response(self, text: str) -> List[PlanStep]:
        """Extract structured steps from model output JSON or fallback to heuristic lines."""
        clean = text.strip()
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
        raw_json = json_match.group(1) if json_match else clean

        try:
            data = json.loads(raw_json)
            raw_steps = data.get("steps", [])
            steps: List[PlanStep] = []
            for idx, s in enumerate(raw_steps, 1):
                title = s.get("title") or f"Step {idx}"
                desc = s.get("description", "")
                steps.append(PlanStep(id=f"step_{idx}", title=title, description=desc))
            if steps:
                return steps
        except Exception:
            pass

        # Fallback: create default 2-step plan
        return [
            PlanStep(id="step_1", title="Analyze Requirements", description="Inspect context and execute initial task"),
            PlanStep(id="step_2", title="Synthesize Results", description="Format final output and verify criteria"),
        ]

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        agent: AgentProfile,
        step_callback: Optional[Callable[[PlanStep, int, int], Any]] = None,
    ) -> Tuple[ExecutionPlan, str]:
        """
        Execute all milestone steps sequentially, updating statuses and synthesizing final output.
        """
        total_steps = len(plan.steps)
        step_summaries: List[str] = []

        for idx, step in enumerate(plan.steps, 1):
            step.status = StepStatus.IN_PROGRESS
            if step_callback:
                await step_callback(step, idx, total_steps) if callable(step_callback) else None

            start_t = time.perf_counter()
            step_prompt = (
                f"EXECUTE PLAN MILESTONE [{idx}/{total_steps}]: '{step.title}'\n"
                f"Instructions: {step.description}\n"
                f"Overall Goal: {plan.goal}\n"
                f"Previous Step Results:\n" + ("\n".join(step_summaries) if step_summaries else "None (Initial Step)")
            )

            try:
                reply = await self.kernel.run_turn(
                    agent=agent,
                    session_id=plan.session_id,
                    user_content=step_prompt,
                )
                step.status = StepStatus.COMPLETED
                step.result_summary = reply.content
                step.duration_ms = (time.perf_counter() - start_t) * 1000
                step_summaries.append(f"[{step.title}]: {reply.content}")
            except Exception as e:
                step.status = StepStatus.FAILED
                step.result_summary = f"Error: {e}"
                step.duration_ms = (time.perf_counter() - start_t) * 1000
                logger.error(f"Plan step {step.id} failed: {e}")
                step_summaries.append(f"[{step.title} FAILED]: {e}")

        # Final Synthesis Turn
        synthesis_prompt = (
            f"All {total_steps} plan milestones have executed for GOAL: '{plan.goal}'.\n\n"
            "Summary of Milestones Executed:\n" + "\n".join(step_summaries) + "\n\n"
            "Please provide a final, comprehensive executive briefing summarizing the completed goal."
        )

        synthesis_reply = await self.kernel.run_turn(
            agent=agent,
            session_id=plan.session_id,
            user_content=synthesis_prompt,
        )

        plan.is_completed = all(s.status == StepStatus.COMPLETED for s in plan.steps)
        return plan, synthesis_reply.content
