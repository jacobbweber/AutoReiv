"""
Prompt Catalog Repository Mixin [CARD-147, REQ-PROMPT-001].
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from src.domain.prompts.models import PromptCreate, PromptItem, PromptUpdate

logger = logging.getLogger(__name__)

BUILTIN_PROMPTS = [
    {
        "id": "builtin_sys_health",
        "title": "System Health & Telemetry Diagnostic",
        "description": "Inspect live provider connectivity, tool health matrix, and recent errors.",
        "category": "system",
        "template_text": "Run a comprehensive platform health diagnostic: inspect active providers, tool error matrices, and recent system logs, then summarize operational health.",
        "tags": ["health", "sre", "diagnostics"],
        "is_builtin": True,
    },
    {
        "id": "builtin_weekly_rollover",
        "title": "Weekly Summary & Task Rollover",
        "description": "Summarize weekly accomplishments and roll over pending tasks.",
        "category": "productivity",
        "template_text": "Review this week's active and completed tasks, generate a bulleted accomplishment summary, and roll over any unfinished items to next week's note.",
        "tags": ["tasks", "weekly", "planning"],
        "is_builtin": True,
    },
    {
        "id": "builtin_meeting_to_wiki",
        "title": "Meeting Notes to Wiki Synthesis",
        "description": "Convert raw meeting discussions or notes into a structured atomic Wiki note.",
        "category": "productivity",
        "template_text": "Transform the following meeting discussion or raw transcript into a well-structured atomic Wiki note with key decisions, action items, and YAML metadata.",
        "tags": ["wiki", "meeting", "notes"],
        "is_builtin": True,
    },
    {
        "id": "builtin_arch_review",
        "title": "Code Architecture & Refactor Review",
        "description": "Audit SOLID boundaries, code smells, and test coverage for a module.",
        "category": "coding",
        "template_text": "Perform a thorough architecture and SOLID boundary review of the specified module, identifying code smells, test gaps, and safe refactoring paths.",
        "tags": ["architecture", "review", "solid"],
        "is_builtin": True,
    },
    {
        "id": "builtin_doc_synthesis",
        "title": "Executive Document & Data Synthesis",
        "description": "Synthesize key data points, trends, and takeaways from an attached document.",
        "category": "analysis",
        "template_text": "Extract the key takeaways, data trends, and critical conclusions from the attached document or spreadsheet into an executive brief.",
        "tags": ["documents", "summary", "data"],
        "is_builtin": True,
    },
]


class PromptRepositoryMixin:
    """Provides persistence and query methods for the Prompt Catalog."""

    def _get_connection(self) -> Any:
        raise NotImplementedError

    def seed_builtin_prompts(self) -> None:
        """Seed default built-in prompts if not already present."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            for p in BUILTIN_PROMPTS:
                cur.execute("SELECT id FROM prompt_catalog WHERE id = ?", (p["id"],))
                if not cur.fetchone():
                    cur.execute(
                        """
                        INSERT INTO prompt_catalog (id, title, description, category, template_text, tags, is_builtin, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                        """,
                        (
                            p["id"],
                            p["title"],
                            p["description"],
                            p["category"],
                            p["template_text"],
                            json.dumps(p["tags"]),
                            now,
                            now,
                        ),
                    )
            conn.commit()
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def list_prompts(self, category: Optional[str] = None, search: Optional[str] = None) -> List[PromptItem]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            query = "SELECT id, title, description, category, template_text, tags, is_builtin, created_at, updated_at FROM prompt_catalog WHERE 1=1"
            params: List[Any] = []
            if category and category.lower() != "all":
                query += " AND LOWER(category) = ?"
                params.append(category.lower())
            if search:
                query += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(template_text) LIKE ?)"
                term = f"%{search.lower().strip()}%"
                params.extend([term, term, term])
            query += " ORDER BY is_builtin DESC, title ASC"

            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            items = []
            for r in rows:
                tags = []
                if r["tags"]:
                    try:
                        tags = json.loads(r["tags"])
                    except Exception:
                        tags = [t.strip() for t in r["tags"].split(",") if t.strip()]
                items.append(
                    PromptItem(
                        id=r["id"],
                        title=r["title"],
                        description=r["description"] or "",
                        category=r["category"] or "general",
                        template_text=r["template_text"],
                        tags=tags,
                        is_builtin=bool(r["is_builtin"]),
                        created_at=str(r["created_at"]),
                        updated_at=str(r["updated_at"]),
                    )
                )
            return items
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def get_prompt(self, prompt_id: str) -> Optional[PromptItem]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, description, category, template_text, tags, is_builtin, created_at, updated_at FROM prompt_catalog WHERE id = ?",
                (prompt_id,),
            )
            r = cur.fetchone()
            if not r:
                return None
            tags = []
            if r["tags"]:
                try:
                    tags = json.loads(r["tags"])
                except Exception:
                    tags = [t.strip() for t in r["tags"].split(",") if t.strip()]
            return PromptItem(
                id=r["id"],
                title=r["title"],
                description=r["description"] or "",
                category=r["category"] or "general",
                template_text=r["template_text"],
                tags=tags,
                is_builtin=bool(r["is_builtin"]),
                created_at=str(r["created_at"]),
                updated_at=str(r["updated_at"]),
            )
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def create_prompt(self, item: PromptCreate) -> PromptItem:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            prompt_id = f"prompt_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()
            cur.execute(
                """
                INSERT INTO prompt_catalog (id, title, description, category, template_text, tags, is_builtin, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    prompt_id,
                    item.title.strip(),
                    (item.description or "").strip(),
                    (item.category or "general").strip().lower(),
                    item.template_text.strip(),
                    json.dumps(item.tags or []),
                    now,
                    now,
                ),
            )
            conn.commit()
            return PromptItem(
                id=prompt_id,
                title=item.title.strip(),
                description=(item.description or "").strip(),
                category=(item.category or "general").strip().lower(),
                template_text=item.template_text.strip(),
                tags=item.tags or [],
                is_builtin=False,
                created_at=now,
                updated_at=now,
            )
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def update_prompt(self, prompt_id: str, item: PromptUpdate) -> Optional[PromptItem]:
        existing = self.get_prompt(prompt_id)
        if not existing:
            return None
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            new_title = item.title.strip() if item.title is not None else existing.title
            new_desc = item.description.strip() if item.description is not None else existing.description
            new_cat = item.category.strip().lower() if item.category is not None else existing.category
            new_text = item.template_text.strip() if item.template_text is not None else existing.template_text
            new_tags = item.tags if item.tags is not None else existing.tags
            now = datetime.now(timezone.utc).isoformat()

            cur.execute(
                """
                UPDATE prompt_catalog
                SET title = ?, description = ?, category = ?, template_text = ?, tags = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_title, new_desc, new_cat, new_text, json.dumps(new_tags), now, prompt_id),
            )
            conn.commit()
            return PromptItem(
                id=prompt_id,
                title=new_title,
                description=new_desc,
                category=new_cat,
                template_text=new_text,
                tags=new_tags,
                is_builtin=existing.is_builtin,
                created_at=existing.created_at,
                updated_at=now,
            )
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def delete_prompt(self, prompt_id: str) -> bool:
        existing = self.get_prompt(prompt_id)
        if not existing or existing.is_builtin:
            return False
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM prompt_catalog WHERE id = ? AND is_builtin = 0", (prompt_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()
