"""
Dynamic Tone Registry SQLite Repository Mixin [CARD-131, REQ-TONE-001].
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from src.domain.kernel.models import ToneDefinition

BUILTIN_TONES: List[Dict[str, Any]] = [
    {
        "id": "default",
        "name": "Default (Balanced)",
        "description": "Balanced conversational baseline",
        "directive": "Standard helpful, conversational baseline.",
        "is_builtin": True,
    },
    {
        "id": "technical",
        "name": "Technical",
        "description": "Precise, authoritative, code-focused",
        "directive": "Tone directive: Technical, precise, and authoritative.",
        "is_builtin": True,
    },
    {
        "id": "concise",
        "name": "Concise",
        "description": "Terse, direct, minimal preamble",
        "directive": "Tone directive: Concise and direct. Avoid unnecessary preamble.",
        "is_builtin": True,
    },
    {
        "id": "friendly",
        "name": "Friendly",
        "description": "Warm, supportive, conversational",
        "directive": "Tone directive: Friendly, warm, and supportive.",
        "is_builtin": True,
    },
    {
        "id": "academic",
        "name": "Academic",
        "description": "Rigorous, structured, cited",
        "directive": "Tone directive: Academic, rigorous, with cited reasoning.",
        "is_builtin": True,
    },
    {
        "id": "socratic",
        "name": "Socratic",
        "description": "Guiding, trade-off structured options",
        "directive": "Tone directive: Socratic and guiding with clear structured options.",
        "is_builtin": True,
    },
]


class TonesRepositoryMixin:
    """SQLite CRUD operations for dynamic and built-in tone definitions."""

    def _ensure_tones_seeded(self, conn: sqlite3.Connection) -> None:
        cur = conn.cursor()
        for b in BUILTIN_TONES:
            cur.execute(
                """
                INSERT OR IGNORE INTO tones (id, name, description, directive, is_builtin)
                VALUES (?, ?, ?, ?, 1)
                """,
                (b["id"], b["name"], b["description"], b["directive"]),
            )
        conn.commit()

    def list_tones(self) -> List[ToneDefinition]:
        conn = self._get_connection()
        try:
            self._ensure_tones_seeded(conn)
            cur = conn.cursor()
            cur.execute("SELECT id, name, description, directive, is_builtin, created_at, updated_at FROM tones ORDER BY is_builtin DESC, name ASC")
            rows = cur.fetchall()
            return [
                ToneDefinition(
                    id=r["id"],
                    name=r["name"],
                    description=r["description"] or "",
                    directive=r["directive"],
                    is_builtin=bool(r["is_builtin"]),
                    created_at=str(r["created_at"]) if r["created_at"] else None,
                    updated_at=str(r["updated_at"]) if r["updated_at"] else None,
                )
                for r in rows
            ]
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_tone(self, tone_id: str) -> Optional[ToneDefinition]:
        conn = self._get_connection()
        try:
            self._ensure_tones_seeded(conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT id, name, description, directive, is_builtin, created_at, updated_at FROM tones WHERE id = ?",
                (tone_id.strip().lower(),),
            )
            r = cur.fetchone()
            if not r:
                return None
            return ToneDefinition(
                id=r["id"],
                name=r["name"],
                description=r["description"] or "",
                directive=r["directive"],
                is_builtin=bool(r["is_builtin"]),
                created_at=str(r["created_at"]) if r["created_at"] else None,
                updated_at=str(r["updated_at"]) if r["updated_at"] else None,
            )
        finally:
            if self._mem_conn is None:
                conn.close()

    def create_tone(self, tone: ToneDefinition) -> ToneDefinition:
        conn = self._get_connection()
        try:
            self._ensure_tones_seeded(conn)
            tid = tone.id.strip().lower()
            cur = conn.cursor()
            cur.execute("SELECT id FROM tones WHERE id = ?", (tid,))
            if cur.fetchone():
                raise ValueError(f"Tone with id '{tid}' already exists.")

            cur.execute(
                """
                INSERT INTO tones (id, name, description, directive, is_builtin)
                VALUES (?, ?, ?, ?, 0)
                """,
                (tid, tone.name.strip(), tone.description.strip(), tone.directive.strip()),
            )
            conn.commit()
            return self.get_tone(tid) or tone
        finally:
            if self._mem_conn is None:
                conn.close()

    def update_tone(self, tone: ToneDefinition) -> ToneDefinition:
        conn = self._get_connection()
        try:
            self._ensure_tones_seeded(conn)
            tid = tone.id.strip().lower()
            cur = conn.cursor()
            cur.execute("SELECT is_builtin FROM tones WHERE id = ?", (tid,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Tone '{tid}' not found.")
            if row["is_builtin"]:
                raise ValueError(f"Built-in tone '{tid}' cannot be modified.")

            cur.execute(
                """
                UPDATE tones
                SET name = ?, description = ?, directive = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (tone.name.strip(), tone.description.strip(), tone.directive.strip(), tid),
            )
            conn.commit()
            return self.get_tone(tid) or tone
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_tone(self, tone_id: str) -> bool:
        conn = self._get_connection()
        try:
            self._ensure_tones_seeded(conn)
            tid = tone_id.strip().lower()
            cur = conn.cursor()
            cur.execute("SELECT is_builtin FROM tones WHERE id = ?", (tid,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Tone '{tid}' not found.")
            if row["is_builtin"]:
                raise ValueError(f"Built-in tone '{tid}' cannot be deleted.")

            cur.execute("DELETE FROM tones WHERE id = ?", (tid,))
            conn.commit()
            return True
        finally:
            if self._mem_conn is None:
                conn.close()
