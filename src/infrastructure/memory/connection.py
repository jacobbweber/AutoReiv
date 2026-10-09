"""
Thread-Safe SQLite Connection & Migration Manager [REQ-KERNEL-004].
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.infrastructure.memory.schema import (
    CAPABILITY_CATALOG_SQL,
    INIT_SCHEMA_SQL,
    JOB_A2A_LINKS_SQL,
    JOB_PHASE_CHECKPOINTS_SQL,
    JOBS_PHASES_SQL,
    PROPOSALS_SQL,
    STANDING_JOURNEY_EVENTS_SQL,
)

logger = logging.getLogger(__name__)

# CARD-577 (ADR-0060, CARD-498/512): retired tables. On startup any rows are exported to
# <data>/backups/factory-retire-<timestamp>.json, then the tables are dropped. An export failure skips the drop.
# Settings no code reads or writes any more; deleted on start, nothing else is touched.
# day1_routines_seeded: the day-one routine seed flag, replaced by src/application/routines/seed.py (CARD-636, CARD-666).
RETIRED_SETTING_KEYS = ("day1_routines_seeded",)

RETIRED_TABLES = (
    "factory_packets",
    "factory_eval_runs",
    "factory_graphs",
    "factory_jobs",
    "factory_phase_instructions",
    "scaffold_spine",
)


class SQLiteConnectionManager:
    """Manages SQLite connections, pragmas, WAL mode, and schema migrations."""

    def __init__(self, db_path: Optional[str] = None):
        import os

        if db_path is not None:
            self.db_path = db_path
        elif os.environ.get("AUTOREIV_DB_PATH"):
            self.db_path = os.environ["AUTOREIV_DB_PATH"]
        else:
            # Live brain is under user data (AUTOREIV_DATA_DIR / platform default), never checkout ./data/
            from src.infrastructure.data.resolver import DataDirResolver

            self.db_path = str(DataDirResolver().resolve().db_path)
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
            self._drop_retired_tables(conn)
            self._drop_retired_settings(conn)
            conn.commit()
            if hasattr(self, "seed_builtin_prompts"):
                try:
                    self.seed_builtin_prompts()
                except Exception:
                    pass
        finally:
            if self._mem_conn is None:
                conn.close()

    def _drop_retired_settings(self, conn: sqlite3.Connection) -> None:
        """Delete obsolete setting keys (RETIRED_SETTING_KEYS) and only those [CARD-666]."""
        marks = ", ".join("?" for _ in RETIRED_SETTING_KEYS)
        conn.execute(f"DELETE FROM settings WHERE key IN ({marks})", RETIRED_SETTING_KEYS)

    def _drop_retired_tables(self, conn: sqlite3.Connection) -> None:
        """Export rows of retired tables (if any) to a backup file, then drop them [CARD-577]."""
        existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
        present = [t for t in RETIRED_TABLES if t in existing]
        if not present:
            return
        dump = {}
        for table in present:
            rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
            if rows:
                cols = [d[0] for d in conn.execute(f'SELECT * FROM "{table}" LIMIT 0').description]
                dump[table] = [dict(zip(cols, tuple(r))) for r in rows]
        if dump:
            if self.db_path == ":memory:":
                return  # nothing to write a backup next to; keep the rows
            try:
                backups = Path(self.db_path).resolve().parent.parent / "backups"
                backups.mkdir(parents=True, exist_ok=True)
                out = backups / f"factory-retire-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
                out.write_text(json.dumps(dump, default=str, indent=1), encoding="utf-8")
                logger.info("Retired tables exported to %s: %s", out, {k: len(v) for k, v in dump.items()})
            except Exception as exc:  # noqa: BLE001 - never block startup; keep the tables
                logger.warning("Retired-table export failed; tables kept: %s", exc)
                return
        conn.execute("PRAGMA foreign_keys = OFF;")
        try:
            for table in present:
                conn.execute(f'DROP TABLE IF EXISTS "{table}"')
            conn.commit()
        finally:
            conn.execute("PRAGMA foreign_keys = ON;")

    def _migrate_if_missing(self, conn: sqlite3.Connection) -> None:
        """Add new tables/columns on a live DB without wiping data [REQ-ORCH-031]."""
        for table, col, decl in (
            ("pending_approvals", "routine_id", "TEXT"),
            ("telemetry_spans", "trace_id", "TEXT"),
            ("telemetry_spans", "parent_span_id", "TEXT"),
            ("telemetry_spans", "provider", "TEXT"),
            ("telemetry_spans", "model", "TEXT"),
            ("telemetry_spans", "ttft_ms", "REAL"),
            ("telemetry_spans", "status", "TEXT DEFAULT 'ok'"),
            ("routine_runs", "job_id", "TEXT"),
            ("jobs", "success_rule", "TEXT NOT NULL DEFAULT ''"),
            ("messages", "reasoning", "TEXT"),
            ("agent_capability_gaps", "context_summary", "TEXT"),  # CARD-664
        ):
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
            except sqlite3.OperationalError:
                pass

        existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
        if "jobs" not in existing or "phases" not in existing:
            conn.executescript(JOBS_PHASES_SQL)
        if "proposals" not in existing:
            conn.executescript(PROPOSALS_SQL)
        if "capability_index" not in existing:
            conn.executescript(CAPABILITY_CATALOG_SQL)
        if "tool_policy_decisions" not in existing:
            from src.infrastructure.memory.schema import TOOL_POLICY_DECISIONS_SQL

            conn.executescript(TOOL_POLICY_DECISIONS_SQL)
        else:
            try:
                conn.execute("ALTER TABLE tool_policy_decisions ADD COLUMN job_id TEXT")
            except sqlite3.OperationalError:
                pass
        if "job_a2a_links" not in existing:
            conn.executescript(JOB_A2A_LINKS_SQL)
        if "standing_journey_events" not in existing:
            conn.executescript(STANDING_JOURNEY_EVENTS_SQL)
        if "job_phase_checkpoints" not in existing:
            conn.executescript(JOB_PHASE_CHECKPOINTS_SQL)
        else:
            try:
                conn.execute(
                    "ALTER TABLE job_phase_checkpoints "
                    "ADD COLUMN matched_capability_ids_json TEXT NOT NULL DEFAULT '[]'"
                )
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute(
                    "ALTER TABLE job_phase_checkpoints ADD COLUMN memory_fact_ids_json TEXT NOT NULL DEFAULT '[]'"
                )
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute(
                    "ALTER TABLE job_phase_checkpoints ADD COLUMN research_inserted INTEGER NOT NULL DEFAULT 0"
                )
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE job_phase_checkpoints ADD COLUMN research_reason TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE job_phase_checkpoints ADD COLUMN replan_count INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE job_phase_checkpoints ADD COLUMN last_fail_reason TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass
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
        if "credentials" not in existing:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS credentials (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    encrypted_value TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        if "remote_hosts" not in existing:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS remote_hosts (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL DEFAULT 22,
                    username TEXT NOT NULL,
                    auth_type TEXT NOT NULL DEFAULT 'password',
                    credential_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_remote_hosts_label ON remote_hosts(label);")
        if "agent_capability_gaps" not in existing:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_capability_gaps (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    session_id TEXT,
                    turn_text TEXT NOT NULL,
                    identified_capability TEXT NOT NULL,
                    suggested_tool_name TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    context_summary TEXT
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gaps_agent_status ON agent_capability_gaps(agent_id, status);")

        # CARD-341: migrate retired platform agents (assistant, wiki) in existing databases
        if "routines" in existing:
            try:
                conn.execute(
                    "UPDATE routines SET agent_id = 'tutor' WHERE agent_id IN ('assistant', 'wiki') AND id = 'education-retrieval-retention';"
                )
                conn.execute("UPDATE routines SET agent_id = 'autoreiv' WHERE agent_id IN ('assistant', 'wiki');")
            except sqlite3.OperationalError:
                pass
        if "sessions" in existing:
            try:
                conn.execute("UPDATE sessions SET agent_id = 'autoreiv' WHERE agent_id IN ('assistant', 'wiki');")
            except sqlite3.OperationalError:
                pass
        if "chat_messages" in existing:
            try:
                conn.execute("UPDATE chat_messages SET agent_id = 'autoreiv' WHERE agent_id IN ('assistant', 'wiki');")
            except sqlite3.OperationalError:
                pass

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
