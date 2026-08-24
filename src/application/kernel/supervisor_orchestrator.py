"""
Supervisor Orchestrator [REQ-A2A-002, REQ-A2A-004].
Coordinates multi-agent task delegations, context hydration, and response aggregation.
"""

import time
from typing import Any, Dict

from src.application.kernel.agent_kernel import AgentKernel
from src.application.telemetry.collector import TelemetryCollector
from src.domain.orchestration.models import HandoffEnvelope
from src.infrastructure.agents.registry import BuiltinAgentRegistry


class SupervisorOrchestrator:
    """Orchestrates inter-agent delegation and specialist dispatch."""

    def __init__(
        self,
        agent_registry: BuiltinAgentRegistry,
        agent_kernel: AgentKernel,
        telemetry: TelemetryCollector,
    ):
        self.agent_registry = agent_registry
        self.agent_kernel = agent_kernel
        self.telemetry = telemetry

    async def dispatch_handoff(self, envelope: HandoffEnvelope) -> Dict[str, Any]:
        """Dispatch subtask to target specialist agent with hydrated context."""
        start_time = time.perf_counter()
        recipient_id = envelope.recipient_agent_id
        if recipient_id == "sysadmin":
            recipient_id = "linux-sysadmin"
        target_agent = self.agent_registry.get_profile(recipient_id)
        if not target_agent:
            duration_ms = (time.perf_counter() - start_time) * 1000
            err_msg = f"Specialist agent '{envelope.recipient_agent_id}' not found."
            self.telemetry.record_handoff_span(
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                session_id=envelope.session_id,
                correlation_id=envelope.correlation_id,
                duration_ms=duration_ms,
                success=False,
                error_message=err_msg,
            )
            return {
                "status": "error",
                "error": err_msg,
                "sender_agent_id": envelope.sender_agent_id,
                "recipient_agent_id": envelope.recipient_agent_id,
                "correlation_id": envelope.correlation_id,
            }

        # Hydrate prompt with context payload
        hydrated_prompt = envelope.task_intent
        if envelope.context_payload:
            context_summary = "\n".join(f"- {k}: {v}" for k, v in envelope.context_payload.items())
            hydrated_prompt = f"{envelope.task_intent}\n\n[Delegated Context]:\n{context_summary}"

        # Ensure session exists in state store
        if hasattr(self.agent_kernel, "state_store") and self.agent_kernel.state_store:
            try:
                self.agent_kernel.state_store.create_session(
                    session_id=envelope.session_id,
                    agent_id=envelope.recipient_agent_id,
                    title=f"Delegation: {envelope.task_intent[:30]}",
                )
            except Exception:
                pass

        try:
            res_msg = await self.agent_kernel.run_turn(
                agent=target_agent,
                session_id=envelope.session_id,
                user_content=hydrated_prompt,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.telemetry.record_handoff_span(
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                session_id=envelope.session_id,
                correlation_id=envelope.correlation_id,
                duration_ms=duration_ms,
                success=True,
                metadata={"task_intent": envelope.task_intent},
            )
            return {
                "status": "success",
                "output": res_msg.content,
                "sender_agent_id": envelope.sender_agent_id,
                "recipient_agent_id": envelope.recipient_agent_id,
                "correlation_id": envelope.correlation_id,
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.telemetry.record_handoff_span(
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                session_id=envelope.session_id,
                correlation_id=envelope.correlation_id,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e),
            )
            return {
                "status": "error",
                "error": str(e),
                "sender_agent_id": envelope.sender_agent_id,
                "recipient_agent_id": envelope.recipient_agent_id,
                "correlation_id": envelope.correlation_id,
            }
