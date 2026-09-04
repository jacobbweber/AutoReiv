"""
Thread-Safe SQLite Connection & Migration Manager [REQ-KERNEL-004].
"""

import sqlite3
from pathlib import Path
from typing import Optional

from src.infrastructure.memory.schema import INIT_SCHEMA_SQL, JOBS_PHASES_SQL, PROPOSALS_SQL


class SQLiteConnectionManager:
    """Manages SQLite connections, pragmas, WAL mode, and schema migrations."""

    def __init__(self, db_path: Optional[str] = None):
        import os

        self.db_path = db_path if db_path is not None else os.environ.get("AUTOREIV_DB_PATH", "./data/autoreiv.db")
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row
            self._mem_conn.execute("PRAGMA foreign_keys = ON;")
        else:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
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

            self._migrate_if_missing(conn)
            conn.executescript(INIT_SCHEMA_SQL)
            conn.commit()
            if hasattr(self, "seed_builtin_prompts"):
                try:
                    self.seed_builtin_prompts()
                except Exception:
                    pass
        finally:
            if self._mem_conn is None:
                conn.close()

    def _migrate_if_missing(self, conn: sqlite3.Connection) -> None:
        """Add new tables/columns on a live DB without wiping data [REQ-ORCH-031]."""
        for table, col, decl in (
            ("agent_overrides", "provider", "TEXT DEFAULT 'default'"),
            ("agent_overrides", "history_retention_days", "INTEGER DEFAULT 30"),
            ("agent_overrides", "purpose", "TEXT"),
            ("agent_overrides", "allowed_skills_json", "TEXT"),
            ("agent_overrides", "pack_tools_json", "TEXT"),
            ("agent_overrides", "show_in_chat", "INTEGER DEFAULT 1"),
            ("custom_agents", "provider", "TEXT DEFAULT 'default'"),
            ("custom_agents", "history_retention_days", "INTEGER DEFAULT 30"),
            ("custom_agents", "allowed_skills_json", "TEXT"),
            ("custom_agents", "pack_tools_json", "TEXT"),
            ("custom_agents", "show_in_chat", "INTEGER DEFAULT 1"),
            ("pending_approvals", "routine_id", "TEXT"),
            ("telemetry_spans", "trace_id", "TEXT"),
            ("telemetry_spans", "parent_span_id", "TEXT"),
            ("telemetry_spans", "provider", "TEXT"),
            ("telemetry_spans", "model", "TEXT"),
            ("telemetry_spans", "ttft_ms", "REAL"),
            ("telemetry_spans", "status", "TEXT DEFAULT 'ok'"),
        ):
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
            except sqlite3.OperationalError:
                pass

        existing = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if "jobs" not in existing or "phases" not in existing:
            conn.executescript(JOBS_PHASES_SQL)
        if "proposals" not in existing:
            conn.executescript(PROPOSALS_SQL)
        if "prompt_catalog" not in existing:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_catalog (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT DEFAULT 'general',
                    template_text TEXT NOT NULL,
                    tags TEXT,
                    is_builtin INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prompt_category ON prompt_catalog(category);")

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
