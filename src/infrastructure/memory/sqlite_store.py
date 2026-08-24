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
from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.memory.models import Session
from src.domain.observability.models import (
    AgentKPISummary,
    KPIDashboardSummary,
    TelemetryFilter,
    TimeSeriesDataPoint,
    ToolReliabilityMetric,
)
from src.domain.routines.models import Routine, RoutineRun, RoutineStatus, ScheduleType
from src.domain.settings.models import AgentCustomization
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
        self.initialize_db()

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

                CREATE TABLE IF NOT EXISTS routines (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    agent_id TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    schedule_type TEXT NOT NULL DEFAULT 'interval',
                    interval_seconds INTEGER DEFAULT 3600,
                    cron_expression TEXT,
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    last_run_at TIMESTAMP,
                    next_run_at TIMESTAMP,
                    last_status TEXT NOT NULL DEFAULT 'idle',
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS routine_runs (
                    id TEXT PRIMARY KEY,
                    routine_id TEXT NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
                    agent_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output TEXT DEFAULT '',
                    error_message TEXT,
                    duration_ms REAL NOT NULL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_routine_runs_routine ON routine_runs(routine_id, created_at);

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS agent_overrides (
                    agent_id TEXT PRIMARY KEY,
                    tone TEXT,
                    system_prompt TEXT,
                    model TEXT,
                    allowed_tools_json TEXT,
                    max_turns INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS custom_agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    system_prompt TEXT NOT NULL,
                    purpose TEXT NOT NULL DEFAULT 'general',
                    tone TEXT DEFAULT 'default',
                    avatar_icon TEXT DEFAULT 'bot',
                    model TEXT DEFAULT 'default',
                    allowed_tools_json TEXT,
                    max_turns INTEGER DEFAULT 10,
                    is_builtin BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS episodic_facts (
                    id TEXT PRIMARY KEY,
                    entity TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source_session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(entity, key)
                );

                CREATE TABLE IF NOT EXISTS pending_approvals (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    decision_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_approvals_session ON pending_approvals(session_id, status);
                CREATE INDEX IF NOT EXISTS idx_facts_entity ON episodic_facts(entity);
                CREATE INDEX IF NOT EXISTS idx_telemetry_spans_query ON telemetry_spans(agent_id, span_type, created_at);
                CREATE INDEX IF NOT EXISTS idx_telemetry_spans_error ON telemetry_spans(success, span_type);
                """
            )
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
        has_error: Optional[bool] = None,
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
        if has_error is not None:
            if has_error:
                query += " AND success = 0"
            else:
                query += " AND success = 1"

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

    def save_routine(self, routine: Routine) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(routine.metadata) if routine.metadata else None
        last_run_str = routine.last_run_at.isoformat() if routine.last_run_at else None
        next_run_str = routine.next_run_at.isoformat() if routine.next_run_at else None

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO routines (
                    id, name, description, agent_id, prompt, schedule_type,
                    interval_seconds, cron_expression, enabled, last_run_at,
                    next_run_at, last_status, metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    agent_id = excluded.agent_id,
                    prompt = excluded.prompt,
                    schedule_type = excluded.schedule_type,
                    interval_seconds = excluded.interval_seconds,
                    cron_expression = excluded.cron_expression,
                    enabled = excluded.enabled,
                    last_run_at = excluded.last_run_at,
                    next_run_at = excluded.next_run_at,
                    last_status = excluded.last_status,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    routine.id,
                    routine.name,
                    routine.description,
                    routine.agent_id,
                    routine.prompt,
                    routine.schedule_type.value
                    if hasattr(routine.schedule_type, "value")
                    else str(routine.schedule_type),
                    routine.interval_seconds,
                    routine.cron_expression,
                    1 if routine.enabled else 0,
                    last_run_str,
                    next_run_str,
                    routine.last_status.value if hasattr(routine.last_status, "value") else str(routine.last_status),
                    metadata_json,
                    routine.created_at.isoformat(),
                    now_str,
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_routine(self, routine_id: str) -> Optional[Routine]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, description, agent_id, prompt, schedule_type,
                       interval_seconds, cron_expression, enabled, last_run_at,
                       next_run_at, last_status, metadata_json, created_at, updated_at
                FROM routines WHERE id = ?
                """,
                (routine_id,),
            )
            r = cur.fetchone()
            if not r:
                return None

            meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
            last_run = datetime.fromisoformat(r["last_run_at"]) if r["last_run_at"] else None
            next_run = datetime.fromisoformat(r["next_run_at"]) if r["next_run_at"] else None

            return Routine(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                agent_id=r["agent_id"],
                prompt=r["prompt"],
                schedule_type=ScheduleType(r["schedule_type"]),
                interval_seconds=r["interval_seconds"],
                cron_expression=r["cron_expression"],
                enabled=bool(r["enabled"]),
                last_run_at=last_run,
                next_run_at=next_run,
                last_status=RoutineStatus(r["last_status"]),
                metadata=meta,
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            )
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_routines(
        self,
        enabled_only: bool = False,
        agent_id: Optional[str] = None,
    ) -> List[Routine]:
        query = "SELECT id, name, description, agent_id, prompt, schedule_type, interval_seconds, cron_expression, enabled, last_run_at, next_run_at, last_status, metadata_json, created_at, updated_at FROM routines WHERE 1=1"
        params: List[Any] = []
        if enabled_only:
            query += " AND enabled = 1"
        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
        query += " ORDER BY created_at ASC"

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            routines = []
            for r in rows:
                meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                last_run = datetime.fromisoformat(r["last_run_at"]) if r["last_run_at"] else None
                next_run = datetime.fromisoformat(r["next_run_at"]) if r["next_run_at"] else None
                routines.append(
                    Routine(
                        id=r["id"],
                        name=r["name"],
                        description=r["description"],
                        agent_id=r["agent_id"],
                        prompt=r["prompt"],
                        schedule_type=ScheduleType(r["schedule_type"]),
                        interval_seconds=r["interval_seconds"],
                        cron_expression=r["cron_expression"],
                        enabled=bool(r["enabled"]),
                        last_run_at=last_run,
                        next_run_at=next_run,
                        last_status=RoutineStatus(r["last_status"]),
                        metadata=meta,
                        created_at=datetime.fromisoformat(r["created_at"]),
                        updated_at=datetime.fromisoformat(r["updated_at"]),
                    )
                )
            return routines
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_routine(self, routine_id: str) -> bool:
        """Delete routine from SQLite storage (protects built-in routines)."""
        from src.domain.routines.manifests import BUILTIN_ROUTINES

        builtin_ids = {r.id for r in BUILTIN_ROUTINES}
        if routine_id in builtin_ids:
            return False

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM routines WHERE id = ?", (routine_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()

    def toggle_routine(self, routine_id: str) -> Optional[bool]:
        """Toggle enabled flag of a routine and return the new enabled state."""
        routine = self.get_routine(routine_id)
        if not routine:
            return None
        new_state = not routine.enabled
        routine.enabled = new_state
        self.save_routine(routine)
        return new_state

    def record_routine_run(self, run: RoutineRun) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO routine_runs (id, routine_id, agent_id, status, output, error_message, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.routine_id,
                    run.agent_id,
                    run.status.value if hasattr(run.status, "value") else str(run.status),
                    run.output,
                    run.error_message,
                    run.duration_ms,
                    run.created_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_routine_runs(self, routine_id: Optional[str] = None, limit: int = 50) -> List[RoutineRun]:
        query = "SELECT id, routine_id, agent_id, status, output, error_message, duration_ms, created_at FROM routine_runs WHERE 1=1"
        params: List[Any] = []
        if routine_id:
            query += " AND routine_id = ?"
            params.append(routine_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            return [
                RoutineRun(
                    id=r["id"],
                    routine_id=r["routine_id"],
                    agent_id=r["agent_id"],
                    status=RoutineStatus(r["status"]),
                    output=r["output"],
                    error_message=r["error_message"],
                    duration_ms=r["duration_ms"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                for r in rows
            ]
        finally:
            if self._mem_conn is None:
                conn.close()

    def set_setting(self, key: str, value: Any) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        val_json = json.dumps(value)
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, val_json, now_str),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_setting(self, key: str, default: Any = None) -> Any:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT value_json FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
            if not row:
                return default
            return json.loads(row["value_json"])
        finally:
            if self._mem_conn is None:
                conn.close()

    def save_agent_override(self, customization: AgentCustomization) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        tools_json = (
            json.dumps(customization.allowed_tool_names) if customization.allowed_tool_names is not None else None
        )
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO agent_overrides (agent_id, tone, system_prompt, model, allowed_tools_json, max_turns, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    tone = excluded.tone,
                    system_prompt = excluded.system_prompt,
                    model = excluded.model,
                    allowed_tools_json = excluded.allowed_tools_json,
                    max_turns = excluded.max_turns,
                    updated_at = excluded.updated_at
                """,
                (
                    customization.agent_id,
                    customization.tone,
                    customization.system_prompt,
                    customization.model,
                    tools_json,
                    customization.max_turns,
                    now_str,
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_agent_override(self, agent_id: str) -> Optional[AgentCustomization]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT agent_id, tone, system_prompt, model, allowed_tools_json, max_turns FROM agent_overrides WHERE agent_id = ?",
                (agent_id,),
            )
            r = cur.fetchone()
            if not r:
                return None
            tools = json.loads(r["allowed_tools_json"]) if r["allowed_tools_json"] else None
            return AgentCustomization(
                agent_id=r["agent_id"],
                tone=r["tone"],
                system_prompt=r["system_prompt"],
                model=r["model"],
                allowed_tool_names=tools,
                max_turns=r["max_turns"],
            )
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_agent_overrides(self) -> List[AgentCustomization]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT agent_id, tone, system_prompt, model, allowed_tools_json, max_turns FROM agent_overrides"
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                tools = json.loads(r["allowed_tools_json"]) if r["allowed_tools_json"] else None
                results.append(
                    AgentCustomization(
                        agent_id=r["agent_id"],
                        tone=r["tone"],
                        system_prompt=r["system_prompt"],
                        model=r["model"],
                        allowed_tool_names=tools,
                        max_turns=r["max_turns"],
                    )
                )
            return results
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_agent_override(self, agent_id: str) -> bool:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM agent_overrides WHERE agent_id = ?", (agent_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()

    def save_agent_profile(self, profile: AgentProfile) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        tools_json = json.dumps(profile.allowed_tool_names) if profile.allowed_tool_names is not None else None
        purpose_str = profile.purpose.value if hasattr(profile.purpose, "value") else str(profile.purpose)
        tone_str = profile.tone.value if hasattr(profile.tone, "value") else str(profile.tone)
        created_str = profile.created_at or now_str

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO custom_agents (
                    id, name, description, system_prompt, purpose, tone,
                    avatar_icon, model, allowed_tools_json, max_turns,
                    is_builtin, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    system_prompt = excluded.system_prompt,
                    purpose = excluded.purpose,
                    tone = excluded.tone,
                    avatar_icon = excluded.avatar_icon,
                    model = excluded.model,
                    allowed_tools_json = excluded.allowed_tools_json,
                    max_turns = excluded.max_turns,
                    is_builtin = excluded.is_builtin,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.id,
                    profile.name,
                    profile.description,
                    profile.system_prompt,
                    purpose_str,
                    tone_str,
                    profile.avatar_icon or "bot",
                    profile.model or "default",
                    tools_json,
                    profile.max_turns,
                    1 if profile.is_builtin else 0,
                    created_str,
                    now_str,
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_agent_profile(self, agent_id: str) -> Optional[AgentProfile]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, description, system_prompt, purpose, tone,
                       avatar_icon, model, allowed_tools_json, max_turns,
                       is_builtin, created_at, updated_at
                FROM custom_agents WHERE id = ?
                """,
                (agent_id,),
            )
            r = cur.fetchone()
            if not r:
                return None
            tools = json.loads(r["allowed_tools_json"]) if r["allowed_tools_json"] else []
            from src.domain.settings.models import ModelPurpose

            purpose_val = (
                ModelPurpose(r["purpose"]) if r["purpose"] in [p.value for p in ModelPurpose] else ModelPurpose.GENERAL
            )
            tone_val = AgentTone(r["tone"]) if r["tone"] in [t.value for t in AgentTone] else AgentTone.DEFAULT
            return AgentProfile(
                id=r["id"],
                name=r["name"],
                description=r["description"] or "",
                system_prompt=r["system_prompt"],
                purpose=purpose_val,
                tone=tone_val,
                avatar_icon=r["avatar_icon"] or "bot",
                model=r["model"] or "default",
                allowed_tool_names=tools,
                max_turns=r["max_turns"] or 10,
                is_builtin=bool(r["is_builtin"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_custom_agent_profiles(self) -> List[AgentProfile]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, description, system_prompt, purpose, tone,
                       avatar_icon, model, allowed_tools_json, max_turns,
                       is_builtin, created_at, updated_at
                FROM custom_agents
                ORDER BY created_at ASC
                """
            )
            rows = cur.fetchall()
            results = []
            from src.domain.settings.models import ModelPurpose

            for r in rows:
                tools = json.loads(r["allowed_tools_json"]) if r["allowed_tools_json"] else []
                purpose_val = (
                    ModelPurpose(r["purpose"])
                    if r["purpose"] in [p.value for p in ModelPurpose]
                    else ModelPurpose.GENERAL
                )
                tone_val = AgentTone(r["tone"]) if r["tone"] in [t.value for t in AgentTone] else AgentTone.DEFAULT
                results.append(
                    AgentProfile(
                        id=r["id"],
                        name=r["name"],
                        description=r["description"] or "",
                        system_prompt=r["system_prompt"],
                        purpose=purpose_val,
                        tone=tone_val,
                        avatar_icon=r["avatar_icon"] or "bot",
                        model=r["model"] or "default",
                        allowed_tool_names=tools,
                        max_turns=r["max_turns"] or 10,
                        is_builtin=bool(r["is_builtin"]),
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                    )
                )
            return results
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_agent_profile(self, agent_id: str) -> bool:
        from src.domain.agents.profiles import BUILTIN_PROFILES

        builtin_ids = {p.id for p in BUILTIN_PROFILES}
        if agent_id in builtin_ids:
            return False

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM custom_agents WHERE id = ?", (agent_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_kpi_summary(self, filter: Optional[TelemetryFilter] = None) -> KPIDashboardSummary:
        query = """
            SELECT
                COUNT(*) as total_turns,
                COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0) as total_tokens,
                COALESCE(AVG(duration_ms), 0.0) as avg_turn_duration_ms,
                COALESCE(SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END), 0) as error_count
            FROM telemetry_spans
            WHERE span_type = 'turn'
        """
        params: List[Any] = []
        if filter:
            if filter.agent_id:
                query += " AND agent_id = ?"
                params.append(filter.agent_id)
            if filter.session_id:
                query += " AND session_id = ?"
                params.append(filter.session_id)
            if filter.start_time:
                query += " AND created_at >= ?"
                params.append(filter.start_time.isoformat())
            if filter.end_time:
                query += " AND created_at <= ?"
                params.append(filter.end_time.isoformat())

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            row = cur.fetchone()
            if not row or row["total_turns"] == 0:
                return KPIDashboardSummary()

            total_turns = row["total_turns"]
            err_count = row["error_count"]
            err_rate = (err_count / total_turns * 100.0) if total_turns > 0 else 0.0

            return KPIDashboardSummary(
                total_turns=total_turns,
                total_prompt_tokens=row["total_prompt_tokens"],
                total_completion_tokens=row["total_completion_tokens"],
                total_tokens=row["total_tokens"],
                avg_turn_duration_ms=round(row["avg_turn_duration_ms"], 2),
                error_count=err_count,
                error_rate_pct=round(err_rate, 2),
            )
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_agent_kpi_breakdown(self) -> List[AgentKPISummary]:
        query = """
            SELECT
                agent_id,
                COALESCE(SUM(CASE WHEN span_type = 'turn' THEN 1 ELSE 0 END), 0) as turn_count,
                COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0) as total_tokens,
                COALESCE(SUM(CASE WHEN span_type = 'tool_call' OR span_type = 'tool' THEN 1 ELSE 0 END), 0) as tool_call_count,
                COALESCE(SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END), 0) as error_count,
                COALESCE(AVG(CASE WHEN span_type = 'turn' THEN duration_ms END), 0.0) as avg_duration_ms
            FROM telemetry_spans
            WHERE agent_id IS NOT NULL
            GROUP BY agent_id
            ORDER BY turn_count DESC
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            return [
                AgentKPISummary(
                    agent_id=r["agent_id"],
                    turn_count=r["turn_count"],
                    prompt_tokens=r["prompt_tokens"],
                    completion_tokens=r["completion_tokens"],
                    total_tokens=r["total_tokens"],
                    tool_call_count=r["tool_call_count"],
                    error_count=r["error_count"],
                    avg_duration_ms=round(r["avg_duration_ms"], 2),
                )
                for r in rows
            ]
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_tool_reliability_metrics(self) -> List[ToolReliabilityMetric]:
        query = """
            SELECT
                name as tool_name,
                COUNT(*) as total_invocations,
                COALESCE(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END), 0) as success_count,
                COALESCE(SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END), 0) as failure_count,
                COALESCE(AVG(duration_ms), 0.0) as avg_duration_ms
            FROM telemetry_spans
            WHERE span_type = 'tool_call' OR span_type = 'tool'
            GROUP BY name
            ORDER BY total_invocations DESC
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            metrics = []
            for r in rows:
                total = r["total_invocations"]
                succ = r["success_count"]
                rate = (succ / total * 100.0) if total > 0 else 100.0
                metrics.append(
                    ToolReliabilityMetric(
                        tool_name=r["tool_name"],
                        total_invocations=total,
                        success_count=succ,
                        failure_count=r["failure_count"],
                        success_rate_pct=round(rate, 2),
                        avg_duration_ms=round(r["avg_duration_ms"], 2),
                    )
                )
            return metrics
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_time_series_metrics(self, bucket_hours: int = 1, limit: int = 24) -> List[TimeSeriesDataPoint]:
        query = """
            SELECT
                strftime('%Y-%m-%d %H:00:00', created_at) as time_bucket,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0) as token_count,
                COALESCE(SUM(CASE WHEN span_type = 'turn' THEN 1 ELSE 0 END), 0) as turn_count,
                COALESCE(SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END), 0) as error_count
            FROM telemetry_spans
            GROUP BY time_bucket
            ORDER BY time_bucket DESC
            LIMIT ?
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, (limit,))
            rows = cur.fetchall()
            return [
                TimeSeriesDataPoint(
                    timestamp_bucket=r["time_bucket"] or "unknown",
                    token_count=r["token_count"],
                    turn_count=r["turn_count"],
                    error_count=r["error_count"],
                )
                for r in reversed(rows)
            ]
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_filtered_traces(
        self,
        filter: Optional[TelemetryFilter] = None,
        limit: int = 100,
    ) -> List[TelemetrySpan]:
        query = "SELECT id, session_id, agent_id, span_type, name, duration_ms, prompt_tokens, completion_tokens, success, error_message, metadata_json, created_at FROM telemetry_spans WHERE 1=1"
        params: List[Any] = []

        if filter:
            if filter.agent_id:
                query += " AND agent_id = ?"
                params.append(filter.agent_id)
            if filter.session_id:
                query += " AND session_id = ?"
                params.append(filter.session_id)
            if filter.span_type:
                query += " AND span_type = ?"
                params.append(filter.span_type)
            if filter.has_error is True:
                query += " AND success = 0"
            elif filter.has_error is False:
                query += " AND success = 1"
            if filter.start_time:
                query += " AND created_at >= ?"
                params.append(filter.start_time.isoformat())
            if filter.end_time:
                query += " AND created_at <= ?"
                params.append(filter.end_time.isoformat())

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            spans = []
            for r in rows:
                meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
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

    # -------------------------------------------------------------
    # Episodic Fact Storage [REQ-MEMORY-003]
    # -------------------------------------------------------------

    def save_fact(
        self,
        entity: str,
        key: str,
        value: str,
        confidence: float = 1.0,
        source_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert an episodic fact record into SQLite."""
        conn = self._get_connection()
        fact_id = str(uuid.uuid4())
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO episodic_facts (id, entity, key, value, confidence, source_session_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(entity, key) DO UPDATE SET
                    value = excluded.value,
                    confidence = excluded.confidence,
                    source_session_id = excluded.source_session_id,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (fact_id, entity, key, value, confidence, source_session_id),
            )
            conn.commit()
            return {
                "id": fact_id,
                "entity": entity,
                "key": key,
                "value": value,
                "confidence": confidence,
                "source_session_id": source_session_id,
            }
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_facts(self, entity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve episodic facts filtered optionally by entity."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if entity:
                cur.execute(
                    "SELECT id, entity, key, value, confidence, source_session_id, updated_at FROM episodic_facts WHERE entity = ? ORDER BY key ASC;",
                    (entity,),
                )
            else:
                cur.execute(
                    "SELECT id, entity, key, value, confidence, source_session_id, updated_at FROM episodic_facts ORDER BY entity ASC, key ASC;"
                )
            rows = cur.fetchall()
            return [
                {
                    "id": r["id"],
                    "entity": r["entity"],
                    "key": r["key"],
                    "value": r["value"],
                    "confidence": r["confidence"],
                    "source_session_id": r["source_session_id"],
                    "updated_at": str(r["updated_at"]),
                }
                for r in rows
            ]
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_fact(self, entity: str, key: str) -> bool:
        """Delete an episodic fact record by entity and key."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM episodic_facts WHERE entity = ? AND key = ?;", (entity, key))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()

    # -------------------------------------------------------------
    # Pending HITL Approvals [REQ-SAFE-004]
    # -------------------------------------------------------------

    def create_approval(
        self,
        session_id: str,
        agent_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> str:
        """Record a pending tool execution awaiting operator approval."""
        conn = self._get_connection()
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO pending_approvals (id, session_id, agent_id, tool_name, arguments_json, status)
                VALUES (?, ?, ?, ?, ?, 'pending');
                """,
                (approval_id, session_id, agent_id, tool_name, json.dumps(arguments)),
            )
            conn.commit()
            return approval_id
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_pending_approvals(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve list of pending approvals."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if session_id:
                cur.execute(
                    "SELECT id, session_id, agent_id, tool_name, arguments_json, status, decision_reason, created_at FROM pending_approvals WHERE session_id = ? AND status = 'pending' ORDER BY created_at ASC;",
                    (session_id,),
                )
            else:
                cur.execute(
                    "SELECT id, session_id, agent_id, tool_name, arguments_json, status, decision_reason, created_at FROM pending_approvals WHERE status = 'pending' ORDER BY created_at ASC;"
                )
            rows = cur.fetchall()
            return [
                {
                    "id": r["id"],
                    "session_id": r["session_id"],
                    "agent_id": r["agent_id"],
                    "tool_name": r["tool_name"],
                    "arguments": json.loads(r["arguments_json"]),
                    "status": r["status"],
                    "decision_reason": r["decision_reason"],
                    "created_at": str(r["created_at"]),
                }
                for r in rows
            ]
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_approval(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific approval record."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, session_id, agent_id, tool_name, arguments_json, status, decision_reason, created_at, resolved_at FROM pending_approvals WHERE id = ?;",
                (approval_id,),
            )
            r = cur.fetchone()
            if not r:
                return None
            return {
                "id": r["id"],
                "session_id": r["session_id"],
                "agent_id": r["agent_id"],
                "tool_name": r["tool_name"],
                "arguments": json.loads(r["arguments_json"]),
                "status": r["status"],
                "decision_reason": r["decision_reason"],
                "created_at": str(r["created_at"]),
                "resolved_at": str(r["resolved_at"]) if r["resolved_at"] else None,
            }
        finally:
            if self._mem_conn is None:
                conn.close()

    def resolve_approval(
        self,
        approval_id: str,
        decision: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Resolve a pending approval with 'approved' or 'rejected' decision."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE pending_approvals
                SET status = ?, decision_reason = ?, resolved_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending';
                """,
                (decision.lower(), reason, approval_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()
