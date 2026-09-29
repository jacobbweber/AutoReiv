"""User agentskills.io pack catalog models [REQ-DATA-009 - REQ-DATA-011]."""

from typing import Literal

from pydantic import BaseModel, Field


class UserSkillManifest(BaseModel):
    """Frontmatter-only catalog entry. Body and tool JSON are not loaded until activate."""

    id: str = Field(description="Pack slug relative to the skills directory")
    name: str = Field(description="agentskills.io frontmatter name")
    description: str = Field(description="agentskills.io frontmatter description")
    path: str = Field(description="Absolute or resolved path to SKILL.md")
    origin: Literal["user"] = "user"
