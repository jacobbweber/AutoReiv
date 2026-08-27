"""
Delegate Subtask Skill [REQ-A2A-003].
Allows agents to hand off specialized sub-goals to other registered agent profiles.
"""

from typing import Any, Dict, Optional

from src.application.kernel.supervisor_orchestrator import SupervisorOrchestrator
from src.domain.orchestration.models import HandoffEnvelope


class DelegateSubtaskSkill:
    """Skill enabling agent-to-agent delegation via the standard 5-key A2A envelope."""

    def __init__(
        self,
        current_agent_id: str,
        session_id: str,
        orchestrator: SupervisorOrchestrator,
    ):
        self.current_agent_id = current_agent_id
        self.session_id = session_id
        self.orchestrator = orchestrator

    async def delegate_task(
        self,
        target_agent: str,
        task_intent: str,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Delegate a subtask to a specialist agent (e.g. 'sysadmin', 'librarian', 'system-agent').
        """
        envelope = HandoffEnvelope(
            sender_agent_id=self.current_agent_id,
            recipient_agent_id=target_agent,
            session_id=self.session_id,
            task_intent=task_intent,
            context_payload=context_data or {},
        )
        return await self.orchestrator.dispatch_handoff(envelope)

    def register_tools(self, registry: Any) -> None:
        """Register delegation tool on ScopedToolRegistry."""
        registry.register_tool(
            name="delegate_task",
            description="Delegate a specialized subtask to a specialist agent (e.g. 'linux-sysadmin', 'system-librarian', 'system-agent') with structured context hydration and isolated execution.",
            parameters={
                "type": "object",
                "properties": {
                    "target_agent": {
                        "type": "string",
                        "description": "Specialist Agent ID or alias receiving delegation (e.g. 'linux-sysadmin', 'system-librarian', 'system-agent')",
                    },
                    "task_intent": {
                        "type": "string",
                        "description": "Clear actionable instruction or directive for the specialist",
                    },
                    "context_data": {
                        "type": "object",
                        "description": "Optional dictionary of context variables or facts",
                    },
                },
                "required": ["target_agent", "task_intent"],
            },
            handler=self.delegate_task,
        )
