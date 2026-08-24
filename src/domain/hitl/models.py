"""
HITL Domain Models [REQ-HITL-001].
Defines approval status, pending action structures, and human decision records.
"""

import time
import uuid
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    """Human-In-The-Loop action approval lifecycle states."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PendingAction(BaseModel):
    """An agent action parked for human review [REQ-HITL-001]."""

    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    risk_level: str
    agent_id: str
    session_id: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = Field(default_factory=time.time)


class ApprovalDecision(BaseModel):
    """Human decision resolving a parked action [REQ-HITL-001]."""

    action_id: str
    status: ApprovalStatus
    decided_at: float = Field(default_factory=time.time)
    reason: Optional[str] = None
