"""Agent Pack schema. Packaging of one specialist, not a fourth primitive."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

PACK_SCHEMA_VERSION = "1.0"

# Never copy these into a pack (instance data / secrets / tool source).
FORBIDDEN_PACK_KEYS = frozenset(
    {
        "input_packet_json",
        "output_packet_json",
        "transcripts",
        "transcript",
        "secrets",
        "secret",
        "instance_facts",
        "episodic_facts",
    }
)
SKIP_PACK_SUFFIXES = frozenset({".py", ".pyc", ".pyo", ".pyd", ".so", ".dll"})


def is_visible_in_chat(agent: Any) -> bool:
    """Chat picker filter. Missing field means show (current roster does not restripe)."""
    if agent is None:
        return True
    if isinstance(agent, dict):
        flag = agent.get("show_in_chat", True)
    else:
        flag = getattr(agent, "show_in_chat", True)
    return flag is not False


class AgentPackManifest(BaseModel):
    """pack.json for one specialist: identity, skills, pack-owned tool ids, Show in Chat."""

    schema_version: str = PACK_SCHEMA_VERSION
    id: str
    name: str
    description: str = ""
    system_prompt: str = ""
    tone: str = "default"
    purpose: str = "general"
    avatar_icon: str = "bot"
    model: str = "default"
    allowed_skill: List[str] = Field(default_factory=list)
    pack_tool_names: List[str] = Field(default_factory=list)
    show_in_chat: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator("id")
    @classmethod
    def validate_id_not_empty(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Pack id cannot be empty.")
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Pack name cannot be empty.")
        return cleaned

    @field_validator("allowed_skill", "pack_tool_names", mode="before")
    @classmethod
    def normalize_str_list(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return [str(item).strip() for item in value if str(item).strip()]
