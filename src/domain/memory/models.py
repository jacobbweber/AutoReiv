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


class SessionArtifact(BaseModel):
    id: str = Field(description="Unique artifact identifier, e.g. art_abc123")
    session_id: str = Field(description="Session this artifact belongs to")
    title: str = Field(description="Short human-readable title of artifact")
    content_type: str = Field(default="text/markdown", description="MIME type, e.g. text/markdown, application/json")
    content: str = Field(description="Full text or structured content of the artifact")
    summary: str = Field(default="", description="Concise 1-3 sentence summary")
    item_count: int = Field(default=0, description="Count of items/files processed")
    is_pinned: bool = Field(default=False, description="Whether artifact is pinned to prevent TTL expiration")
    expires_at: datetime | None = Field(default=None, description="Expiration timestamp for TTL cleanup")
    created_at: datetime = Field(default_factory=utc_now)
