"""
Domain models for AutoReiv Agent Kernel & Scoped Manifests.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from src.domain.settings.models import ModelPurpose


class AgentTone(str, Enum):
    CONCISE = "concise"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    ACADEMIC = "academic"
    SOCRATIC = "socratic"
    DEFAULT = "default"


class AgentProfile(BaseModel):
    id: str = Field(description="Unique agent identifier, e.g. 'general-assistant'")
    name: str = Field(description="Human readable name")
    description: str = Field(description="Summary of agent role")
    system_prompt: str = Field(description="Base persona prompt")
    purpose: ModelPurpose = Field(default=ModelPurpose.GENERAL, description="Primary purpose slot in Purpose Matrix")
    tone: AgentTone = Field(default=AgentTone.DEFAULT, description="Persona tone directive")
    avatar_icon: str = Field(default="bot", description="Avatar icon identifier")
    model: str = Field(default="default", description="Model override or purpose tag")
    allowed_tool_names: List[str] = Field(default_factory=list, description="Authorized tool IDs")
    max_turns: int = Field(default=10, ge=1, le=50, description="Max ReAct turns")
    is_builtin: bool = Field(default=False, description="True if agent is built-in baseline")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator("id")
    @classmethod
    def validate_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Agent id cannot be empty.")
        return v.strip()

    def get_effective_system_prompt(self) -> str:
        """Inject tone directive if configured."""
        base = self.system_prompt.strip()
        if self.tone == AgentTone.DEFAULT:
            return base

        tone_directives = {
            AgentTone.CONCISE: "Tone directive: Concise and direct. Avoid unnecessary preamble.",
            AgentTone.TECHNICAL: "Tone directive: Technical, precise, and authoritative.",
            AgentTone.FRIENDLY: "Tone directive: Friendly, warm, and supportive.",
            AgentTone.ACADEMIC: "Tone directive: Academic, rigorous, with cited reasoning.",
            AgentTone.SOCRATIC: "Tone directive: Socratic and guiding with clear structured options.",
        }
        directive = tone_directives.get(self.tone, f"Tone directive: {self.tone.value.capitalize()}")
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
    APPROVAL_REQUIRED = "approval_required"
    TURN_END = "turn_end"
    ERROR = "error"


class KernelEvent(BaseModel):
    event_type: KernelEventType
    content: str = Field(default="", description="Incremental text delta")
    reasoning_content: str = Field(default="", description="Incremental reasoning delta")
    tool_call: Optional[Dict[str, Any]] = Field(default=None, description="Tool invocation details")
    tool_result: Optional[ToolResult] = Field(default=None, description="Tool execution result")
    approval_id: Optional[str] = Field(default=None, description="ID of parked approval if awaiting decision")
    is_finished: bool = Field(default=False, description="True when complete")
