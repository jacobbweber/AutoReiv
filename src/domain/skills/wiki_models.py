"""
Domain models for PARA-Wiki & Document Management.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class WikiNote(BaseModel):
    relative_path: str = Field(description="Relative path inside Wiki root")
    title: str = Field(description="Note title")
    category: str = Field(default="Inbox", description="PARA category: Projects, Areas, Resources, Archives, Inbox")
    tags: List[str] = Field(default_factory=list, description="Associated tags")
    frontmatter: Dict[str, Any] = Field(default_factory=dict, description="Parsed YAML frontmatter")
    body: str = Field(default="", description="Markdown body content")
