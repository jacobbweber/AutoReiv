"""CARD-224: A2A handoff inherits standing Job/Phase path (thin slice)."""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.standing_a2a_handoff import (
    child_ids_do_not_widen,
    create_standing_child_job,
    linked_child_job_ids,
    matched_ids_for_parent,
)
from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    TrustTier,
)
from src.infrastructure.memory.repositories.capability_catalog import (
    CapabilityCatalogRepository,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


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


@pytest.fixture
def resolver(store):
    return CapabilityCatalogResolver(CapabilityCatalogRepository(store))


@pytest.fixture
def orch(store, resolver):
    return JobPhaseOrchestrator(store, capability_resolver=resolver)


def _seed(resolver: CapabilityCatalogResolver) -> None:
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.wiki_note_search",
            kind=CapabilityKind.TOOL,
            name="wiki_note_search",
            summary="Search wiki notes",
            keywords=["wiki", "search", "notes", "research", "fleet", "health"],
            roles=["assistant", "autoreiv"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.assistant",
            kind=CapabilityKind.AGENT,
            name="Assistant",
            summary="Day-to-day coordinator handoff",
            keywords=["assistant", "handoff", "coordinate"],
            roles=["assistant", "autoreiv"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )


def test_child_ids_do_not_widen_helper():
    assert child_ids_do_not_widen(["a", "b"], ["a"]) is True
    assert child_ids_do_not_widen(["a", "b"], ["a", "b"]) is True
    assert child_ids_do_not_widen(["a", "b"], ["a", "c"]) is False


def test_create_standing_child_job_inherits_matched_ids(store, orch, resolver):
    _seed(resolver)
    parent = orch.create_job_from_catalog_resolve(
        intent="First research wiki, then handoff to assistant, finally verify health.",
        session_id="sess-parent",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    parent_ids = matched_ids_for_parent(orch, parent.id)
    assert parent_ids

    child = create_standing_child_job(
        orch,
        parent_job_id=parent.id,
        intent="Handoff specialist: deepen wiki research findings.",
        session_id="sess-parent_child_abc",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    assert child.id != parent.id
    assert child.template_id == "catalog_resolve_rhe"
    child_ids = matched_ids_for_parent(orch, child.id)
    assert child_ids == parent_ids
    assert linked_child_job_ids(orch, parent.id) == [child.id]
    assert child_ids_do_not_widen(parent_ids, child_ids)


def test_child_policy_block_cannot_widen_beyond_parent_subset(store, orch, resolver):
    """BLOCK on parent capability subset remains BLOCK after handoff [CARD-224]."""
    from src.application.safety.tool_policy_gate import _capability_tool_names

    _seed(resolver)
    parent = orch.create_job_from_catalog_resolve(
        intent="First research wiki, then handoff to assistant, finally verify.",
        session_id="sess-pol",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    parent_ids = matched_ids_for_parent(orch, parent.id)
    child = create_standing_child_job(
        orch,
        parent_job_id=parent.id,
        intent="Child deepen research",
        session_id="sess-pol_child_1",
        agent_id="assistant",
    )
    child_ids = matched_ids_for_parent(orch, child.id)
    assert child_ids == parent_ids
    parent_tools = _capability_tool_names(parent_ids)
    child_tools = _capability_tool_names(child_ids)
    assert parent_tools == child_tools
    # cli_exec not in matched tool.* subset => capability_subset BLOCK on both
    assert "cli_exec" not in (parent_tools or set())
    assert "cli_exec" not in (child_tools or set())
