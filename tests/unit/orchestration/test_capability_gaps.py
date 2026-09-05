"""
Unit tests for CapabilityGap Domain Model and Repository [REQ-FACT-027].
"""

import sqlite3

import pytest

from src.domain.orchestration.capability_gaps import CapabilityGap
from src.infrastructure.memory.repositories.capability_gaps import CapabilityGapRepository
from src.infrastructure.memory.schema import INIT_SCHEMA_SQL


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(INIT_SCHEMA_SQL)
    yield conn
    conn.close()


def test_capability_gap_model():
    gap = CapabilityGap(
        id="gap-001",
        agent_id="hyperv",
        session_id="sess-123",
        turn_text="create me a vm named billy",
        identified_capability="Create Hyper-V virtual machine",
        suggested_tool_name="manage_hyperv",
        status="pending",
    )
    assert gap.id == "gap-001"
    assert gap.agent_id == "hyperv"
    assert gap.turn_text == "create me a vm named billy"
    assert gap.status == "pending"


def test_capability_gap_repository_crud(db_conn):
    repo = CapabilityGapRepository(connection_factory=lambda: db_conn)

    # 1. Create gap
    gap = repo.create_gap(
        agent_id="hyperv",
        turn_text="can you delete vm billy",
        identified_capability="Delete Hyper-V virtual machine",
        suggested_tool_name="manage_hyperv",
        session_id="sess-abc",
    )
    assert gap.id.startswith("gap_")
    assert gap.agent_id == "hyperv"
    assert gap.status == "pending"

    # 2. Get gap
    fetched = repo.get_gap(gap.id)
    assert fetched is not None
    assert fetched.identified_capability == "Delete Hyper-V virtual machine"

    # 3. List gaps by agent
    gaps = repo.list_gaps(agent_id="hyperv")
    assert len(gaps) == 1
    assert gaps[0].id == gap.id

    # Other agent has no gaps
    other_gaps = repo.list_gaps(agent_id="coding")
    assert len(other_gaps) == 0

    # 4. Update status
    updated = repo.update_gap_status(gap.id, "trained")
    assert updated is True

    # After trained, pending list is empty
    pending = repo.list_gaps(agent_id="hyperv", status="pending")
    assert len(pending) == 0

    # All status returns the gap
    all_gaps = repo.list_gaps(agent_id="hyperv", status=None)
    assert len(all_gaps) == 1
    assert all_gaps[0].status == "trained"

    # 5. Delete gap
    deleted = repo.delete_gap(gap.id)
    assert deleted is True
    assert repo.get_gap(gap.id) is None
