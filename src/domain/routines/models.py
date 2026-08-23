"""
Domain models for Autonomous Routines & Background Execution [REQ-ROUTINE-001].
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScheduleType(str, Enum):
    INTERVAL = "interval"
    CRON = "cron"


class RoutineStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Routine(BaseModel):
    id: str = Field(description="Unique routine identifier")
    name: str = Field(description="Human readable name")
    description: str = Field(default="", description="Detailed purpose of the routine")
    agent_id: str = Field(description="Target agent ID to execute the routine")
    prompt: str = Field(description="Autonomous prompt sent to the agent kernel")
    schedule_type: ScheduleType = Field(default=ScheduleType.INTERVAL, description="Interval or cron schedule")
    interval_seconds: int = Field(default=3600, description="Interval duration in seconds if schedule_type is interval")
    cron_expression: Optional[str] = Field(default=None, description="Cron expression if schedule_type is cron")
    enabled: bool = Field(default=True, description="Whether the routine is active")
    last_run_at: Optional[datetime] = Field(default=None, description="Timestamp of previous execution")
    next_run_at: Optional[datetime] = Field(default=None, description="Calculated next execution time")
    last_status: RoutineStatus = Field(default=RoutineStatus.IDLE, description="Status outcome of previous execution")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional custom configuration")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RoutineRun(BaseModel):
    id: str = Field(description="Unique run execution identifier")
    routine_id: str = Field(description="Associated routine ID")
    agent_id: str = Field(description="Executing agent ID")
    status: RoutineStatus = Field(description="Execution outcome")
    output: str = Field(default="", description="Assistant final message output")
    error_message: Optional[str] = Field(default=None, description="Error detail if failed")
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    created_at: datetime = Field(default_factory=utc_now)
