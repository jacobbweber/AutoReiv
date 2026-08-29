"""
Multi-Agent Handoff & Discovery Domain Models [REQ-ORCH-001, REQ-ORCH-002, REQ-ORCH-003].
Structured contracts for JIT Agent Discovery and Isolated Handoffs.
"""

import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CompactAgentCard(BaseModel):
    """
    Minimal, token-efficient summary card for JIT Agent Discovery (<60 tokens).
    """

    id: str = Field(description="Unique agent profile ID")
    name: str = Field(description="Display name of the agent")
    tone: str = Field(default="analytical", description="Persona tone")
    summary: str = Field(description="1-2 sentence capability summary")
    skills: List[str] = Field(default_factory=list, description="List of authorized skill pack tags or tools")


class HandoffEnvelope(BaseModel):
    """
    Standard Structured Inter-Agent Handoff Envelope.
    Transfers structured goal intent and context across isolated agent boundaries.
    """

    sender_agent_id: str = Field(description="Agent ID initiating the delegation")
    recipient_agent_id: str = Field(description="Specialist Agent ID receiving the delegation")
    session_id: str = Field(description="Parent conversational session ID")
    task_intent: str = Field(description="Specific subtask instruction for the specialist")
    context_payload: Dict[str, Any] = Field(
        default_factory=dict, description="Working memory facts and state variables"
    )
    correlation_id: str = Field(default_factory=lambda: uuid.uuid4().hex, description="Trace correlation identifier")
    depth: int = Field(default=1, description="Delegation recursion depth tier")
    max_turns: int = Field(default=5, description="Maximum execution turns permitted for child session")
    timeout_seconds: float = Field(default=60.0, description="Execution timeout in seconds")
    approval_mode: str = Field(default="ask", description="Parent HITL policy: ask or run [REQ-HITL-028]")


class HandoffResult(BaseModel):
    """
    Structured execution result returned by a subagent upon handoff completion.
    """

    correlation_id: str = Field(description="Trace correlation identifier from the envelope")
    sender_agent_id: str = Field(description="Original calling agent ID")
    recipient_agent_id: str = Field(description="Target specialist agent ID")
    status: Literal["completed", "failed", "rejected", "timed_out", "approval_required"] = Field(
        description="Execution lifecycle termination status"
    )
    summary: str = Field(description="Synthesized conclusion and output produced by the specialist")
    turns_used: int = Field(default=0, description="Number of ReAct turns executed")
    error_message: Optional[str] = Field(default=None, description="Error detail if execution failed or rejected")
    approval_id: Optional[str] = Field(default=None, description="Parked approval id when status is approval_required")
    parked_tool_name: Optional[str] = Field(default=None, description="Child tool that was parked")
    parked_arguments: Optional[Dict[str, Any]] = Field(default=None, description="Arguments of the parked child tool")
