"""
Multi-Agent Handoff & Discovery Domain Models [REQ-ORCH-001, REQ-ORCH-002, REQ-ORCH-003].
Structured contracts for JIT Agent Discovery and Isolated Handoffs.
Job + Phase records [REQ-ORCH-031, REQ-ORCH-032].
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


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
    max_turns: int = Field(default=10, description="Maximum execution turns permitted for child session")
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

    @property
    def success(self) -> bool:
        """True only when the child finished without failure, rejection, or timeout."""
        return self.status == "completed"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, Enum):
    """Durable job lifecycle. Linear orchestrator does not invent extra states."""

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PhaseStatus(str, Enum):
    """Durable phase lifecycle. Same locked set as JobStatus."""

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReactState(str, Enum):
    """Named ReAct overlay persisted on a phase. Kernel wiring is CARD-097."""

    THINKING = "THINKING"
    CALLING_TOOLS = "CALLING_TOOLS"
    PARKED = "PARKED"
    DONE = "DONE"
    FAILED = "FAILED"


class HandoffPacket(BaseModel):
    """
    Child user-message packet [REQ-ORCH-036]. Defined here for CARD-096 persistence.
    Child stream_turn wiring is CARD-098.
    """

    goal: str = Field(description="Isolated child/phase goal")
    facts: List[str] = Field(default_factory=list, description="Facts the child is allowed to know")
    constraints: List[str] = Field(default_factory=list, description="Hard constraints for the child")
    done_when: str = Field(description="Success rule / done_when for this packet")
    budget: Dict[str, Any] = Field(
        default_factory=dict,
        description="max_turns, max_handoffs, max_ollama_slots",
    )


class Job(BaseModel):
    """Durable parent of a user goal [REQ-ORCH-031]. Not ExecutionPlan."""

    id: str
    goal: str
    status: JobStatus = JobStatus.QUEUED
    budget_max_phases: int = 16
    budget_max_handoffs: int = 4
    budget_max_ollama_slots: int = 1
    current_phase_id: Optional[str] = None
    template_id: Optional[str] = None
    session_id: str
    agent_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: Any) -> Any:
        if isinstance(value, JobStatus):
            return value
        if isinstance(value, str):
            try:
                return JobStatus(value)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid job status {value!r}. "
                    "Allowed: queued|running|waiting_approval|done|failed|cancelled."
                ) from exc
        raise ValueError(f"Invalid job status {value!r}.")


class Phase(BaseModel):
    """Linear run unit under a job [REQ-ORCH-032]. index is the only edge."""

    id: str
    job_id: str
    name: str
    index: int = Field(ge=0, description="0-based linear order. Not a DAG edge.")
    assigned_agent_id: str
    status: PhaseStatus = PhaseStatus.QUEUED
    success_rule: str = ""
    verify_checker: Optional[str] = None
    input_packet_json: Optional[str] = None
    output_packet_json: Optional[str] = None
    parent_phase_id: Optional[str] = None
    max_turns: int = 10
    react_state: Optional[ReactState] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: Any) -> Any:
        if isinstance(value, PhaseStatus):
            return value
        if isinstance(value, str):
            try:
                return PhaseStatus(value)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid phase status {value!r}. "
                    "Allowed: queued|running|waiting_approval|done|failed|cancelled."
                ) from exc
        raise ValueError(f"Invalid phase status {value!r}.")

    @field_validator("react_state", mode="before")
    @classmethod
    def validate_react_state(cls, value: Any) -> Any:
        if value is None or value == "":
            return None
        if isinstance(value, ReactState):
            return value
        if isinstance(value, str):
            try:
                return ReactState(value)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid react_state {value!r}. "
                    "Allowed: THINKING|CALLING_TOOLS|PARKED|DONE|FAILED."
                ) from exc
        raise ValueError(f"Invalid react_state {value!r}.")


class PhaseSpec(BaseModel):
    """Planner/API input for create_job_with_phases. Linear name + success_rule only."""

    name: str
    success_rule: str = ""
    assigned_agent_id: Optional[str] = None
    verify_checker: Optional[str] = None
    max_turns: int = 10
    parent_phase_id: Optional[str] = None
