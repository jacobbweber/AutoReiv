"""
Domain models for Capability Gaps & Needs Training Backlog [REQ-FACT-027].
"""

from typing import Optional

from pydantic import BaseModel, Field


class CapabilityGap(BaseModel):
    """
    Records a detected capability gap or missing tool request for an agent.
    """

    id: str = Field(description="Unique capability gap identifier")
    agent_id: str = Field(description="Target agent identifier")
    session_id: Optional[str] = Field(default=None, description="Chat session where gap occurred")
    turn_text: str = Field(description="User prompt or turn instruction that failed or lacked tools")
    identified_capability: str = Field(description="Summary of missing capability")
    suggested_tool_name: Optional[str] = Field(default=None, description="Heuristically suggested tool name")
    status: str = Field(default="pending", description="Status: pending, trained, dismissed")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of creation")
