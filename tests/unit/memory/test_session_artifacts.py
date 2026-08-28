"""
Unit tests for Session Artifact Store & TTL Garbage Collection [REQ-ART-001, REQ-ART-002].
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from src.domain.memory.models import SessionArtifact
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


@pytest.fixture
def store(temp_db_path):
    s = SQLiteStateStore(db_path=temp_db_path)
    s.initialize_db()
    return s


def test_session_artifact_crud(store):
    session = store.create_session(agent_id="assistant", title="Codebase Audit")

    artifact = SessionArtifact(
        id="art_test_123",
        session_id=session.id,
        title="Router Security Audit",
        content_type="text/markdown",
        content="# Audit Report\n- Finding 1: Unvalidated query param\n- Finding 2: Rate limit missing",
        summary="Found 2 security findings across 12 router files.",
        item_count=12,
        is_pinned=False,
    )

    saved = store.save_artifact(artifact)
    assert saved.id == "art_test_123"
    assert saved.session_id == session.id
    assert saved.is_pinned is False
    assert saved.expires_at is not None

    fetched = store.get_artifact("art_test_123")
    assert fetched is not None
    assert fetched.title == "Router Security Audit"
    assert fetched.item_count == 12
    assert "Finding 1" in fetched.content

    artifacts = store.list_session_artifacts(session.id)
    assert len(artifacts) == 1
    assert artifacts[0].id == "art_test_123"

    # Test Pinning
    pinned = store.pin_artifact("art_test_123", is_pinned=True)
    assert pinned is True
    fetched_pinned = store.get_artifact("art_test_123")
    assert fetched_pinned.is_pinned is True

    # Test Delete
    deleted = store.delete_artifact("art_test_123")
    assert deleted is True
    assert store.get_artifact("art_test_123") is None


def test_session_artifact_cascade_deletion(store):
    session = store.create_session(agent_id="assistant", title="Ephemeral Session")

    art1 = SessionArtifact(
        id="art_casc_1",
        session_id=session.id,
        title="Batch Scan 1",
        content="Log 1 details",
        summary="Scan 1 summary",
    )
    art2 = SessionArtifact(
        id="art_casc_2",
        session_id=session.id,
        title="Batch Scan 2",
        content="Log 2 details",
        summary="Scan 2 summary",
    )
    store.save_artifact(art1)
    store.save_artifact(art2)
    assert len(store.list_session_artifacts(session.id)) == 2

    # Deleting the parent session cascades to delete all linked artifacts
    store.delete_session(session.id)
    assert store.get_artifact("art_casc_1") is None
    assert store.get_artifact("art_casc_2") is None


def test_session_artifact_ttl_pruning(store):
    session = store.create_session(agent_id="assistant", title="TTL Test")

    # 1. Expired unpinned artifact (expires in the past)
    expired_art = SessionArtifact(
        id="art_expired",
        session_id=session.id,
        title="Old Scan",
        content="Old content",
        summary="Old summary",
        is_pinned=False,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    # 2. Expired but PINNED artifact (should NOT be pruned)
    pinned_art = SessionArtifact(
        id="art_pinned_past",
        session_id=session.id,
        title="Pinned Important Scan",
        content="Important content",
        summary="Important summary",
        is_pinned=True,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    # 3. Active unpinned artifact (expires in the future)
    future_art = SessionArtifact(
        id="art_future",
        session_id=session.id,
        title="Recent Scan",
        content="Recent content",
        summary="Recent summary",
        is_pinned=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    store.save_artifact(expired_art)
    store.save_artifact(pinned_art)
    store.save_artifact(future_art)

    pruned_count = store.prune_expired_artifacts()
    assert pruned_count == 1

    assert store.get_artifact("art_expired") is None
    assert store.get_artifact("art_pinned_past") is not None
    assert store.get_artifact("art_future") is not None
