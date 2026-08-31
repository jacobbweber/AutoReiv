"""
Orchestration & Agent-to-Agent Delegation Tools [REQ-ORCH-002].
Exposes lean tools for Just-In-Time capability discovery and isolated subagent handoffs.
"""

from typing import Any, Dict, List, Optional

from src.application.gateway.generation_semaphore import (
    HandoffBatchExceedsCapError,
    get_process_generation_limit,
    validate_handoff_batch,
)
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.orchestration.directory_service import AgentDirectoryService
from src.application.orchestration.followup import propose_followup_job
from src.application.orchestration.handoff_engine import (
    HandoffIsolationEngine,
    infer_handoff_depth,
)
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.domain.orchestration.errors import HandoffPacketError, JobNotFoundError
from src.domain.orchestration.models import HandoffEnvelope, HandoffPacket


class OrchestrationTools:
    """
    Tool group providing JIT agent discovery and isolated subagent delegation.
    """

    def __init__(
        self,
        directory_service: AgentDirectoryService,
        handoff_engine: HandoffIsolationEngine,
        caller_agent_id: str = "general-assistant",
        session_id: str = "default_session",
        store: Any = None,
        orchestrator: Any = None,
    ):
        self.directory_service = directory_service
        self.handoff_engine = handoff_engine
        self.caller_agent_id = caller_agent_id
        self.session_id = session_id
        self.store = store if store is not None else getattr(directory_service, "state_store", None)
        self.orchestrator = orchestrator
        if self.orchestrator is None and self.store is not None:
            self.orchestrator = JobPhaseOrchestrator(self.store)

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
                        "description": "Clear, actionable subtask instruction for the specialist. Mapped into packet.goal when packet is omitted.",
                    },
                    "input_payload": {
                        "type": "object",
                        "description": "Optional context. Never include parent transcript. Mapped into packet facts.",
                    },
                    "packet": {
                        "type": "object",
                        "description": "Required child packet: goal, facts, constraints, done_when, budget. Child sees only this.",
                    },
                    "batch": {
                        "type": "array",
                        "description": "Optional list of handoff payloads. Errors if length > max_concurrent_generations (no silent truncate).",
                        "items": {"type": "object"},
                    },
                },
                "required": ["target_agent_id"],
            },
            handler=self.handoff_to_agent,
        )

        registry.register_tool(
            name="propose_followup",
            description=(
                "Propose a draft follow-up job from a mid-flight discovery. "
                "Creates a queued job that does NOT auto-run. A human must Approve "
                "(job stays queued) or Reject (cancelled). There is no set_goal tool."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Follow-up job goal. Required.",
                    },
                    "facts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional facts the follow-up may use.",
                    },
                    "constraints": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional hard constraints for the follow-up.",
                    },
                    "parent_job_id": {
                        "type": "string",
                        "description": "Parent job id that discovered this follow-up.",
                    },
                },
                "required": ["goal"],
            },
            handler=self.propose_followup,
        )

    def propose_followup(
        self,
        goal: str,
        facts: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        parent_job_id: Optional[str] = None,
    ) -> str:
        """
        Create a draft follow-up job/proposal. Does not auto-run [REQ-ORCH-043].
        """
        from src.application.kernel.tool_registry import get_tool_context

        if self.store is None or self.orchestrator is None:
            return (
                "=== Follow-up Proposal Failed ===\n"
                "Error: job store is unavailable. The draft was not created."
            )
        ctx = get_tool_context()
        session_id = str(ctx.get("session_id") or self.session_id)
        agent_id = str(ctx.get("agent_id") or self.caller_agent_id)
        parent = (parent_job_id or "").strip() or str(ctx.get("job_id") or "").strip() or None
        try:
            result = propose_followup_job(
                self.store,
                self.orchestrator,
                goal=goal,
                session_id=session_id,
                agent_id=agent_id,
                parent_job_id=parent,
                facts=facts,
                constraints=constraints,
            )
        except (JobNotFoundError, ValueError) as exc:
            return f"=== Follow-up Proposal Failed ===\nError: {exc}"
        return (
            "=== Follow-up Job Proposed (draft, not started) ===\n"
            f"proposal_id: {result['proposal_id']}\n"
            f"job_id: {result['job_id']}\n"
            f"approval_id: {result['approval_id']}\n"
            f"status: {result['status']}\n"
            f"job_status: {result['job_status']}\n"
            f"parent_job_id: {result['parent_job_id'] or '(none)'}\n"
            "Auto-run: no. Approve unblocks the queued job; it does not start a ReAct loop. "
            "Reject cancels it. There is no set_goal tool."
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
        packet: Optional[Dict[str, Any]] = None,
        goal: Optional[str] = None,
        facts: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        done_when: Optional[str] = None,
        budget: Optional[Dict[str, Any]] = None,
        batch: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """
        Execute an isolated delegation handoff to target agent.
        Child receives a HandoffPacket only [REQ-ORCH-036]. Batch > cap errors [REQ-ORCH-038].
        """
        from src.application.kernel.tool_registry import get_tool_context

        if batch is not None:
            try:
                validate_handoff_batch(len(batch), get_process_generation_limit())
            except HandoffBatchExceedsCapError as exc:
                return f"=== Subagent Handoff Failed ===\nError: {exc}"
            outputs = []
            for item in batch:
                if not isinstance(item, dict):
                    return (
                        "=== Subagent Handoff Failed ===\n"
                        "Error: each batch item must be an object. The batch was not truncated."
                    )
                outputs.append(await self.handoff_to_agent(**item))
            return outputs

        target = target_agent_id or target_agent
        directive = task_directive or task_intent or goal
        if not target:
            return (
                "=== Subagent Handoff Failed ===\n"
                "Error: target_agent_id is required."
            )
        ctx = get_tool_context()
        parent_mode = "run" if str(ctx.get("approval_mode") or "").strip().lower() == "run" else "ask"
        session_id = ctx.get("session_id") or self.session_id
        resolved_packet = None
        packet_error = None
        if packet is not None or any(v is not None for v in (goal, facts, constraints, done_when, budget)):
            raw = dict(packet or {})
            if goal is not None:
                raw.setdefault("goal", goal)
            elif directive:
                raw.setdefault("goal", directive)
            if facts is not None:
                raw.setdefault("facts", facts)
            if constraints is not None:
                raw.setdefault("constraints", constraints)
            missing = [
                k
                for k in ("goal", "facts", "constraints", "done_when", "budget")
                if k not in raw or raw[k] is None
            ]
            if missing:
                packet_error = (
                    "HandoffPacket missing required fields: "
                    + ", ".join(missing)
                    + ". Child was not started."
                )
            else:
                try:
                    resolved_packet = HandoffPacket.model_validate(raw)
                except Exception as exc:
                    packet_error = f"Invalid handoff packet: {exc}"
        if packet_error:
            return f"=== Subagent Handoff Failed ===\nError: {packet_error}"
        if resolved_packet is None:
            if not directive:
                return (
                    "=== Subagent Handoff Failed ===\n"
                    "Error: packet or task_directive is required."
                )
            try:
                resolved_packet = HandoffPacket.from_legacy_envelope(
                    task_intent=directive,
                    context_payload=input_payload or context_data or {},
                )
            except (HandoffPacketError, ValueError) as exc:
                return f"=== Subagent Handoff Failed ===\nError: {exc}"
        envelope = HandoffEnvelope(
            sender_agent_id=ctx.get("agent_id") or self.caller_agent_id,
            recipient_agent_id=target,
            session_id=session_id,
            task_intent=resolved_packet.goal,
            context_payload=input_payload or context_data or {},
            approval_mode=parent_mode,
            depth=infer_handoff_depth(session_id),
            packet=resolved_packet,
        )

        result = await self.handoff_engine.execute_handoff(envelope)

        if result.status == "approval_required" and result.approval_id:
            return {
                "status": "approval_required",
                "approval_id": result.approval_id,
                "tool_name": result.parked_tool_name or "tool",
                "arguments": result.parked_arguments or {},
                "message": result.error_message or result.summary,
                "recipient_agent_id": result.recipient_agent_id,
            }
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
