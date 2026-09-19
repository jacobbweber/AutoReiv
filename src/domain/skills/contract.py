"""
Domain models for Skill Capability Contracts and Mechanical Linting [CARD-363, ADR-0054].
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class VerificationKind(str, Enum):
    COMMAND = "command"
    EXIT_CODE = "exit_code"
    ASSERTION = "assertion"
    FILE_EXISTS = "file_exists"
    CHECKER = "checker"


class VerificationContract(BaseModel):
    """Deterministic completion verification contract [REQ-CAP-LINT-002]."""

    model_config = ConfigDict(extra="ignore")

    kind: VerificationKind = VerificationKind.COMMAND
    rule: str
    expected_exit_code: int = 0
    assert_pattern: Optional[str] = None


class SafetyContract(BaseModel):
    """Security boundaries and human-in-the-loop gating for a skill [REQ-CAP-LINT-003]."""

    model_config = ConfigDict(extra="ignore")

    read_only: bool = False
    requires_hitl: bool = False
    untrusted_input_allowed: bool = False


class SkillContract(BaseModel):
    """Typed representation of a compiled SKILL.md capability contract [REQ-CAP-LINT-001..005]."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: Optional[str] = None
    tier: str = "platform"
    requires_tools: List[str] = Field(default_factory=list)
    verification: Optional[VerificationContract] = None
    safety: SafetyContract = Field(default_factory=SafetyContract)
    raw_body: str = ""
    path: Optional[str] = None


class LintSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class LintViolation(BaseModel):
    """Specific diagnostic rule violation detected by the mechanical linter."""

    model_config = ConfigDict(extra="ignore")

    rule_id: str
    rule_name: str
    severity: LintSeverity
    message: str
    path: Optional[str] = None
    line_number: Optional[int] = None


class LintReport(BaseModel):
    """Summary report of capability contract linting across one or more skills."""

    model_config = ConfigDict(extra="ignore")

    scanned_count: int = 0
    valid_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    violations: List[LintViolation] = Field(default_factory=list)
    passed: bool = True
