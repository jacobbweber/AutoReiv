"""
Reflexion Loop Engine [REQ-VERIFY-002, REQ-VERIFY-003, REQ-VERIFY-010 - REQ-VERIFY-013].
Orchestrates autonomous self-verification and critique-guided refinement loops.
"""

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.gateway.models import ChatMessage, CompletionRequest, Role, ToolCall
from src.domain.kernel.models import AgentProfile

logger = logging.getLogger(__name__)

_CRITIC_SYSTEM = (
    "You are a strict verifier. Reply with JSON only. "
    "No markdown fences, no prose. Schema: "
    '{"is_valid": boolean, "discrepancies": [string]}. '
    "is_valid is true only if OUTPUT fully satisfies GOAL."
)


def parse_critic_payload(text: str) -> Optional[Dict[str, Any]]:
    """Extract {is_valid, discrepancies} from critic text. None if unusable."""
    if not text or not str(text).strip():
        return None
    raw = str(text).strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
    if not isinstance(parsed, dict) or "is_valid" not in parsed:
        return None
    return parsed


class ReflexionLoopEngine:
    """
    Executes multi-attempt refinement cycles guided by verification assertions
    or a builtin JSON critic. Missing checks never count as a pass.
    """

    def __init__(
        self,
        kernel: Any,
        tool_registry: ScopedToolRegistry,
    ):
        self.kernel = kernel
        self.tool_registry = tool_registry

    async def _run_builtin_critic(self, goal: str, output: str, model: str) -> Tuple[bool, List[str]]:
        if not (output or "").strip():
            return False, ["Deliverable is empty"]
        gateway = getattr(self.kernel, "gateway", None)
        if gateway is None or not hasattr(gateway, "complete"):
            return False, ["Critic unavailable: no gateway"]
        req = CompletionRequest(
            model=model or "default",
            messages=[
                ChatMessage(role=Role.SYSTEM, content=_CRITIC_SYSTEM),
                ChatMessage(
                    role=Role.USER,
                    content=f"GOAL:\n{goal}\n\nOUTPUT:\n{output}\n",
                ),
            ],
            tools=None,
            temperature=0.0,
        )
        try:
            resp = await gateway.complete(req)
            content = resp.message.content if resp and resp.message else ""
        except Exception as exc:
            logger.warning("Builtin critic failed: %s", exc)
            return False, [f"Critic execution failed: {exc}"]
        parsed = parse_critic_payload(content)
        if parsed is None:
            return False, ["Critic did not return valid JSON with is_valid"]
        discrepancies = parsed.get("discrepancies") or []
        if not isinstance(discrepancies, list):
            discrepancies = [str(discrepancies)]
        return bool(parsed.get("is_valid")), [str(item) for item in discrepancies]

    async def _run_tool_verifier(
        self,
        agent: AgentProfile,
        verifier_tool_name: str,
        verifier_args: Optional[Dict[str, Any]],
        last_output: str,
    ) -> Tuple[bool, List[str]]:
        call_args = dict(verifier_args or {})
        if "payload" not in call_args and verifier_tool_name == "assert_json_schema":
            call_args["payload"] = last_output
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
            discrepancies = verify_res.output.get("discrepancies") or []
            if not isinstance(discrepancies, list):
                discrepancies = [str(discrepancies)]
            return bool(verify_res.output.get("is_valid", False)), [str(item) for item in discrepancies]
        return False, [verify_res.error or "Verification execution failed"]

    async def run_reflexion_turn(
        self,
        agent: AgentProfile,
        session_id: str,
        user_content: str,
        verifier_tool_name: Optional[str] = None,
        verifier_args: Optional[Dict[str, Any]] = None,
        max_refinements: int = 3,
        save_to_history: bool = True,
        use_builtin_critic: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a self-verifying turn. A missing check is skipped, never a pass.
        """
        has_check = bool(verifier_tool_name) or use_builtin_critic
        critique_history: List[str] = []
        current_prompt = user_content
        last_output = ""
        model_name = "default"
        resolve = getattr(self.kernel, "_resolve_model", None)
        if callable(resolve):
            try:
                resolved = resolve(agent)
                if isinstance(resolved, str) and resolved:
                    model_name = resolved
            except Exception:
                model_name = getattr(agent, "model", None) or "default"

        for attempt in range(1, max_refinements + 1):
            logger.info("Reflexion turn attempt %s/%s for agent '%s'", attempt, max_refinements, agent.id)

            reply = await self.kernel.run_turn(
                agent=agent,
                session_id=session_id,
                user_content=current_prompt,
                save_to_history=save_to_history,
            )
            last_output = reply.content if reply else ""

            if not has_check:
                return {
                    "status": "skipped",
                    "attempts_taken": attempt,
                    "verification_passed": False,
                    "output": last_output,
                    "critique_history": critique_history,
                }

            if verifier_tool_name:
                is_valid, discrepancies = await self._run_tool_verifier(
                    agent, verifier_tool_name, verifier_args, last_output
                )
            else:
                is_valid, discrepancies = await self._run_builtin_critic(
                    user_content, last_output, model_name
                )

            if is_valid:
                return {
                    "status": "verified",
                    "attempts_taken": attempt,
                    "verification_passed": True,
                    "output": last_output,
                    "critique_history": critique_history,
                }

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
