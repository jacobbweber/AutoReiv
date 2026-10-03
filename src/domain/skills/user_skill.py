"""User agentskills.io skill catalog models [REQ-DATA-009 - REQ-DATA-011]."""

import json
from typing import Literal

from pydantic import BaseModel, Field

SKILL_DESCRIPTION_LIMIT = 200  # CARD-614 / CARD-618: about 200 characters, "when to use this skill"


def clip_description(text: str, limit: int = SKILL_DESCRIPTION_LIMIT) -> str:
    """One line, at most ``limit`` characters, cut on a word boundary (CARD-618)."""
    s = " ".join((text or "").split())
    if len(s) <= limit:
        return s
    cut = s[: limit + 1].rsplit(" ", 1)[0] if " " in s[: limit + 1] else s[:limit]
    return cut[:limit].rstrip(" ,;:-")


def yaml_scalar(text: str) -> str:
    """Quote a frontmatter value when a plain YAML scalar would break (``: ``, `` #``, leading indicator)."""
    if ": " in text or " #" in text or text[:1] in "'\"[]{}&*!|>%@`#,?:-":
        return json.dumps(text, ensure_ascii=False)
    return text


class UserSkillManifest(BaseModel):
    """Frontmatter-only catalog entry. Body and tool JSON are not loaded until activate."""

    id: str = Field(description="Skill slug relative to the skills directory")
    name: str = Field(description="agentskills.io frontmatter name")
    description: str = Field(description="agentskills.io frontmatter description")
    path: str = Field(description="Absolute or resolved path to SKILL.md")
    origin: Literal["user"] = "user"
