"""
Domain Models for Observability & Modern KPI Dashboard [REQ-OBS-001, REQ-OBS-002, REQ-OBS-003].
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
