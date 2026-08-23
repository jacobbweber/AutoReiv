"""
Librarian Skill for PARA-Wiki & YAML Frontmatter Management [REQ-AGENTS-005].
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry


class LibrarianSkill:
    """
    Skill for managing markdown wiki documents, structured YAML frontmatter,
    and enforcing path-jailed file access.
    """

    def __init__(self, wiki_root: str = "data/wiki"):
        self.wiki_root = Path(wiki_root).resolve()
        self.wiki_root.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Optional[Path]:
        """Ensure path resolves within wiki_root without traversal."""
        try:
            target = (self.wiki_root / relative_path).resolve()
            if not str(target).startswith(str(self.wiki_root)):
                return None
            return target
        except Exception:
            return None

    def parse_yaml_frontmatter(self, content: str) -> Dict[str, Any]:
        """
        Parse YAML frontmatter enclosed in leading --- delimiters.
        """
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
        if not match:
            return {"frontmatter": {}, "body": content.strip()}

        fm_text, body = match.group(1), match.group(2)
        frontmatter: Dict[str, Any] = {}

        current_list_key = None
        for line in fm_text.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue

            if line_str.startswith("- ") and current_list_key:
                frontmatter[current_list_key].append(line_str[2:].strip().strip("\"'"))
                continue

            if ":" in line_str:
                parts = line_str.split(":", 1)
                k = parts[0].strip()
                v = parts[1].strip().strip("\"'")
                if not v:
                    frontmatter[k] = []
                    current_list_key = k
                else:
                    frontmatter[k] = v
                    current_list_key = None

        return {"frontmatter": frontmatter, "body": body.strip()}

    def _format_frontmatter_text(self, metadata: Dict[str, Any]) -> str:
        lines = ["---"]
        for k, v in metadata.items():
            if isinstance(v, list):
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{k}: {v}")
        lines.append("---")
        return "\n".join(lines)

    def create_wiki_note(
        self,
        relative_path: str,
        title: str,
        category: str = "Inbox",
        tags: Optional[List[str]] = None,
        content: str = "",
        extra_frontmatter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new markdown note with structured YAML frontmatter inside the wiki.
        """
        target_path = self._resolve_safe_path(relative_path)
        if target_path is None:
            return {"success": False, "error": "Path traversal detected: target path is outside wiki root."}

        target_path.parent.mkdir(parents=True, exist_ok=True)

        meta: Dict[str, Any] = {
            "title": title,
            "category": category,
            "tags": tags or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra_frontmatter:
            meta.update(extra_frontmatter)

        header = self._format_frontmatter_text(meta)
        full_document = f"{header}\n\n{content.strip()}\n"

        target_path.write_text(full_document, encoding="utf-8")
        return {
            "success": True,
            "path": relative_path,
            "title": title,
            "category": category,
        }

    def read_wiki_note(self, relative_path: str) -> Dict[str, Any]:
        """Read a wiki note and parse its frontmatter and body."""
        target_path = self._resolve_safe_path(relative_path)
        if target_path is None or not target_path.exists():
            return {"success": False, "error": f"Note '{relative_path}' not found."}

        raw_text = target_path.read_text(encoding="utf-8")
        parsed = self.parse_yaml_frontmatter(raw_text)
        title = parsed["frontmatter"].get("title", target_path.stem)

        return {
            "success": True,
            "path": relative_path,
            "title": title,
            "frontmatter": parsed["frontmatter"],
            "body": parsed["body"],
        }

    def list_wiki_notes(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all wiki markdown files, optionally filtered by PARA category."""
        results = []
        for file_path in self.wiki_root.rglob("*.md"):
            rel = str(file_path.relative_to(self.wiki_root)).replace("\\", "/")
            try:
                raw_text = file_path.read_text(encoding="utf-8")
                parsed = self.parse_yaml_frontmatter(raw_text)
                note_cat = parsed["frontmatter"].get("category", "Inbox")
                title = parsed["frontmatter"].get("title", file_path.stem)
                tags = parsed["frontmatter"].get("tags", [])

                if category and note_cat.lower() != category.lower():
                    continue

                results.append(
                    {
                        "path": rel,
                        "title": title,
                        "category": note_cat,
                        "tags": tags,
                    }
                )
            except Exception:
                continue
        return results

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
            description="Create or overwrite a markdown note with structured YAML frontmatter in the Wiki.",
            parameters={
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Relative file path (e.g. projects/app.md)"},
                    "title": {"type": "string", "description": "Note title"},
                    "category": {
                        "type": "string",
                        "enum": ["Projects", "Areas", "Resources", "Archives", "Inbox"],
                        "default": "Inbox",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tags",
                    },
                    "content": {"type": "string", "description": "Markdown body content"},
                },
                "required": ["relative_path", "title"],
            },
            handler=self.create_wiki_note,
        )

        registry.register_tool(
            name="wiki_note_read",
            description="Read a markdown note from the Wiki and parse its YAML frontmatter.",
            parameters={
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Relative file path (e.g. inbox/idea.md)"},
                },
                "required": ["relative_path"],
            },
            handler=self.read_wiki_note,
        )

        registry.register_tool(
            name="wiki_note_list",
            description="List markdown notes stored in the Wiki, optionally filtered by category.",
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["Projects", "Areas", "Resources", "Archives", "Inbox"],
                    },
                },
            },
            handler=self.list_wiki_notes,
        )
