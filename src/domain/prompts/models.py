"""
Domain models for Prompt Catalog [CARD-147, REQ-PROMPT-001].
"""

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class PromptItem(BaseModel):
    id: str = Field(description="Unique prompt ID, e.g. prompt_123 or builtin_sys_health")
    title: str = Field(description="Human-readable title of the prompt template")
    description: Optional[str] = Field(default="", description="Brief explanation of what the prompt achieves")
    category: str = Field(default="general", description="Category grouping, e.g. system, productivity, coding, analysis")
    template_text: str = Field(description="The prompt template content")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    is_builtin: bool = Field(default=False, description="Whether this is a seeded platform prompt")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PromptCreate(BaseModel):
    title: str = Field(description="Prompt template title")
    description: Optional[str] = Field(default="", description="Description")
    category: str = Field(default="general", description="Category")
    template_text: str = Field(description="Prompt text")
    tags: List[str] = Field(default_factory=list, description="Tags")


class PromptUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    template_text: Optional[str] = None
    tags: Optional[List[str]] = None
