"""
Multi-Agent Handoff Domain Models [REQ-A2A-001].
5-Key A2A Inter-Agent Handoff Envelope for structured agent delegation.
"""

import uuid
from typing import Any, Dict

from pydantic import BaseModel, Field


class HandoffEnvelope(BaseModel):
    """
    Standard 5-Key Inter-Agent Handoff Envelope.
    Transfers structured goal intent and hydrated context across agent boundaries.
    """

    sender_agent_id: str = Field(description="Agent ID initiating the delegation")
    recipient_agent_id: str = Field(description="Specialist Agent ID receiving the delegation")
    session_id: str = Field(description="Parent conversational session ID")
    task_intent: str = Field(description="Specific subtask instruction for the specialist")
    context_payload: Dict[str, Any] = Field(
        default_factory=dict, description="Working memory facts and state variables"
    )
    correlation_id: str = Field(default_factory=lambda: uuid.uuid4().hex, description="Trace correlation identifier")
