"""
Librarian Skill for Wiki Document Management & YAML Frontmatter Governance [REQ-AGENTS-005, REQ-WIKI-005].
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.wiki.frontmatter import FrontmatterParser
from src.domain.wiki.store import WikiStore


class LibrarianSkill:
    """
    Skill for managing markdown wiki documents, structured YAML frontmatter,
    and enforcing path-jailed file access.
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
            # If explicit path provided, check for traversal
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
        return {
            "success": True,
            "path": res["path"],
            "title": res["title"],
            "frontmatter": res["meta"],
            "body": res["content"],
        }

    def update_wiki_note(
        self,
        relative_path: str,
        content: str,
        update_frontmatter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Non-destructively update an existing note's body while preserving frontmatter."""
        return self.store.write_note(
            relative_path=relative_path,
            content=content,
            update_frontmatter=update_frontmatter,
        )

    def search_wiki_notes(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search markdown notes by keyword with ranking."""
        return self.store.search_notes(query=query, limit=limit)

    def list_wiki_notes(
        self,
        category: Optional[str] = None,
        domain: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all wiki markdown files, optionally filtered."""
        notes = self.store.list_notes()
        results = []
        for n in notes:
            if category and not n["path"].startswith(category.lower()):
                continue
            if domain and n.get("domain", "").lower() != domain.lower():
                continue
            if topic and n.get("topic", "").lower() != topic.lower():
                continue
            results.append(n)
        return results

    def get_wiki_overview(self, max_items: int = 20) -> str:
        """Return a compact summary of wiki contents for agent context."""
        return self.store.get_overview(max_items=max_items)

    def get_wiki_graph(self) -> Dict[str, Any]:
        """Return the knowledge graph nodes and edges."""
        return self.store.get_graph()

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register Librarian tools in the scoped tool registry."""
        registry.register_tool(
            name="yaml_frontmatter_parse",
            description="Parse YAML frontmatter metadata and body from a markdown document string.",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Raw markdown document string with YAML header"},
                },
                "required": ["content"],
            },
            handler=self.parse_yaml_frontmatter,
        )

        registry.register_tool(
            name="wiki_note_create",
            description="Create or file a new markdown note with structured YAML frontmatter in the Wiki.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title"},
                    "content": {"type": "string", "description": "Markdown body content"},
                    "domain": {"type": "string", "description": "Level 1 Degree field (e.g. information_technology)", "default": "general"},
                    "topic": {"type": "string", "description": "Level 2 Class/Subject (e.g. ai_engineering)", "default": "general"},
                    "category": {"type": "string", "enum": ["notes", "inbox", "resources"], "default": "notes"},
                    "inbox_priority": {"type": "string", "enum": ["need_to_do", "should_do", "want_to_do"], "default": "need_to_do"},
                    "document_type": {
                        "type": "string",
                        "enum": ["atomic_note", "master_note", "proxy_note", "moc", "operating_manual", "template", "log"],
                        "default": "atomic_note",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of snake_case tags",
                    },
                    "summary": {"type": "string", "description": "1-3 sentence factual abstraction"},
                    "relative_path": {"type": "string", "description": "Optional explicit relative path"},
                },
                "required": ["title"],
            },
            handler=self.create_wiki_note,
        )

        registry.register_tool(
            name="wiki_note_read",
            description="Read a markdown note from the Wiki and parse its YAML frontmatter.",
            parameters={
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Relative file path (e.g. notes/information_technology/ai_engineering/note.md)"},
                },
                "required": ["relative_path"],
            },
            handler=self.read_wiki_note,
        )

        registry.register_tool(
            name="wiki_note_update",
            description="Update a note's body non-destructively, preserving existing YAML frontmatter.",
            parameters={
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Relative file path"},
                    "content": {"type": "string", "description": "New body content"},
                    "update_frontmatter": {"type": "object", "description": "Optional dictionary of frontmatter fields to update"},
                },
                "required": ["relative_path", "content"],
            },
            handler=self.update_wiki_note,
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
