"""
Domain Models for Observability & Modern KPI Dashboard [REQ-OBS-001, REQ-OBS-002, REQ-OBS-003].
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# CARD-520: the remedy for "this needs a tool" is tool_escalation; the old name is read and migrated.
TOOL_ESCALATION = "tool_escalation"
LEGACY_TOOL_ESCALATION = "factory_escalation"


def normalize_remedy_kind(value: Any) -> Any:
    """Map the pre-CARD-520 remedy name to ``tool_escalation``; anything else is returned as is."""
    return TOOL_ESCALATION if value == LEGACY_TOOL_ESCALATION else value


class KPIDashboardSummary(BaseModel):
    total_turns: int = Field(default=0, description="Total completed conversation turns")
    total_prompt_tokens: int = Field(default=0, description="Sum of prompt input tokens")
    total_completion_tokens: int = Field(default=0, description="Sum of completion output tokens")
    total_tokens: int = Field(default=0, description="Total tokens consumed across all providers")
    avg_turn_duration_ms: float = Field(default=0.0, description="Mean turn latency in milliseconds")
    avg_ttft_ms: float = Field(default=0.0, description="Mean time to first token in milliseconds")
    error_count: int = Field(default=0, description="Total failed turns or errors")
    hitl_paused_count: int = Field(default=0, description="Total human-in-the-loop paused turns")
    error_rate_pct: float = Field(default=0.0, description="Error rate percentage (0.0 - 100.0)")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated total cost in USD")


class AgentKPISummary(BaseModel):
    agent_id: str = Field(description="Unique agent identifier")
    turn_count: int = Field(default=0, description="Number of turns processed by agent")
    prompt_tokens: int = Field(default=0, description="Prompt tokens consumed by agent")
    completion_tokens: int = Field(default=0, description="Completion tokens consumed by agent")
    total_tokens: int = Field(default=0, description="Total tokens consumed by agent")
    tool_call_count: int = Field(default=0, description="Number of tool calls executed by agent")
    error_count: int = Field(default=0, description="Errors encountered by agent")
    avg_duration_ms: float = Field(default=0.0, description="Average response latency in milliseconds")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated total cost in USD")


class ToolReliabilityMetric(BaseModel):
    tool_name: str = Field(description="Tool identifier/name")
    total_invocations: int = Field(default=0, description="Total times tool was called")
    success_count: int = Field(default=0, description="Successful executions")
    failure_count: int = Field(default=0, description="Failed executions or exceptions")
    success_rate_pct: float = Field(default=100.0, description="Success percentage (0.0 - 100.0)")
    avg_duration_ms: float = Field(default=0.0, description="Average execution duration in milliseconds")


class TelemetryFilter(BaseModel):
    trace_id: Optional[str] = Field(default=None, description="Filter by distributed trace identifier")
    parent_span_id: Optional[str] = Field(default=None, description="Filter by parent span identifier")
    agent_id: Optional[str] = Field(default=None, description="Filter by agent identifier")
    session_id: Optional[str] = Field(default=None, description="Filter by session identifier")
    span_type: Optional[str] = Field(default=None, description="Filter by span type (turn, llm_call, tool, etc.)")
    provider: Optional[str] = Field(default=None, description="Filter by LLM provider")
    model: Optional[str] = Field(default=None, description="Filter by model identifier")
    has_error: Optional[bool] = Field(default=None, description="Filter by error status")
    start_time: Optional[datetime] = Field(default=None, description="Start timestamp cutoff")
    end_time: Optional[datetime] = Field(default=None, description="End timestamp cutoff")


class TimeSeriesDataPoint(BaseModel):
    timestamp_bucket: str = Field(description="Time interval bucket string (e.g. YYYY-MM-DD HH:00:00)")
    token_count: int = Field(default=0, description="Total tokens consumed in bucket")
    turn_count: int = Field(default=0, description="Total turns processed in bucket")
    error_count: int = Field(default=0, description="Total errors in bucket")


class FrictionSignatureType(str, Enum):
    REDUNDANT_VERIFICATION = "redundant_verification"
    PAYLOAD_BLOAT = "payload_bloat"
    SEARCH_THRASHING = "search_thrashing"
    STALLED_TURN = "stalled_turn"


class FrictionIncident(BaseModel):
    id: str = Field(description="Unique incident ID")
    session_id: str = Field(description="Session ID where friction occurred")
    turn_index: Optional[int] = Field(default=None, description="Turn index if applicable")
    agent_id: str = Field(description="Agent exhibiting friction")
    tool_name: str = Field(description="Primary tool involved in friction")
    signature: FrictionSignatureType = Field(description="Identified friction signature")
    evidence: str = Field(description="Observable evidence description")
    payload_bytes: Optional[int] = Field(default=None, description="Payload size in bytes if payload_bloat")
    severity: str = Field(default="medium", description="Severity level: low, medium, high")
    occurred_at: Optional[datetime] = Field(default=None, description="Timestamp of incident")


class RunbookRecommendation(BaseModel):
    id: str = Field(description="Unique recommendation ID")
    agent_id: str = Field(description="Target agent ID")
    skill_id: Optional[str] = Field(default=None, description="Owning skill identifier")
    skill_path: Optional[str] = Field(default=None, description="Path to SKILL.md under user data")
    friction_type: FrictionSignatureType = Field(description="Associated friction signature")
    summary: str = Field(description="One-sentence description of the problem and proposed rule")
    proposed_patch: str = Field(description="Markdown addition for ## Common Pitfalls & Forbidden Paths")
    original_snippet: Optional[str] = Field(default=None, description="Original section context")
    remedy_kind: str = Field(default="runbook_patch", description="'runbook_patch' or 'tool_escalation' [CARD-520]")
    status: str = Field(default="pending", description="'pending', 'applied', 'dismissed', 'escalated'")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    tool_name: Optional[str] = Field(default=None, description="Tool that caused the friction [CARD-520]")
    payload_bytes: Optional[int] = Field(default=None, description="Payload size for payload bloat [CARD-520]")
    session_id: Optional[str] = Field(default=None, description="Session where the friction was seen [CARD-520]")
    developer_session_id: Optional[str] = Field(default=None, description="Developer chat opened by Ask Developer [CARD-520]")

    @field_validator("remedy_kind", mode="before")
    @classmethod
    def _legacy_remedy(cls, value: Any) -> Any:
        return normalize_remedy_kind(value)


class ArchitecturalThresholdType(str, Enum):
    """The 5 God-Agent threshold types [ADR-0054, CARD-364]."""

    TOOL_BLOAT = "tool_bloat"
    CONTEXT_TAX = "context_tax"
    SECURITY_COLLISION = "security_collision"
    LIFECYCLE_MISMATCH = "lifecycle_mismatch"
    COGNITIVE_CONFLICT = "cognitive_conflict"


class ArchitecturalAlert(BaseModel):
    """Runtime architectural threshold breach alert [CARD-364, REQ-ARCH-001..005]."""

    id: str = Field(description="Unique alert identifier")
    threshold_type: ArchitecturalThresholdType = Field(description="Architectural threshold violated")
    severity: str = Field(default="medium", description="Severity level: low, medium, high, critical")
    agent_id: str = Field(description="Agent associated with threshold violation")
    session_id: Optional[str] = Field(default=None, description="Session ID where violation occurred")
    evidence: str = Field(description="Observable evidence and metrics describing the breach")
    remediation_proposal: str = Field(description="Actionable remediation recommendation")
    occurred_at: Optional[datetime] = Field(default=None, description="Timestamp of violation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic telemetry payload")


class ArchitecturalScanReport(BaseModel):
    """Summary of architectural telemetry scan across historical sessions [CARD-364, REQ-ARCH-006]."""

    scanned_sessions: int = Field(default=0, description="Total sessions evaluated")
    scanned_spans: int = Field(default=0, description="Total turn spans inspected")
    alert_count: int = Field(default=0, description="Total architectural alerts detected")
    alerts_by_type: Dict[str, int] = Field(default_factory=dict, description="Counts broken down by threshold type")
    alerts: List[ArchitecturalAlert] = Field(default_factory=list, description="List of generated alerts")
    clean: bool = Field(default=True, description="True if zero high or critical alerts detected")


class ArchitecturalProposalType(str, Enum):
    """Actionable remediation proposal types [ADR-0054, CARD-365, REQ-ARCH-008]."""

    PROMOTION_ROUTINE = "promotion_routine"
    SKILL_DECOMPOSITION = "skill_decomposition"
    TOOL_PRUNING = "tool_pruning"
    SECURITY_ISOLATION = "security_isolation"
    CONTRACT_REINFORCEMENT = "contract_reinforcement"


class ArchitecturalProposalStatus(str, Enum):
    """Lifecycle state of an architectural proposal [CARD-365, REQ-ARCH-008]."""

    PENDING = "pending"
    APPLIED = "applied"
    DISMISSED = "dismissed"


class ArchitecturalProposal(BaseModel):
    """Actionable architectural proposal staged in Agent Forge Studio [CARD-365, REQ-ARCH-008]."""

    id: str = Field(description="Unique proposal identifier")
    alert_id: str = Field(description="Originating ArchitecturalAlert identifier")
    proposal_type: ArchitecturalProposalType = Field(description="Remediation category")
    status: ArchitecturalProposalStatus = Field(default=ArchitecturalProposalStatus.PENDING, description="Proposal lifecycle state")
    title: str = Field(description="Human-readable title describing the proposed architectural evolution")
    description: str = Field(description="Technical rationale and observable evidence context")
    agent_id: str = Field(description="Target agent identifier")
    session_id: Optional[str] = Field(default=None, description="Session ID associated with breach")
    impact_summary: str = Field(description="Observable token, latency, or security impact summary")
    action_payload: Dict[str, Any] = Field(default_factory=dict, description="Payload required to execute one-click remedy")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    applied_at: Optional[datetime] = Field(default=None, description="Timestamp when remedy was executed")
    dismissed_at: Optional[datetime] = Field(default=None, description="Timestamp when proposal was dismissed")



