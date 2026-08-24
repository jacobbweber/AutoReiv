"""
Safety Domain Models [REQ-GUARD-001].
Defines risk levels, safety violation structures, and command safety evaluation reports.
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk severity classifications for command execution and safety evaluation."""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SafetyViolation(BaseModel):
    """Specific security or safety rule violation [REQ-GUARD-001]."""

    rule_id: str
    risk_level: RiskLevel
    reason: str
    matched_pattern: str


class CommandSafetyReport(BaseModel):
    """Aggregate safety analysis report for an evaluated command [REQ-GUARD-001]."""


    command: str
    is_safe: bool
    highest_risk: RiskLevel
    violations: List[SafetyViolation] = Field(default_factory=list)
