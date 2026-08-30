"""
Plan-and-Execute engine [REQ-PLAN-001, REQ-PLAN-002, REQ-ORCH-039, REQ-ORCH-040].
Planner is a no-tool gateway.complete call. Goal-mode store is Job+Phases, not this DTO.
"""

import json
import logging
import re
import time
import uuid
from typing import Any, Callable, List, Optional, Tuple

from src.domain.gateway.models import ChatMessage, CompletionRequest, Role
from src.domain.kernel.models import AgentProfile
from src.domain.planning.models import ExecutionPlan, PlanStep, StepStatus

logger = logging.getLogger(__name__)

_PLANNER_SYSTEM = (
    "You are AutoReiv's Planning Engine. Output JSON only. "
    "No markdown fences unless wrapping the JSON object. "
    "You have no tools. Do not call tools. Do not emit a graph or DAG."
)

_PLANNER_USER = (
    "Decompose the following user goal into 2 to 6 concrete, sequential "
    "execution phases. Linear index only. No graph edges, no depends_on.\n\n"
    "GOAL: {goal}\n\n"
    "Output ONLY a valid JSON object with this schema:\n"
    "{{\n"
    '  "phases": [\n'
    '    {{"name": "Short name of phase 1", "success_rule": "Done when ..."}},\n'
    '    {{"name": "Short name of phase 2", "success_rule": "Done when ..."}}\n'
    "  ]\n"
    "}}\n"
    "Legacy key 'steps' with title/description is also accepted."
)


class PlanAndExecuteEngine:
    """
    Formulates a linear phase list via a no-tool LLM call.
    ExecutionPlan is a DTO; persist Job+Phases at the chat/orchestrator boundary.
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
        No-tool planner [REQ-ORCH-039]. Uses gateway.complete with tools disabled.
        Does not call AgentKernel.run_turn (that path mounts tools).
        """
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        content = await self._complete_without_tools(agent, goal)
        steps = self._parse_steps_from_response(content)
        return ExecutionPlan(
            id=plan_id,
            goal=goal,
            agent_id=agent.id,
            session_id=session_id,
            steps=steps,
        )

    async def _complete_without_tools(self, agent: AgentProfile, goal: str) -> str:
        gateway = getattr(self.kernel, "gateway", None)
        if gateway is None or not hasattr(gateway, "complete"):
            raise RuntimeError("Planner requires kernel.gateway.complete with tools disabled.")
        model_name = "default"
        resolve = getattr(self.kernel, "_resolve_model", None)
        if callable(resolve):
            try:
                resolved = resolve(agent)
                if isinstance(resolved, str) and resolved:
                    model_name = resolved
            except Exception:
                model_name = getattr(agent, "model", None) or "default"
        else:
            model_name = getattr(agent, "model", None) or "default"

        req = CompletionRequest(
            model=model_name,
            messages=[
                ChatMessage(role=Role.SYSTEM, content=_PLANNER_SYSTEM),
                ChatMessage(role=Role.USER, content=_PLANNER_USER.format(goal=goal)),
            ],
            tools=None,
            temperature=0.0,
        )
        resp = await gateway.complete(req)
        if resp is None or resp.message is None:
            return ""
        return resp.message.content or ""

    def _parse_steps_from_response(self, text: str) -> List[PlanStep]:
        """Extract linear phases. Graph edges are ignored. Clamp 2-6."""
        clean = (text or "").strip()
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
        raw_json = json_match.group(1) if json_match else clean

        try:
            data = json.loads(raw_json)
            raw_steps = data.get("phases") or data.get("steps") or []
            steps: List[PlanStep] = []
            for idx, item in enumerate(raw_steps, 1):
                if not isinstance(item, dict):
                    continue
                title = item.get("name") or item.get("title") or f"Phase {idx}"
                desc = item.get("success_rule") or item.get("description") or ""
                steps.append(PlanStep(id=f"step_{idx}", title=str(title), description=str(desc)))
            if len(steps) > 6:
                steps = steps[:6]
            if steps:
                return steps
        except Exception:
            pass

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
        Sequential DTO execution for the non-streaming /api/chat/goal path.
        Stream+goal_mode uses stream_turn per persisted phase instead.
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
