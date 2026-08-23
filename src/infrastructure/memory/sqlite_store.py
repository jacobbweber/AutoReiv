"""
SQLite State Store with WAL Mode [REQ-KERNEL-004].
Handles session CRUD, message history checkpointing, and telemetry persistence.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.domain.memory.models import Session
from src.domain.telemetry.models import TelemetrySpan


class SQLiteStateStore:
    """
    Embedded SQLite State Store with WAL mode and thread-safe connections.
    """

    def __init__(self, db_path: str = "autoreiv.db"):
        self.db_path = db_path
        self._mem_conn: Optional[sqlite3.Connection] = None
        if db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row
            self._mem_conn.execute("PRAGMA foreign_keys = ON;")
        else:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        if self._mem_conn is not None:
            return self._mem_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def initialize_db(self) -> None:
        """Create tables, indexes, and configure WAL mode."""
        conn = self._get_connection()
        try:
            if self.db_path != ":memory:":
                conn.execute("PRAGMA journal_mode = WAL;")

            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    agent_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls_json TEXT,
                    tool_call_id TEXT,
                    name TEXT,
                    sequence_num INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, sequence_num);

                CREATE TABLE IF NOT EXISTS telemetry_spans (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    agent_id TEXT,
                    span_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    success BOOLEAN NOT NULL DEFAULT 1,
                    error_message TEXT,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_telemetry_agent ON telemetry_spans(agent_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_telemetry_span_type ON telemetry_spans(span_type, created_at);

                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    due_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                """
            )
            if self._mem_conn is None:
                conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_journal_mode(self) -> str:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode;")
            row = cur.fetchone()
            return row[0] if row else "unknown"
        finally:
            if self._mem_conn is None:
                conn.close()

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

    def save_telemetry_span(self, span: TelemetrySpan) -> None:
        metadata_json = json.dumps(span.metadata) if span.metadata else None
        now_str = span.created_at.isoformat()
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO telemetry_spans (id, session_id, agent_id, span_type, name, duration_ms, prompt_tokens, completion_tokens, success, error_message, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    span.id,
                    span.session_id,
                    span.agent_id,
                    span.span_type,
                    span.name,
                    span.duration_ms,
                    span.prompt_tokens,
                    span.completion_tokens,
                    1 if span.success else 0,
                    span.error_message,
                    metadata_json,
                    now_str,
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_telemetry_spans(
        self,
        agent_id: Optional[str] = None,
        span_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[TelemetrySpan]:
        query = "SELECT id, session_id, agent_id, span_type, name, duration_ms, prompt_tokens, completion_tokens, success, error_message, metadata_json, created_at FROM telemetry_spans WHERE 1=1"
        params: List[Any] = []

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
        if span_type:
            query += " AND span_type = ?"
            params.append(span_type)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            spans = []
            for r in rows:
                meta = {}
                if r["metadata_json"]:
                    try:
                        meta = json.loads(r["metadata_json"])
                    except Exception:
                        pass

                spans.append(
                    TelemetrySpan(
                        id=r["id"],
                        session_id=r["session_id"],
                        agent_id=r["agent_id"],
                        span_type=r["span_type"],
                        name=r["name"],
                        duration_ms=r["duration_ms"],
                        prompt_tokens=r["prompt_tokens"],
                        completion_tokens=r["completion_tokens"],
                        success=bool(r["success"]),
                        error_message=r["error_message"],
                        metadata=meta,
                        created_at=datetime.fromisoformat(r["created_at"]),
                    )
                )
            return spans
        finally:
            if self._mem_conn is None:
                conn.close()

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        due_date: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        tid = task_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO tasks (id, title, description, status, priority, due_date, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (tid, title, description, priority, due_date, now, now),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()
        return {
            "id": tid,
            "title": title,
            "description": description,
            "status": "pending",
            "priority": priority,
            "due_date": due_date,
            "created_at": now,
            "updated_at": now,
        }

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT id, title, description, status, priority, due_date, created_at, updated_at FROM tasks WHERE 1=1"
        params: List[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        query += " ORDER BY created_at DESC"

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            if self._mem_conn is None:
                conn.close()

    def update_task_status(self, task_id: str, status: str) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, task_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            cur.execute(
                "SELECT id, title, description, status, priority, due_date, created_at, updated_at FROM tasks WHERE id = ?",
                (task_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_task(self, task_id: str) -> bool:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()
