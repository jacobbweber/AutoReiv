"""
Wiki Application Service [REQ-WIKI-001, REQ-WIKI-005].
Orchestrates high-level Wiki operations for web endpoints and agent skills.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.domain.wiki.store import WikiStore


class WikiService:
    """
    Application service managing document operations against the local-first WikiStore.
    """

    def __init__(self, wiki_root: str | Path = "data/wiki"):
        self.store = WikiStore(root_dir=wiki_root)
        self.store.scaffold()

    def get_tree(self) -> Dict[str, Any]:
        """Return hierarchical category and topic navigation tree."""
        return self.store.get_tree()

    def get_note(self, relative_path: str) -> Dict[str, Any]:
        """Read note and parse YAML frontmatter and body."""
        return self.store.read_note(relative_path)

    def create_note(
        self,
        title: str,
        content: str,
        domain: str = "general",
        topic: str = "general",
        category: str = "notes",
        inbox_priority: str = "need_to_do",
        document_type: str = "atomic_note",
        tags: Optional[List[str]] = None,
        summary: str = "",
        status: str = "draft",
        priority: str = "medium",
        sensitivity: str = "internal",
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create and save a new note."""
        return self.store.file_note(
            title=title,
            content=content,
            domain=domain,
            topic=topic,
            category=category,
            inbox_priority=inbox_priority,
            document_type=document_type,
            tags=tags,
            summary=summary,
            status=status,
            priority=priority,
            sensitivity=sensitivity,
            extra_meta=extra_meta,
        )

    def update_note(
        self,
        relative_path: str,
        content: str,
        update_frontmatter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Non-destructively update an existing note."""
        return self.store.write_note(
            relative_path=relative_path,
            content=content,
            update_frontmatter=update_frontmatter,
        )

    def delete_note(self, relative_path: str) -> bool:
        """Delete a note."""
        return self.store.delete_note(relative_path)

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search notes by keyword with ranking."""
        return self.store.search_notes(query, limit=limit)

    def get_graph(self) -> Dict[str, Any]:
        """Return knowledge graph with nodes and edges."""
        return self.store.get_graph()

    def get_mindmap(self, include_tags: bool = True, include_taxonomy: bool = True) -> Dict[str, Any]:
        """Return multi-dimensional knowledge graph for Mind Map view."""
        return self.store.get_mindmap(include_tags=include_tags, include_taxonomy=include_taxonomy)

    def get_overview(self, max_items: int = 20) -> str:
        """Return compact text summary for LLM prompt context."""
        return self.store.get_overview(max_items=max_items)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate metrics."""
        return self.store.get_stats()
