"""
Reflexion Loop Engine [REQ-VERIFY-002, REQ-VERIFY-003].
Orchestrates autonomous self-verification and critique-guided refinement loops.
"""

import logging
from typing import Any, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.kernel.models import AgentProfile

logger = logging.getLogger(__name__)


class ReflexionLoopEngine:
    """
    Executes multi-attempt refinement cycles guided by deterministic verification assertions.
    """

    def __init__(
        self,
        kernel: Any,
        tool_registry: ScopedToolRegistry,
    ):
        self.kernel = kernel
        self.tool_registry = tool_registry

    async def run_reflexion_turn(
        self,
        agent: AgentProfile,
        session_id: str,
        user_content: str,
        verifier_tool_name: Optional[str] = None,
        verifier_args: Optional[Dict[str, Any]] = None,
        max_refinements: int = 3,
        save_to_history: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a self-verifying turn with critique-guided refinement if assertions fail.
        """
        critique_history: List[str] = []
        current_prompt = user_content
        last_output = ""

        for attempt in range(1, max_refinements + 1):
            logger.info(f"Reflexion turn attempt {attempt}/{max_refinements} for agent '{agent.id}'")

            reply = await self.kernel.run_turn(
                agent=agent,
                session_id=session_id,
                user_content=current_prompt,
                save_to_history=save_to_history,
            )
            last_output = reply.content

            # If no verifier requested, pass immediately
            if not verifier_tool_name:
                return {
                    "status": "verified",
                    "attempts_taken": attempt,
                    "verification_passed": True,
                    "output": last_output,
                    "critique_history": critique_history,
                }

            # Run verifier tool
            call_args = dict(verifier_args or {})
            # If verifier takes 'payload', inject last_output
            if "payload" not in call_args and verifier_tool_name == "assert_json_schema":
                call_args["payload"] = last_output

            import uuid

            from src.domain.gateway.models import ToolCall

            agent_exec = agent.model_copy(
                update={"allowed_tool_names": list(set(agent.allowed_tool_names + [verifier_tool_name]))}
            )
            tool_call = ToolCall(
                id=f"verify_{uuid.uuid4().hex[:8]}",
                name=verifier_tool_name,
                arguments=call_args,
            )
            verify_res = await self.tool_registry.execute(tool_call, agent_exec)

            if verify_res.success and isinstance(verify_res.output, dict):
                is_valid = verify_res.output.get("is_valid", False)
                discrepancies = verify_res.output.get("discrepancies", [])
            else:
                is_valid = False
                discrepancies = [verify_res.error or "Verification execution failed"]

            if is_valid:
                return {
                    "status": "verified",
                    "attempts_taken": attempt,
                    "verification_passed": True,
                    "output": last_output,
                    "critique_history": critique_history,
                }

            # Verification failed, construct critique note
            critique = f"Attempt {attempt} verification failed with errors: {'; '.join(discrepancies)}"
            critique_history.append(critique)
            logger.warning(critique)

            if attempt < max_refinements:
                current_prompt = (
                    f"CRITIQUE ON PREVIOUS OUTPUT:\n{critique}\n\n"
                    f"Please self-correct and output a revised, fully compliant response addressing the original request:\n"
                    f"{user_content}"
                )

        return {
            "status": "unverified_budget_exhausted",
            "attempts_taken": max_refinements,
            "verification_passed": False,
            "output": last_output,
            "critique_history": critique_history,
        }
