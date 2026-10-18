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
            if agent_id == "autoreiv":
                cur.execute(
                    "SELECT id, agent_id, title, created_at, updated_at FROM sessions "
                    "WHERE agent_id IN ('autoreiv', 'toolsmith', 'developer', 'architect') ORDER BY updated_at DESC",
                )
            elif agent_id:
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

    @staticmethod
    def _ensure_archive_links_table(conn: Any) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS archive_links (
                message_id TEXT PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                summary_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def delete_session(self, session_id: str) -> bool:
        conn = self._get_connection()
        try:
            self._ensure_archive_links_table(conn)
            cur = conn.cursor()
            cur.execute("DELETE FROM archive_links WHERE session_id = ?", (session_id,))
            cur.execute("DELETE FROM pending_approvals WHERE session_id = ?", (session_id,))
            cur.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            deleted = cur.rowcount > 0
            # CARD-608: the chat's job step sessions are hidden from Recent Chats, so they go with it.
            prefix = f"{session_id}::phase::"
            cur.execute("DELETE FROM archive_links WHERE substr(session_id, 1, ?) = ?", (len(prefix), prefix))
            cur.execute("DELETE FROM pending_approvals WHERE substr(session_id, 1, ?) = ?", (len(prefix), prefix))
            cur.execute("DELETE FROM messages WHERE substr(session_id, 1, ?) = ?", (len(prefix), prefix))
            cur.execute("DELETE FROM sessions WHERE substr(id, 1, ?) = ?", (len(prefix), prefix))
            conn.commit()
            return deleted
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
            if getattr(conn, "in_transaction", False):
                conn.commit()
            conn.execute("BEGIN IMMEDIATE")
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

            cur.execute(
                """
                INSERT INTO messages (
                    id, session_id, agent_id, role, content, tool_calls_json,
                    tool_call_id, name, reasoning, sequence_num, created_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    (SELECT COALESCE(MAX(sequence_num), 0) + 1 FROM messages WHERE session_id = ?),
                    ?
                )
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
                    getattr(message, "reasoning", None),
                    session_id,
                    now.isoformat(),
                ),
            )
            cur.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now.isoformat(), session_id))
            conn.commit()
        except Exception:
            if getattr(conn, "in_transaction", False):
                conn.rollback()
            raise
        finally:
            if self._mem_conn is None:
                conn.close()

        return msg_id

    def update_message(self, message_id: str, content: str) -> bool:
        """Update message content (e.g. proposal adoption state) by message ID [CARD-358]."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE messages SET content = ? WHERE id = ?", (content, message_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_message(self, message_id: str) -> Optional[ChatMessage]:
        """Fetch a single message by its persistent ID [CARD-358]."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, role, content, tool_calls_json, tool_call_id, name, reasoning FROM messages WHERE id = ?",
                (message_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            tool_calls = None
            if row["tool_calls_json"]:
                try:
                    tool_calls = [ToolCall(**tc) for tc in json.loads(row["tool_calls_json"])]
                except Exception:
                    tool_calls = None
            reasoning = None
            try:
                reasoning = row["reasoning"]
            except (KeyError, IndexError):
                reasoning = None
            return ChatMessage(
                id=row["id"],
                role=Role(row["role"]),
                content=row["content"],
                tool_calls=tool_calls,
                tool_call_id=row["tool_call_id"],
                name=row["name"],
                reasoning=reasoning,
            )
        finally:
            if self._mem_conn is None:
                conn.close()


    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        include_archived: bool = False,
    ) -> List[ChatMessage]:
        conn = self._get_connection()
        try:
            self._ensure_archive_links_table(conn)
            cur = conn.cursor()
            if include_archived:
                query = """
                    SELECT m.id, m.role, m.content, m.tool_calls_json, m.tool_call_id, m.name, m.reasoning
                    FROM messages m
                    WHERE m.session_id = ?
                    ORDER BY m.sequence_num ASC
                """
            else:
                query = """
                    SELECT m.id, m.role, m.content, m.tool_calls_json, m.tool_call_id, m.name, m.reasoning
                    FROM messages m
                    LEFT JOIN archive_links a ON a.message_id = m.id
                    WHERE m.session_id = ? AND a.message_id IS NULL
                    ORDER BY m.sequence_num ASC
                """
            params: List[Any] = [session_id]
            if limit:
                query += " LIMIT ?"
                params.append(limit)
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

                reasoning = None
                try:
                    reasoning = r["reasoning"]
                except (KeyError, IndexError):
                    reasoning = None
                messages.append(
                    ChatMessage(
                        id=r["id"],
                        role=Role(r["role"]),
                        content=r["content"],
                        tool_calls=tool_calls,
                        tool_call_id=r["tool_call_id"],
                        name=r["name"],
                        reasoning=reasoning,
                    )
                )
            return messages
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_archive_links(self, session_id: str) -> List[dict[str, str]]:
        """Return non-destructive archive_links rows for a session [CARD-699]."""
        conn = self._get_connection()
        try:
            self._ensure_archive_links_table(conn)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT message_id, session_id, summary_id, archived_at
                FROM archive_links
                WHERE session_id = ?
                ORDER BY rowid ASC
                """,
                (session_id,),
            )
            return [
                {
                    "message_id": str(r["message_id"]),
                    "session_id": str(r["session_id"]),
                    "summary_id": str(r["summary_id"]),
                    "archived_at": str(r["archived_at"]),
                }
                for r in cur.fetchall()
            ]
        finally:
            if self._mem_conn is None:
                conn.close()

    def replace_session_messages(self, session_id: str, agent_id: str, messages: List[ChatMessage]) -> None:
        """Compact or revise active messages while preserving summarized rows via archive_links [CARD-161, CARD-699]."""
        conn = self._get_connection()
        now = datetime.now(timezone.utc)
        summary_marker = "[Summary of earlier conversation:"
        try:
            self._ensure_archive_links_table(conn)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT m.id, m.role, m.content
                FROM messages m
                LEFT JOIN archive_links a ON a.message_id = m.id
                WHERE m.session_id = ? AND a.message_id IS NULL
                ORDER BY m.sequence_num ASC
                """,
                (session_id,),
            )
            existing_active = cur.fetchall()
            existing_by_id = {str(r["id"]): r for r in existing_active}

            cur.execute("SELECT COALESCE(MAX(sequence_num), 0) FROM messages WHERE session_id = ?", (session_id,))
            base_seq = int(cur.fetchone()[0] or 0)

            kept_ids: set[str] = set()
            summary_ids: list[str] = []

            for idx, msg in enumerate(messages, start=1):
                seq_num = base_seq + idx
                existing_id = str(msg.id) if getattr(msg, "id", None) and str(msg.id) in existing_by_id else None
                if existing_id is None:
                    # Fallback match by (role, content) for in-memory messages without id attached
                    for cand in existing_active:
                        cid = str(cand["id"])
                        if (
                            cid not in kept_ids
                            and cand["role"] == msg.role.value
                            and cand["content"] == (msg.content or "")
                        ):
                            existing_id = cid
                            break

                tool_calls_json = None
                if msg.tool_calls:
                    tool_calls_json = json.dumps([tc.model_dump() for tc in msg.tool_calls])

                if existing_id is not None:
                    kept_ids.add(existing_id)
                    cur.execute(
                        """
                        UPDATE messages
                        SET content = ?, tool_calls_json = ?, tool_call_id = ?, name = ?, reasoning = ?, sequence_num = ?
                        WHERE id = ?
                        """,
                        (
                            msg.content or "",
                            tool_calls_json,
                            msg.tool_call_id,
                            msg.name,
                            getattr(msg, "reasoning", None),
                            seq_num,
                            existing_id,
                        ),
                    )
                    if (msg.content or "").lstrip().startswith(summary_marker):
                        summary_ids.append(existing_id)
                else:
                    msg_id = str(getattr(msg, "id", None) or uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO messages (id, session_id, agent_id, role, content, tool_calls_json, tool_call_id, name, reasoning, sequence_num, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            msg_id,
                            session_id,
                            agent_id,
                            msg.role.value,
                            msg.content or "",
                            tool_calls_json,
                            msg.tool_call_id,
                            msg.name,
                            getattr(msg, "reasoning", None),
                            seq_num,
                            now.isoformat(),
                        ),
                    )
                    kept_ids.add(msg_id)
                    if (msg.content or "").lstrip().startswith(summary_marker):
                        summary_ids.append(msg_id)

            archived_ids = [str(r["id"]) for r in existing_active if str(r["id"]) not in kept_ids]
            if archived_ids:
                target_summary_id = summary_ids[-1] if summary_ids else next(iter(kept_ids), None)
                if target_summary_id:
                    for old_id in archived_ids:
                        cur.execute(
                            """
                            INSERT OR REPLACE INTO archive_links (message_id, session_id, summary_id, archived_at)
                            VALUES (?, ?, ?, ?)
                            """,
                            (old_id, session_id, target_summary_id, now.isoformat()),
                        )

            cur.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now.isoformat(), session_id))
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()
