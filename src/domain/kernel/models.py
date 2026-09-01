"""
Domain models for AutoReiv Agent Kernel & Scoped Manifests.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from src.domain.settings.models import ModelPurpose


class AgentTone(str, Enum):
    CONCISE = "concise"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    ACADEMIC = "academic"
    SOCRATIC = "socratic"
    DEFAULT = "default"


class ToneDefinition(BaseModel):
    id: str = Field(description="Unique slug identifier for the tone, e.g. 'technical' or 'executive_briefing'")
    name: str = Field(description="Human readable name for the tone")
    description: str = Field(default="", description="Short description of the tone style")
    directive: str = Field(description="Prompt directive appended to system prompts")
    is_builtin: bool = Field(default=False, description="True if tone is a built-in platform preset")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AgentProfile(BaseModel):
    id: str = Field(description="Unique agent identifier, e.g. 'general-assistant'")
    name: str = Field(description="Human readable name")
    description: str = Field(description="Summary of agent role")
    system_prompt: str = Field(description="Base persona prompt")
    purpose: ModelPurpose = Field(default=ModelPurpose.GENERAL, description="Primary purpose slot in Purpose Matrix")
    tone: Union[AgentTone, str] = Field(default=AgentTone.DEFAULT, description="Persona tone directive")
    avatar_icon: str = Field(default="bot", description="Avatar icon identifier")
    model: str = Field(default="default", description="Model override or purpose tag")
    allowed_tool_names: List[str] = Field(default_factory=list, description="Authorized tool IDs")
    allowed_skill: List[str] = Field(
        default_factory=list,
        description="Authorized SKILL.md runbook ids for this agent",
    )
    pack_tool_names: List[str] = Field(
        default_factory=list,
        description="Tool ids that belong to this agent's pack (Agent Studio Pack-owned group)",
    )
    show_in_chat: bool = Field(
        default=True,
        description="When true, list this agent in Chat pickers. Handoff is not filtered.",
    )
    pinned_tool_names: List[str] = Field(
        default_factory=list, description="Core tools always retained in context [REQ-MCP-004]"
    )
    max_active_tools: int = Field(
        default=50, ge=1, le=50, description="Reserved. Turn time mounts the full allowlist [REQ-TOOLS-010]"
    )
    max_turns: int = Field(default=10, ge=1, le=50, description="Max ReAct turns")
    history_retention_days: int = Field(
        default=30,
        ge=0,
        description="Auto-delete chat sessions older than this many days. 0 means never [REQ-RET-001]",
    )
    is_builtin: bool = Field(default=False, description="True if agent is built-in baseline")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator("id")
    @classmethod
    def validate_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Agent id cannot be empty.")
        return v.strip()

    def get_effective_system_prompt(self, tones_lookup: Optional[Dict[str, str]] = None) -> str:
        """Inject tone directive if configured."""
        base = self.system_prompt.strip()
        tone_str = self.tone.value if hasattr(self.tone, "value") else str(self.tone).lower()
        if tone_str in (AgentTone.DEFAULT.value, "default"):
            return base

        tone_directives = {
            AgentTone.CONCISE.value: "Tone directive: Concise and direct. Avoid unnecessary preamble.",
            AgentTone.TECHNICAL.value: "Tone directive: Technical, precise, and authoritative.",
            AgentTone.FRIENDLY.value: "Tone directive: Friendly, warm, and supportive.",
            AgentTone.ACADEMIC.value: "Tone directive: Academic, rigorous, with cited reasoning.",
            AgentTone.SOCRATIC.value: "Tone directive: Socratic and guiding with clear structured options.",
        }
        if tones_lookup and tone_str in tones_lookup:
            directive = tones_lookup[tone_str]
        else:
            directive = tone_directives.get(tone_str, f"Tone directive: {tone_str.capitalize()}")
        return f"{base}\n\n{directive}"


class ToolResult(BaseModel):
    call_id: str = Field(description="Matching tool call identifier")
    tool_name: str = Field(description="Name of invoked tool")
    output: Any = Field(default=None, description="Returned payload from tool")
    success: bool = Field(default=True, description="True if execution succeeded")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    duration_ms: float = Field(default=0.0, description="Tool execution duration in ms")


class KernelEventType(str, Enum):
    TOKEN = "token"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    HANDOFF_START = "handoff_start"
    HANDOFF_COMPLETE = "handoff_complete"
    APPROVAL_REQUIRED = "approval_required"
    TURN_END = "turn_end"
    REACT_STATE = "react_state"
    ERROR = "error"


class KernelEvent(BaseModel):
    event_type: KernelEventType
    content: str = Field(default="", description="Incremental text delta")
    reasoning_content: str = Field(default="", description="Incremental reasoning delta")
    tool_call: Optional[Dict[str, Any]] = Field(default=None, description="Tool invocation details")
    tool_result: Optional[ToolResult] = Field(default=None, description="Tool execution result")
    handoff: Optional[Dict[str, Any]] = Field(default=None, description="Inter-agent handoff event details")
    approval_id: Optional[str] = Field(default=None, description="ID of parked approval if awaiting decision")
    react: Optional[Dict[str, Any]] = Field(default=None, description="Named ReAct overlay payload [REQ-KERNEL-002]")
    is_finished: bool = Field(default=False, description="True when complete")
