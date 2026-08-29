"""
Orchestration & Agent-to-Agent Delegation Skill [REQ-ORCH-002].
Exposes lean tools for Just-In-Time capability discovery and isolated subagent handoffs.
"""

from typing import Any, Dict, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.orchestration.directory_service import AgentDirectoryService
from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.domain.orchestration.models import HandoffEnvelope


class OrchestrationSkill:
    """
    Skill pack providing JIT agent discovery and isolated subagent delegation.
    """

    def __init__(
        self,
        directory_service: AgentDirectoryService,
        handoff_engine: HandoffIsolationEngine,
        caller_agent_id: str = "general-assistant",
        session_id: str = "default_session",
    ):
        self.directory_service = directory_service
        self.handoff_engine = handoff_engine
        self.caller_agent_id = caller_agent_id
        self.session_id = session_id

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register orchestration tools on ScopedToolRegistry."""
        registry.register_tool(
            name="lookup_agents",
            description="Search available specialist agents by natural language capability or keywords. Returns compact agent cards with IDs and summaries.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language capability search query (e.g. 'postgres dba', 'linux shell', 'specs librarian')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of candidate cards to return (default 3)",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
            handler=self.lookup_agents,
        )

        registry.register_tool(
            name="handoff_to_agent",
            description="Delegate a specialized subtask to a peer specialist agent with isolated context and bounded execution.",
            parameters={
                "type": "object",
                "properties": {
                    "target_agent_id": {
                        "type": "string",
                        "description": "Exact agent ID of the specialist recipient (e.g. 'autoreiv' or custom agent ID). Do not delegate to yourself.",
                    },
                    "task_directive": {
                        "type": "string",
                        "description": "Clear, actionable subtask instruction for the specialist",
                    },
                    "input_payload": {
                        "type": "object",
                        "description": "Optional dictionary of context variables or arguments for the subagent",
                    },
                },
                "required": ["target_agent_id", "task_directive"],
            },
            handler=self.handoff_to_agent,
        )

    def lookup_agents(self, query: str, limit: int = 3) -> str:
        """
        Query available peer agents in the platform registry.
        """
        cards = self.directory_service.search_agents(query=query, limit=limit)
        if not cards:
            return f"No specialist agents found matching query: '{query}'"

        lines = [f"Found {len(cards)} specialist agents:"]
        for card in cards:
            skills_str = ", ".join(card.skills) if card.skills else "general"
            lines.append(f"- ID: `{card.id}` | Name: {card.name} | Tone: {card.tone}")
            lines.append(f"  Summary: {card.summary}")
            lines.append(f"  Tools/Skills: {skills_str}")

        return "\n".join(lines)

    async def handoff_to_agent(
        self,
        target_agent_id: Optional[str] = None,
        task_directive: Optional[str] = None,
        input_payload: Optional[Dict[str, Any]] = None,
        target_agent: Optional[str] = None,
        task_intent: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Execute an isolated delegation handoff to target agent.
        """
        from src.application.kernel.tool_registry import get_tool_context

        target = target_agent_id or target_agent
        directive = task_directive or task_intent
        if not target or not directive:
            return (
                "=== Subagent Handoff Failed ===\n"
                "Error: target_agent_id and task_directive are required."
            )
        ctx = get_tool_context()
        envelope = HandoffEnvelope(
            sender_agent_id=ctx.get("agent_id") or self.caller_agent_id,
            recipient_agent_id=target,
            session_id=ctx.get("session_id") or self.session_id,
            task_intent=directive,
            context_payload=input_payload or context_data or {},
        )

        result = await self.handoff_engine.execute_handoff(envelope)

        if result.status == "completed":
            return (
                f"=== Subagent Handoff Completed ({result.recipient_agent_id}) ===\n"
                f"Status: {result.status} | Turns Used: {result.turns_used}\n"
                f"Conclusion:\n{result.summary}"
            )
        elif result.status == "rejected":
            return (
                f"=== Subagent Handoff Rejected ===\n"
                f"Target: {result.recipient_agent_id}\n"
                f"Reason: {result.error_message}"
            )
        else:
            return (
                f"=== Subagent Handoff Failed ===\n"
                f"Target: {result.recipient_agent_id}\n"
                f"Error: {result.error_message or 'Unknown execution failure'}"
            )
