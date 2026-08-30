"""
Proposals SQLite schema and migrate-if-missing [REQ-ORCH-043].
"""

import os
import sqlite3
import tempfile

import pytest
from pydantic import ValidationError

from src.domain.orchestration.errors import InvalidProposalStatusError, ProposalNotFoundError
from src.domain.orchestration.models import Proposal, ProposalKind, ProposalStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

_OLD_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    budget_max_phases INTEGER NOT NULL DEFAULT 16,
    budget_max_handoffs INTEGER NOT NULL DEFAULT 4,
    budget_max_ollama_slots INTEGER NOT NULL DEFAULT 1,
    current_phase_id TEXT,
    template_id TEXT,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_REQUIRED_COLUMNS = {
    "id",
    "kind",
    "payload_json",
    "status",
    "requested_by_job_id",
    "created_at",
    "updated_at",
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


def test_proposals_table_has_locked_columns(store, temp_db_path):
    conn = sqlite3.connect(temp_db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "proposals" in tables
        assert _REQUIRED_COLUMNS <= _column_names(conn, "proposals")
        indexes = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall() if row[0]
        }
        assert "idx_proposals_parent" in indexes
        assert "idx_proposals_status" in indexes
    finally:
        conn.close()


def test_domain_model_rejects_invalid_proposal_status():
    with pytest.raises(ValidationError):
        Proposal(id="p1", kind="followup_job", payload_json="{}", status="queued")
    with pytest.raises(ValidationError):
        Proposal(id="p1", kind="not_a_kind", payload_json="{}")


def test_repository_rejects_invalid_status(store):
    proposal = store.create_proposal(
        Proposal(
            id="prop_ok",
            kind=ProposalKind.FOLLOWUP_JOB,
            payload_json='{"goal":"x"}',
            status=ProposalStatus.DRAFT,
            requested_by_job_id="job_parent",
        )
    )
    assert proposal.status == ProposalStatus.DRAFT
    with pytest.raises(InvalidProposalStatusError):
        store.update_proposal_status("prop_ok", "queued")


def test_migrate_if_missing_adds_proposals_on_old_db(temp_db_path):
    conn = sqlite3.connect(temp_db_path)
    try:
        conn.executescript(_OLD_SCHEMA_SQL)
        conn.commit()
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "proposals" not in tables
    finally:
        conn.close()

    store = SQLiteStateStore(db_path=temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "proposals" in tables
        assert _REQUIRED_COLUMNS <= _column_names(conn, "proposals")
    finally:
        conn.close()
    created = store.create_proposal(
        Proposal(id="prop_mig", kind="followup_job", payload_json='{"goal":"after migrate"}', status="draft")
    )
    assert created.payload_json == '{"goal":"after migrate"}'


def test_get_unknown_proposal_raises(store):
    with pytest.raises(ProposalNotFoundError):
        store.get_proposal("prop_nope")
