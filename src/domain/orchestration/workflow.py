"""
Workflow recipe models [CARD-123].
Reusable plan owned by the agent who starts it. Not a skill, not Goal, not a job.
"""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from src.domain.orchestration.models import utc_now


class WorkflowChapterKind(str, Enum):
    """A chapter is this agent running a skill, or a handoff to another agent."""

    SKILL = "skill"
    HANDOFF = "handoff"


class WorkflowChapter(BaseModel):
    """One chapter of a recipe. Who owns it, skill vs handoff, done-when. Not instance facts."""

    name: str
    kind: WorkflowChapterKind = WorkflowChapterKind.SKILL
    assigned_agent_id: str = ""
    skill_id: Optional[str] = None
    handoff_target_agent_id: Optional[str] = None
    success_rule: str = ""

    @field_validator("kind", mode="before")
    @classmethod
    def validate_kind(cls, value: Any) -> Any:
        if isinstance(value, WorkflowChapterKind):
            return value
        if isinstance(value, str):
            try:
                return WorkflowChapterKind(value)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid chapter kind {value!r}. Allowed: skill|handoff."
                ) from exc
        raise ValueError(f"Invalid chapter kind {value!r}.")


class Workflow(BaseModel):
    """Reusable plan. Lives on the starting agent. Instantiating creates a Job with Phase rows."""

    id: str
    name: str
    owner_agent_id: str
    chapters: List[WorkflowChapter] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
