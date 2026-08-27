"""
Session & Message History Repository Mixin [REQ-KERNEL-004].
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.domain.memory.models import Session


class SessionRepositoryMixin:
    """Methods for managing chat sessions and chronological message histories."""

    def create_session(
        self,
        agent_id: str,
        title: str = "New Conversation",
        session_id: Optional[str] = None,
    ) -> Session:
        sid = session_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO sessions (id, agent_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sid, agent_id, title, now.isoformat(), now.isoformat()),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()
        return Session(id=sid, agent_id=agent_id, title=title, created_at=now, updated_at=now)

    def get_session(self, session_id: str) -> Optional[Session]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, agent_id, title, created_at, updated_at FROM sessions WHERE id = ?", (session_id,))
            row = cur.fetchone()
            if not row:
                return None
            return Session(
                id=row["id"],
                agent_id=row["agent_id"],
                title=row["title"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_sessions(self, agent_id: Optional[str] = None) -> List[Session]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if agent_id:
                cur.execute(
                    "SELECT id, agent_id, title, created_at, updated_at FROM sessions WHERE agent_id = ? ORDER BY updated_at DESC",
                    (agent_id,),
                )
            else:
                cur.execute("SELECT id, agent_id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC")
            rows = cur.fetchall()
            return [
                Session(
                    id=r["id"],
                    agent_id=r["agent_id"],
                    title=r["title"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                    updated_at=datetime.fromisoformat(r["updated_at"]),
                )
                for r in rows
            ]
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_session(self, session_id: str) -> bool:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()

    def save_message(self, session_id: str, agent_id: str, message: ChatMessage) -> str:
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        tool_calls_json = None
        if message.tool_calls:
            tool_calls_json = json.dumps([tc.model_dump() for tc in message.tool_calls])

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(MAX(sequence_num), 0) + 1 FROM messages WHERE session_id = ?", (session_id,))
            next_seq = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO messages (id, session_id, agent_id, role, content, tool_calls_json, tool_call_id, name, sequence_num, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg_id,
                    session_id,
                    agent_id,
                    message.role.value,
                    message.content,
                    tool_calls_json,
                    message.tool_call_id,
                    message.name,
                    next_seq,
                    now.isoformat(),
                ),
            )
            cur.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now.isoformat(), session_id))
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

        return msg_id

    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        query = """
            SELECT role, content, tool_calls_json, tool_call_id, name
            FROM messages
            WHERE session_id = ?
            ORDER BY sequence_num ASC
        """
        params: List[Any] = [session_id]
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            messages = []
            for r in rows:
                tool_calls = None
                if r["tool_calls_json"]:
                    try:
                        raw_calls = json.loads(r["tool_calls_json"])
                        tool_calls = [ToolCall(**tc) for tc in raw_calls]
                    except Exception:
                        tool_calls = None

                messages.append(
                    ChatMessage(
                        role=Role(r["role"]),
                        content=r["content"],
                        tool_calls=tool_calls,
                        tool_call_id=r["tool_call_id"],
                        name=r["name"],
                    )
                )
            return messages
        finally:
            if self._mem_conn is None:
                conn.close()
