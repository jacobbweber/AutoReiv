"""
Job/Phase SQLite schema, migrate-if-missing, and repository tests
[REQ-ORCH-031, REQ-ORCH-032, REQ-ORCH-033].
"""

import os
import sqlite3
import tempfile

import pytest
from pydantic import ValidationError

from src.domain.orchestration.errors import InvalidJobStatusError, JobNotFoundError, MissingParentJobError
from src.domain.orchestration.models import HandoffPacket, Job, JobStatus, Phase, PhaseStatus, ReactState
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

# Snapshot of INIT_SCHEMA_SQL before CARD-096 jobs/phases tables.
_OLD_SCHEMA_SQL = """
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
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_REQUIRED_JOB_COLUMNS = {
    "id",
    "goal",
    "status",
    "budget_max_phases",
    "budget_max_handoffs",
    "budget_max_ollama_slots",
    "current_phase_id",
    "template_id",
    "created_at",
    "updated_at",
    "session_id",
    "agent_id",
}
_REQUIRED_PHASE_COLUMNS = {
    "id",
    "job_id",
    "name",
    "index",
    "assigned_agent_id",
    "status",
    "success_rule",
    "verify_checker",
    "input_packet_json",
    "output_packet_json",
    "parent_phase_id",
    "max_turns",
    "react_state",
}


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.fixture
def store(temp_db_path):
    return SQLiteStateStore(db_path=temp_db_path)


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_jobs_and_phases_tables_have_locked_columns(store, temp_db_path):
    conn = sqlite3.connect(temp_db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "jobs" in tables
        assert "phases" in tables
        assert "tasks" in tables  # todo list stays; jobs is a different table
        job_cols = _column_names(conn, "jobs")
        phase_cols = _column_names(conn, "phases")
        assert _REQUIRED_JOB_COLUMNS <= job_cols
        assert _REQUIRED_PHASE_COLUMNS <= phase_cols
        indexes = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall() if row[0]
        }
        assert "idx_jobs_session" in indexes
        assert "idx_phases_job" in indexes
    finally:
        conn.close()


def test_repository_rejects_invalid_job_status(store):
    job = Job(
        id="job_badstatus",
        goal="x",
        session_id="sess_1",
        agent_id="assistant",
        status=JobStatus.QUEUED,
    )
    store.create_job(job)
    with pytest.raises(InvalidJobStatusError):
        store.update_job_status("job_badstatus", "graph_running")


def test_domain_model_rejects_invalid_status_string():
    with pytest.raises(ValidationError):
        Job(id="job_x", goal="g", session_id="s", agent_id="a", status="graph_running")
    with pytest.raises(ValidationError):
        Phase(
            id="phase_x",
            job_id="job_x",
            name="n",
            index=0,
            assigned_agent_id="a",
            status="dag_wait",
        )


def test_repository_rejects_phase_without_parent_job(store):
    orphan = Phase(
        id="phase_orphan",
        job_id="job_missing",
        name="Chat",
        index=0,
        assigned_agent_id="assistant",
    )
    with pytest.raises(MissingParentJobError):
        store.create_phase(orphan)


def test_create_get_list_phases_ordered_by_index(store):
    job = Job(id="job_linear", goal="Ship CARD-096", session_id="sess_q", agent_id="assistant")
    p1 = Phase(id="phase_b", job_id="job_linear", name="Verify", index=1, assigned_agent_id="assistant")
    p0 = Phase(id="phase_a", job_id="job_linear", name="Draft", index=0, assigned_agent_id="assistant")
    store.create_job(job, [p1, p0])
    fetched = store.get_job("job_linear")
    assert fetched.goal == "Ship CARD-096"
    assert fetched.status == JobStatus.QUEUED
    phases = store.list_phases_for_job("job_linear")
    assert [phase.index for phase in phases] == [0, 1]
    assert [phase.name for phase in phases] == ["Draft", "Verify"]
    assert store.get_phase("phase_a").name == "Draft"


def test_repository_survives_reopen(store, temp_db_path):
    job = Job(
        id="job_persist",
        goal="durable",
        session_id="sess_p",
        agent_id="coding",
        current_phase_id="phase_p0",
        status=JobStatus.RUNNING,
    )
    phase = Phase(
        id="phase_p0",
        job_id="job_persist",
        name="Chat",
        index=0,
        assigned_agent_id="coding",
        status=PhaseStatus.RUNNING,
        react_state=ReactState.THINKING,
        input_packet_json=HandoffPacket(goal="durable", facts=[], constraints=[], done_when="done").model_dump_json(),
    )
    store.create_job(job, [phase])
    reopened = SQLiteStateStore(db_path=temp_db_path)
    loaded = reopened.get_job("job_persist")
    assert loaded.status == JobStatus.RUNNING
    assert loaded.current_phase_id == "phase_p0"
    loaded_phases = reopened.list_phases_for_job("job_persist")
    assert len(loaded_phases) == 1
    assert loaded_phases[0].react_state == ReactState.THINKING


def test_migrate_if_missing_adds_jobs_phases_on_old_db(temp_db_path):
    conn = sqlite3.connect(temp_db_path)
    try:
        conn.executescript(_OLD_SCHEMA_SQL)
        conn.execute("INSERT INTO settings (key, value_json) VALUES ('theme', '\"dark\"')")
        conn.commit()
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "jobs" not in tables
        assert "phases" not in tables
    finally:
        conn.close()

    store = SQLiteStateStore(db_path=temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "jobs" in tables
        assert "phases" in tables
        job_cols = _column_names(conn, "jobs")
        phase_cols = _column_names(conn, "phases")
        assert _REQUIRED_JOB_COLUMNS <= job_cols
        assert _REQUIRED_PHASE_COLUMNS <= phase_cols
        theme = conn.execute("SELECT value_json FROM settings WHERE key = 'theme'").fetchone()
        assert theme[0] == '"dark"'
    finally:
        conn.close()

    job = Job(id="job_migrated", goal="after migrate", session_id="sess_m", agent_id="assistant")
    store.create_job(job)
    assert store.get_job("job_migrated").goal == "after migrate"


def test_list_phases_unknown_job_raises(store):
    with pytest.raises(JobNotFoundError):
        store.list_phases_for_job("job_nope")
