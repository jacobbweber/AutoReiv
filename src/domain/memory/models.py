"""
Domain models for Conversation Memory & Sessions.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Session(BaseModel):
    id: str = Field(description="Unique session identifier")
    agent_id: str = Field(description="Agent associated with this session")
    title: str = Field(default="New Conversation", description="Session title")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
