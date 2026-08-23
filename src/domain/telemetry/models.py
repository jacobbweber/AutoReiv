"""
Domain models for Telemetry & Observability Spans.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, computed_field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TelemetrySpan(BaseModel):
    id: str = Field(description="Unique span ID")
    session_id: Optional[str] = Field(default=None, description="Optional associated session ID")
    agent_id: Optional[str] = Field(default=None, description="Optional associated agent ID")
    span_type: str = Field(default="turn", description="Type of span: 'turn' or 'tool'")
    name: str = Field(description="Name of operation / tool / model")
    duration_ms: float = Field(default=0.0, description="Duration in milliseconds")
    prompt_tokens: int = Field(default=0, description="Prompt tokens used")
    completion_tokens: int = Field(default=0, description="Completion tokens generated")
    success: bool = Field(default=True, description="True if operation succeeded")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context metadata")
    created_at: datetime = Field(default_factory=utc_now)

    @computed_field
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens
