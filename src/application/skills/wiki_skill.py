"""
Universal Wiki Skill for Document Management, Search & Knowledge Graph [REQ-WIKI-005].
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.wiki.frontmatter import FrontmatterParser
from src.domain.wiki.store import WikiStore


class WikiSkill:
    """
    Universal Skill for managing markdown wiki documents, structured YAML frontmatter,
    and navigating the knowledge graph.
    """

    def __init__(self, wiki_root: str | Path = "data/wiki"):
        self.store = WikiStore(root_dir=wiki_root)
        self.store.scaffold()
        self.wiki_root = self.store.root_dir

    def parse_yaml_frontmatter(self, content: str) -> Dict[str, Any]:
        """
        Parse YAML frontmatter enclosed in leading --- delimiters.
        """
        meta, body = FrontmatterParser.parse(content)
        return {"frontmatter": meta.model_dump(), "body": body}

    def create_wiki_note(
        self,
        title: str,
        content: str = "",
        domain: str = "general",
        topic: str = "general",
        category: str = "notes",
        inbox_priority: str = "need_to_do",
        document_type: str = "atomic_note",
        tags: Optional[List[str]] = None,
        summary: str = "",
        status: str = "draft",
        priority: str = "medium",
        relative_path: Optional[str] = None,
        extra_frontmatter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new markdown note with structured YAML frontmatter inside the wiki.
        """
        if relative_path:
            safe_target = self.store._resolve_safe_path(relative_path)
            if safe_target is None:
                return {"success": False, "error": "Path traversal detected: target path is outside wiki root."}

            res = self.store.write_note(
                relative_path=relative_path,
                content=content,
                update_frontmatter={
                    "title": title,
                    "domain": domain,
                    "topic": topic,
                    "document_type": document_type,
                    "tags": tags or [],
                    "summary": summary,
                    "status": status,
                    "priority": priority,
                    **(extra_frontmatter or {}),
                },
            )
            return {
                "success": True,
                "path": res["path"],
                "title": title,
                "category": category,
            }

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
            extra_meta=extra_frontmatter,
        )

    def read_wiki_note(self, relative_path: str) -> Dict[str, Any]:
        """Read a wiki note and parse its frontmatter and body."""
        res = self.store.read_note(relative_path)
        if not res.get("success"):
            return res
        meta = res.get("meta") or res.get("frontmatter") or {}
        title = res.get("title") or meta.get("title") or ""
        body = res.get("content") or ""
        return {
            "success": True,
            "path": res["path"],
            "title": title,
            "frontmatter": meta,
            "meta": meta,
            "content": body,
            "body": body,
        }

    def update_wiki_note(
        self,
        relative_path: str,
        content: str = "",
        update_frontmatter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update note content or frontmatter in the Wiki."""
        return self.store.write_note(
            relative_path=relative_path,
            content=content,
            update_frontmatter=update_frontmatter,
        )

    def organize_wiki_note(
        self,
        source_path: str,
        target_domain: str,
        target_topic: str,
        document_type: str = "atomic_note",
        summary: str = "",
        tags: Optional[List[str]] = None,
        new_title: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Triage an inbox note and move it to a permanent Degree/Subject directory."""
        return self.store.organize_note(
            source_path=source_path,
            target_domain=target_domain,
            target_topic=target_topic,
            document_type=document_type,
            summary=summary,
            tags=tags,
            new_title=new_title,
        )

    def search_wiki_notes(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search across all markdown notes in the Wiki."""
        return self.store.search_notes(query=query, limit=limit)

    def list_wiki_notes(
        self,
        category: Optional[str] = None,
        domain: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List markdown notes matching category, domain, or topic."""
        return self.store.list_notes(category=category, domain=domain, topic=topic)

    def get_wiki_overview(self, max_items: int = 20) -> Dict[str, Any]:
        """Get high-level summary overview of the Wiki."""
        return self.store.get_overview(max_items=max_items)

    def get_wiki_graph(self) -> Dict[str, Any]:
        """Get the interconnected wiki knowledge graph nodes and edges."""
        return self.store.get_graph()

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register all Wiki tools into the ScopedToolRegistry."""
        registry.register_tool(
            name="wiki_note_create",
            description="Create a new markdown note in the Wiki with structured YAML metadata.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the note"},
                    "content": {"type": "string", "description": "Markdown body content"},
                    "domain": {"type": "string", "default": "general", "description": "Degree domain"},
                    "topic": {"type": "string", "default": "general", "description": "Subject class topic"},
                    "category": {"type": "string", "default": "notes", "enum": ["notes", "inbox", "resources"]},
                    "inbox_priority": {
                        "type": "string",
                        "default": "need_to_do",
                        "enum": ["need_to_do", "look_into", "archive"],
                    },
                    "document_type": {"type": "string", "default": "atomic_note"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "summary": {"type": "string", "description": "1-3 sentence summary"},
                    "status": {"type": "string", "default": "draft"},
                    "priority": {"type": "string", "default": "medium"},
                    "relative_path": {"type": "string", "description": "Optional explicit relative path"},
                },
                "required": ["title"],
            },
            handler=self.create_wiki_note,
        )

        registry.register_tool(
            name="wiki_note_read",
            description="Read a markdown note from the Wiki and return its YAML frontmatter and body.",
            parameters={
                "type": "object",
                "properties": {
                    "relative_path": {
                        "type": "string",
                        "description": "Relative path to the note (e.g. notes/ai/agents/intro.md)",
                    },
                },
                "required": ["relative_path"],
            },
            handler=self.read_wiki_note,
        )

        registry.register_tool(
            name="wiki_note_update",
            description="Update the content or frontmatter of an existing Wiki note.",
            parameters={
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Relative path to the note"},
                    "content": {"type": "string", "description": "Updated markdown body"},
                    "update_frontmatter": {
                        "type": "object",
                        "description": "Dictionary of frontmatter fields to update",
                    },
                },
                "required": ["relative_path"],
            },
            handler=self.update_wiki_note,
        )

        registry.register_tool(
            name="wiki_note_organize",
            description="Triage an inbox note and move it to a permanent Degree/Subject directory.",
            parameters={
                "type": "object",
                "properties": {
                    "source_path": {"type": "string", "description": "Relative path of source inbox note"},
                    "target_domain": {"type": "string", "description": "Destination degree domain"},
                    "target_topic": {"type": "string", "description": "Destination subject topic"},
                    "document_type": {"type": "string", "default": "atomic_note"},
                    "summary": {"type": "string", "description": "1-3 sentence summary"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "new_title": {"type": "string", "description": "Optional refined title"},
                },
                "required": ["source_path", "target_domain", "target_topic"],
            },
            handler=self.organize_wiki_note,
        )

        registry.register_tool(
            name="wiki_note_search",
            description="Search markdown notes across the Wiki using keyword ranking.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword query"},
                    "limit": {"type": "integer", "default": 5, "description": "Max results to return"},
                },
                "required": ["query"],
            },
            handler=self.search_wiki_notes,
        )

        registry.register_tool(
            name="wiki_note_list",
            description="List markdown notes stored in the Wiki, optionally filtered by category, domain, or topic.",
            parameters={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["notes", "inbox", "resources"]},
                    "domain": {"type": "string", "description": "Degree domain filter"},
                    "topic": {"type": "string", "description": "Class topic filter"},
                },
            },
            handler=self.list_wiki_notes,
        )

        registry.register_tool(
            name="wiki_overview",
            description="Get a compact, high-level summary of all categories and notes in the Wiki (<150 tokens).",
            parameters={
                "type": "object",
                "properties": {
                    "max_items": {"type": "integer", "default": 20, "description": "Max sample items per folder"},
                },
            },
            handler=self.get_wiki_overview,
        )

        registry.register_tool(
            name="wiki_graph",
            description="Retrieve the interconnected Wiki knowledge graph (nodes and [[wikilink]] edges).",
            parameters={"type": "object", "properties": {}},
            handler=self.get_wiki_graph,
        )


# Backward compatibility alias
LibrarianSkill = WikiSkill
