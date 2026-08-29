"""
Isolated Subagent Handoff Execution Engine [REQ-ORCH-003].
Orchestrates isolated child execution loops with recursion depth & turn bounding.
"""

import json
import logging
from typing import Any, Callable, Optional

from src.domain.kernel.models import AgentProfile
from src.domain.orchestration.models import HandoffEnvelope, HandoffResult
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)


class HandoffIsolationEngine:
    """
    Executes subagent handoffs within isolated conversation contexts,
    enforcing anti-recursion and turn-bounded safety guards.
    """

    def __init__(
        self,
        agent_registry: BuiltinAgentRegistry,
        state_store: SQLiteStateStore,
        kernel: Optional[Any] = None,
        kernel_factory: Optional[Callable[[AgentProfile], Any]] = None,
    ):
        self.agent_registry = agent_registry
        self.state_store = state_store
        self.kernel = kernel
        self.kernel_factory = kernel_factory

    async def execute_handoff(
        self,
        envelope: HandoffEnvelope,
        on_event: Optional[Callable[[str, Any], None]] = None,
    ) -> HandoffResult:
        """
        Execute an isolated child session for the recipient specialist agent.
        """
        # 1. Guardrail: Anti-Recursion Depth Check (Max 2 tiers)
        if envelope.depth > 2:
            logger.warning(
                "Rejected handoff %s: Depth %d exceeds max allowed depth 2",
                envelope.correlation_id,
                envelope.depth,
            )
            return HandoffResult(
                correlation_id=envelope.correlation_id,
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                status="rejected",
                summary="",
                error_message="Maximum recursion depth limit of 2 tiers reached.",
            )

        alias_map = {
            "sysadmin": "autoreiv",
            "linux-sysadmin": "autoreiv",
            "system-agent": "autoreiv",
            "system": "autoreiv",
            "librarian": "assistant",
            "system-librarian": "assistant",
            "general-assistant": "assistant",
            "general": "assistant",
        }
        recipient_id = alias_map.get(envelope.recipient_agent_id, envelope.recipient_agent_id)
        sender_id = alias_map.get(envelope.sender_agent_id, envelope.sender_agent_id)

        # 2. Guardrail: Circular Self-Handoff Check
        if recipient_id == sender_id or envelope.recipient_agent_id == envelope.sender_agent_id:
            logger.warning(
                "Rejected self-handoff from agent '%s'",
                envelope.sender_agent_id,
            )
            return HandoffResult(
                correlation_id=envelope.correlation_id,
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                status="rejected",
                summary="",
                error_message="Self-handoff is forbidden to prevent circular deadlocks.",
            )

        # 3. Target Specialist Profile Resolution
        target_profile = self.agent_registry.get_agent(recipient_id) or self.agent_registry.get_profile(recipient_id)
        if not target_profile:
            logger.error("Recipient agent '%s' not found in registry", envelope.recipient_agent_id)
            return HandoffResult(
                correlation_id=envelope.correlation_id,
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                status="failed",
                summary="",
                error_message=f"Specialist agent '{envelope.recipient_agent_id}' not found in registry.",
            )

        # 4. Create Isolated Child Session ID from the live parent session
        child_session_id = f"{envelope.session_id}_child_{envelope.correlation_id[:8]}"
        if self.state_store and hasattr(self.state_store, "create_session"):
            try:
                self.state_store.create_session(
                    session_id=child_session_id,
                    agent_id=recipient_id,
                    title=f"Handoff: {envelope.task_intent[:30]}",
                )
            except Exception:
                pass

        # 5. Hydrate Isolated Context Directive
        child_prompt = f"Delegated Subtask Directive:\n{envelope.task_intent}"
        if envelope.context_payload:
            child_prompt += f"\n\nInput Context:\n{json.dumps(envelope.context_payload, indent=2)}"

        # 6. Resolve Execution Kernel
        exec_kernel = self.kernel_factory(target_profile) if self.kernel_factory else self.kernel

        if not exec_kernel:
            return HandoffResult(
                correlation_id=envelope.correlation_id,
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                status="failed",
                summary="",
                error_message="Execution kernel unavailable for handoff execution.",
            )

        # 7. Bound Turns
        bounded_profile = target_profile.model_copy()
        bounded_profile.max_turns = min(max(1, envelope.max_turns), 10)

        if on_event:
            on_event(
                "handoff_start",
                {
                    "correlation_id": envelope.correlation_id,
                    "sender": envelope.sender_agent_id,
                    "recipient": envelope.recipient_agent_id,
                    "recipient_name": target_profile.name,
                    "directive": envelope.task_intent,
                },
            )

        try:
            # Execute isolated child turn
            if hasattr(exec_kernel, "run_turn"):
                result = await exec_kernel.run_turn(
                    agent=bounded_profile,
                    session_id=child_session_id,
                    user_content=child_prompt,
                )
            elif hasattr(exec_kernel, "execute_turn"):
                result = await exec_kernel.execute_turn(
                    agent=bounded_profile,
                    session_id=child_session_id,
                    user_content=child_prompt,
                )
            else:
                raise AttributeError("Execution kernel does not implement run_turn or execute_turn")

            summary_val = getattr(result, "content", None)
            if summary_val is None or not isinstance(summary_val, str):
                summary_val = getattr(result, "output", None)
            summary_text = str(summary_val if summary_val is not None else result)
            turns_taken = getattr(result, "turns_taken", 1)
            if not isinstance(turns_taken, int):
                turns_taken = 1

            parked = None
            try:
                parsed = json.loads(summary_text)
                if isinstance(parsed, dict) and parsed.get("status") == "approval_required" and parsed.get("approval_id"):
                    parked = parsed
            except (json.JSONDecodeError, TypeError):
                parked = None

            if parked:
                if on_event:
                    on_event(
                        "handoff_complete",
                        {
                            "correlation_id": envelope.correlation_id,
                            "recipient": envelope.recipient_agent_id,
                            "recipient_name": target_profile.name,
                            "status": "approval_required",
                            "turns_used": turns_taken,
                        },
                    )
                return HandoffResult(
                    correlation_id=envelope.correlation_id,
                    sender_agent_id=envelope.sender_agent_id,
                    recipient_agent_id=envelope.recipient_agent_id,
                    status="approval_required",
                    summary=str(parked.get("message") or "Specialist parked a tool for approval."),
                    turns_used=turns_taken,
                    error_message=str(parked.get("message") or "Approval required"),
                    approval_id=str(parked.get("approval_id")),
                    parked_tool_name=parked.get("tool_name"),
                    parked_arguments=parked.get("arguments") if isinstance(parked.get("arguments"), dict) else {},
                )

            if on_event:
                on_event(
                    "handoff_complete",
                    {
                        "correlation_id": envelope.correlation_id,
                        "recipient": envelope.recipient_agent_id,
                        "recipient_name": target_profile.name,
                        "status": "completed",
                        "turns_used": turns_taken,
                    },
                )

            return HandoffResult(
                correlation_id=envelope.correlation_id,
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                status="completed",
                summary=summary_text,
                turns_used=turns_taken,
            )

        except Exception as err:
            logger.error("Handoff execution failed for %s: %s", envelope.correlation_id, err, exc_info=True)
            if on_event:
                on_event(
                    "handoff_complete",
                    {
                        "correlation_id": envelope.correlation_id,
                        "recipient": envelope.recipient_agent_id,
                        "status": "failed",
                        "error": str(err),
                    },
                )
            return HandoffResult(
                correlation_id=envelope.correlation_id,
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                status="failed",
                summary="",
                error_message=f"Subagent execution error: {str(err)}",
            )
