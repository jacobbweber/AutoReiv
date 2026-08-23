"""
Planning Domain Models [REQ-PLAN-001].
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanStep(BaseModel):
    id: str
    title: str
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    result_summary: Optional[str] = None
    duration_ms: Optional[float] = None


class ExecutionPlan(BaseModel):
    id: str
    goal: str
    agent_id: str
    session_id: str
    steps: List[PlanStep] = Field(default_factory=list)
    is_completed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
