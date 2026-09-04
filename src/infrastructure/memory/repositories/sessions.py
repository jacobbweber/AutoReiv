"""
Session & Message History Repository Mixin [REQ-KERNEL-004].
"""

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.domain.memory.models import Session


def generate_session_title_from_prompt(prompt: str) -> str:
    """Generate a clean 2-5 word session title from initial user prompt [CARD-150, REQ-CHAT-002]."""
    if not prompt or not isinstance(prompt, str):
        return ""
    clean = prompt.strip()
    clean = re.sub(r'^[#>\s"\']+', '', clean)

    filler_patterns = [
        r'^(?:hey|hi|hello|good\s+(?:morning|afternoon|evening))\b[,\s]*',
        r'^(?:autoreiv|assistant|agent)\b[,\s]*',
        r'^(?:please|can you(?: please)?|could you(?: please)?|help me(?: to)?|i want to|i need to|let\'s|lets|how do i|how to)\b[,\s]*',
    ]
    changed = True
    while changed:
        changed = False
        for pat in filler_patterns:
            new_clean = re.sub(pat, '', clean, flags=re.IGNORECASE).strip()
            if new_clean and new_clean != clean:
                clean = new_clean
                changed = True

    if not clean:
        clean = prompt.strip()
    if not clean:
        return ""

    first_line = clean.splitlines()[0]
    first_sentence = re.split(r'[.?!]\s+', first_line)[0].strip()
    if not first_sentence:
        first_sentence = first_line

    words = first_sentence.split()
    if len(words) > 6:
        selected_words = words[:5]
        title = " ".join(selected_words)
    else:
        title = " ".join(words)

    title = re.sub(r'[,:;!?.-]+$', '', title).strip()
    if len(title) > 48:
        title = title[:45].rsplit(' ', 1)[0] + '…'

    if title:
        title = title[0].upper() + title[1:]

    return title


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

    def update_session_title(self, session_id: str, title: str) -> Optional[Session]:
        """Update session title and refresh updated_at timestamp [CARD-150, REQ-CHAT-002]."""
        clean_title = title.strip()
        if not clean_title:
            return None
        now = datetime.now(timezone.utc)
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (clean_title, now.isoformat(), session_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            return self.get_session(session_id)
        finally:
            if self._mem_conn is None:
                conn.close()


    def prune_expired_sessions(
        self,
        agent_id: str,
        max_age_days: int,
        exclude_session_id: Optional[str] = None,
    ) -> int:
        """Delete chat sessions (and cascaded messages) older than max_age_days. 0 means never."""
        if max_age_days <= 0:
            return 0
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            sql = "SELECT id FROM sessions WHERE agent_id = ? AND updated_at < ?"
            params: list = [agent_id, cutoff]
            if exclude_session_id:
                sql += " AND id != ?"
                params.append(exclude_session_id)
            cur.execute(sql, params)
            ids = [row["id"] for row in cur.fetchall()]
            for sid in ids:
                cur.execute("DELETE FROM pending_approvals WHERE session_id = ?", (sid,))
                cur.execute("DELETE FROM sessions WHERE id = ?", (sid,))
            conn.commit()
            return len(ids)
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
            if message.role == Role.TOOL and message.tool_call_id:
                cur.execute(
                    "SELECT id FROM messages WHERE session_id = ? AND role = 'tool' AND tool_call_id = ? ORDER BY sequence_num DESC LIMIT 1",
                    (session_id, message.tool_call_id),
                )
                existing_row = cur.fetchone()
                if existing_row:
                    existing_id = existing_row[0]
                    cur.execute(
                        "UPDATE messages SET content = ?, name = ?, created_at = ? WHERE id = ?",
                        (message.content, message.name, now.isoformat(), existing_id),
                    )
                    cur.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now.isoformat(), session_id))
                    conn.commit()
                    return existing_id

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
