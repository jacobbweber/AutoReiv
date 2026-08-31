"""Agent Pack schema. Packaging of one specialist, not a fourth primitive."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

PACK_SCHEMA_VERSION = "1.1"

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


# Chat pickers skip these by id even if a stale override has show_in_chat=1.
CHAT_HIDDEN_BY_ID = frozenset({"agent-builder", "coding", "review"})
# Conductor pack is the human-facing specialist; stale hide overrides must not win.
CHAT_SHOWN_BY_ID = frozenset({"conductor"})


def is_visible_in_chat(agent: Any) -> bool:
    """Chat picker filter. Missing field means show. Some ids are forced."""
    if agent is None:
        return True
    if isinstance(agent, dict):
        agent_id = agent.get("id")
        flag = agent.get("show_in_chat", True)
    else:
        agent_id = getattr(agent, "id", None)
        flag = getattr(agent, "show_in_chat", True)
    if agent_id in CHAT_HIDDEN_BY_ID:
        return False
    if agent_id in CHAT_SHOWN_BY_ID:
        return True
    return flag is not False


def _normalize_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    seen: List[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in seen:
            seen.append(text)
    return seen


class PackSkill(BaseModel):
    """One skill on a pack: runbook id plus the tools that belong to it."""

    id: str
    name: str = ""
    description: str = ""
    tools: List[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def validate_id_not_empty(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Skill id cannot be empty.")
        return cleaned

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_optional_str(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("tools", mode="before")
    @classmethod
    def normalize_tools(cls, value: Any) -> List[str]:
        return _normalize_str_list(value)


class AgentPackManifest(BaseModel):
    """pack.json for one specialist: identity, nested skills, pack-owned tool ids, Show in Chat."""

    schema_version: str = PACK_SCHEMA_VERSION
    id: str
    name: str
    description: str = ""
    system_prompt: str = ""
    tone: str = "default"
    purpose: str = "general"
    avatar_icon: str = "bot"
    model: str = "default"
    skills: List[PackSkill] = Field(default_factory=list)
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
        return _normalize_str_list(value)

    @model_validator(mode="after")
    def derive_compat_lists(self) -> AgentPackManifest:
        nested_ids = [skill.id for skill in self.skills if skill.id]
        if nested_ids:
            merged_ids = list(nested_ids)
            extras: List[PackSkill] = []
            for sid in self.allowed_skill:
                if sid not in merged_ids:
                    merged_ids.append(sid)
                    extras.append(PackSkill(id=sid, tools=[]))
            self.allowed_skill = merged_ids
            if extras:
                self.skills = list(self.skills) + extras
        elif self.allowed_skill:
            self.skills = [PackSkill(id=sid, tools=[]) for sid in self.allowed_skill]

        nested_tools: List[str] = []
        for skill in self.skills:
            for tool in skill.tools:
                if tool not in nested_tools:
                    nested_tools.append(tool)
        merged_tools = list(nested_tools)
        for name in self.pack_tool_names:
            if name not in merged_tools:
                merged_tools.append(name)
        self.pack_tool_names = merged_tools
        return self
