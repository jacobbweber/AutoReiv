"""
Autonomous Agent Pack Factory Typed Packets and Durable Store Domain Models [REQ-FACT-003, REQ-FACT-012].

Enforces structured, token-efficient inter-room communication between the 5 Platform Factory Agents
(Conductor, Inspector, Coder, Sandbox Runner, Critic) and durable job tracking in SQLite.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkPacket(BaseModel):
    """
    Typed envelope dispatching instructions to a factory worker [REQ-FACT-003].
    """

    goal: str = Field(description="Actionable goal statement for this phase")
    target_agent_id: str = Field(description="Slug identifier of the agent pack being authored/trained")
    facts: List[str] = Field(default_factory=list, description="Verified facts about environment, OS, services")
    constraints: List[str] = Field(
        default_factory=list, description="Safety invariants (e.g. read-only, no path traversal)"
    )
    done_when: str = Field(description="Unambiguous verification criteria")
    budget: Dict[str, Any] = Field(default_factory=dict, description="Resource bounds (max turns, timeouts)")
    target_host: Optional[str] = Field(default=None, description="Remote host / IP or None for local target")
    target_directory: Optional[str] = Field(default=None, description="Filesystem directory being inspected/mirrored")


class GapPacket(BaseModel):
    """
    Structured emission when a capability deficiency is encountered during loop execution [REQ-FACT-003].
    """

    kind: Literal["tool", "skill", "agent", "graph_edge"] = Field(description="Category of capability deficiency")
    justification: str = Field(description="Explanation of why existing tools/skills failed to achieve the goal")
    evidence: str = Field(description="Logs, error codes, or trace excerpt demonstrating the deficiency")
    suggested_signature: str = Field(description="Draft signature or interface contract for the missing capability")
    target_agent_id: str = Field(description="Slug of the agent pack that requires this capability")


class EvalPacket(BaseModel):
    """
    Evaluation results emitted across the 4-stage verification battery [REQ-FACT-003, REQ-FACT-009].
    """

    checks_executed: List[str] = Field(default_factory=list, description="List of verification stages executed")
    passed: bool = Field(description="True if all executed stages passed cleanly")
    stage_1_functional: bool = Field(default=False, description="Stage 1: Deterministic functional execution (code 0)")
    stage_2_safety: bool = Field(
        default=False, description="Stage 2: Invariant and safety guardrails (no sandbox escape)"
    )
    stage_3_idempotency: bool = Field(default=False, description="Stage 3: Idempotency and dirty input replay")
    stage_4_critic: bool = Field(default=False, description="Stage 4: SRE Critic AST audit and regex safety")
    stdout: str = Field(default="", description="Sandbox stdout capture")
    stderr: str = Field(default="", description="Sandbox stderr capture")
    critic_notes: str = Field(default="", description="Auditor feedback and recommendations")
    duration_ms: float = Field(default=0.0, description="Total execution duration across stages in ms")


class PromotePacket(BaseModel):
    """
    Sign-off packet emitted upon successful certification of an agent capability [REQ-FACT-003, REQ-FACT-014].
    """

    target_agent_id: str = Field(description="Slug of the agent pack ready for deployment or review")
    modified_files: List[str] = Field(default_factory=list, description="Relative paths of authored tools/skills")
    test_scores: Dict[str, Any] = Field(default_factory=dict, description="Stage score summary")
    critic_verdict: Literal["approved", "rejected", "conditional"] = Field(description="Critic sign-off decision")
    hitl_approval_id: Optional[str] = Field(
        default=None, description="Human-in-the-loop approval ticket ID if required"
    )
    created_at: datetime = Field(default_factory=_utc_now, description="Timestamp of promotion packet generation")


class FactoryPacket(BaseModel):
    """
    Durable database row envelope wrapping inter-room packet payloads [REQ-FACT-003].
    """

    id: str = Field(default_factory=lambda: f"fpkt_{uuid.uuid4().hex[:12]}")
    job_id: str = Field(description="Parent factory job ID")
    packet_type: Literal["work", "gap", "eval", "promote"] = Field(description="Payload type discriminator")
    sender_role: str = Field(
        description="Role emitting the packet (conductor, inspector, coder, sandbox_runner, critic)"
    )
    recipient_role: str = Field(description="Target role recipient")
    node_id: str = Field(description="Current capability graph node identifier")
    payload: Dict[str, Any] = Field(description="Serialized packet dictionary")
    created_at: datetime = Field(default_factory=_utc_now, description="Envelope creation timestamp")


class FactoryJob(BaseModel):
    """
    Durable representation of an autonomous agent training job [REQ-FACT-003, REQ-FACT-012].
    """

    id: str = Field(default_factory=lambda: f"fjob_{uuid.uuid4().hex[:12]}")
    target_agent_id: str = Field(description="Target user agent pack slug (e.g. 'game-agent')")
    session_id: str = Field(description="Originating Chat Studio session ID")
    status: Literal["queued", "running", "waiting_approval", "done", "failed", "cancelled"] = Field(default="queued")
    seed_intent: str = Field(description="Original user intent or prompt")
    target_host: Optional[str] = Field(default=None, description="Target host or IP address")
    environment_manifest_json: Optional[str] = Field(default=None, description="Serialized EnvironmentManifest")
    active_graph_id: str = Field(default="graph_standard_factory_v1", description="Active capability graph ID")
    current_node_id: str = Field(default="socratic_handshake", description="Active graph node ID")
    budget_max_cycles: int = Field(default=25, description="Maximum loop iterations permitted")
    cycles_consumed: int = Field(default=0, description="Completed loop cycles")
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class FactoryEvalRun(BaseModel):
    """
    Durable log of a 4-stage verification battery execution [REQ-FACT-009, REQ-FACT-012].
    """

    id: str = Field(default_factory=lambda: f"feval_{uuid.uuid4().hex[:12]}")
    job_id: str = Field(description="Parent factory job ID")
    tool_name: str = Field(description="Name of the tool tested")
    stage_1_functional: bool = Field(default=False)
    stage_2_safety: bool = Field(default=False)
    stage_3_idempotency: bool = Field(default=False)
    stage_4_critic: bool = Field(default=False)
    stdout_log: Optional[str] = Field(default="")
    stderr_log: Optional[str] = Field(default="")
    critic_notes: Optional[str] = Field(default="")
    duration_ms: float = Field(default=0.0)
    overall_passed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utc_now)
