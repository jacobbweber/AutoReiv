"""
Wiki Export Application Service [REQ-WEB-003].
Formats and persists markdown documents with YAML frontmatter to a path-jailed wiki directory.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class WikiExportService:
    """
    Exports single messages or entire conversation sessions into PARA-Wiki compatible
    markdown files with structured YAML frontmatter.
    """

    def __init__(self, base_wiki_path: str = "./data/wiki"):
        self.base_wiki_path = Path(base_wiki_path).resolve()

    def _sanitize_name(self, name: str) -> str:
        """Sanitize title or category to prevent directory traversal and illegal characters."""
        cleaned = re.sub(r"[^a-zA-Z0-9_\-\s]", "_", name)
        cleaned = re.sub(r"\s+", "_", cleaned).strip("_")
        return cleaned.lower() if cleaned else "untitled"

    def _resolve_safe_category_dir(self, category: str) -> Path:
        """Ensure the target category directory is strictly jailed inside base_wiki_path."""
        safe_cat = self._sanitize_name(category)
        target_dir = (self.base_wiki_path / safe_cat).resolve()

        # Ensure path does not escape base_wiki_path
        if not str(target_dir).startswith(str(self.base_wiki_path)):
            target_dir = (self.base_wiki_path / "03_resources").resolve()

        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def _generate_frontmatter(
        self,
        title: str,
        agent_id: str,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Generate valid YAML frontmatter block."""
        now_str = datetime.now(timezone.utc).isoformat()
        clean_tags = tags or ["chat_export"]
        tags_yaml = "\n".join([f'  - "{t}"' for t in clean_tags])

        return (
            f"---\n"
            f'title: "{title}"\n'
            f'agent: "{agent_id}"\n'
            f'session_id: "{session_id or "unknown"}"\n'
            f'exported_at: "{now_str}"\n'
            f"tags:\n"
            f"{tags_yaml}\n"
            f"---\n\n"
        )

    def export_message(
        self,
        title: str,
        content: str,
        agent_id: str,
        session_id: Optional[str] = None,
        category: str = "03_Resources",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Export an individual message to markdown note."""
        target_dir = self._resolve_safe_category_dir(category)
        safe_filename = f"{self._sanitize_name(title)}.md"
        filepath = target_dir / safe_filename

        frontmatter = self._generate_frontmatter(
            title=title,
            agent_id=agent_id,
            session_id=session_id,
            tags=tags,
        )
        body = f"# {title}\n\n{content}\n"
        full_content = frontmatter + body

        filepath.write_text(full_content, encoding="utf-8")

        return {
            "status": "success",
            "filepath": str(filepath),
            "filename": safe_filename,
        }

    def export_session(
        self,
        title: str,
        messages: List[Dict[str, Any]],
        agent_id: str,
        session_id: Optional[str] = None,
        category: str = "03_Resources",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Export a full conversation thread to markdown note."""
        formatted_messages = []
        for msg in messages:
            role = msg.get("role", "user").capitalize()
            text = msg.get("content", "")
            formatted_messages.append(f"**{role}**:\n\n{text}\n\n---\n")

        thread_body = "\n".join(formatted_messages)
        return self.export_message(
            title=title,
            content=thread_body,
            agent_id=agent_id,
            session_id=session_id,
            category=category,
            tags=tags or ["session_export"],
        )
