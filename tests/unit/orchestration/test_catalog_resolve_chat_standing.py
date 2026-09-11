"""CARD-220 anti-theatre: Chat multi-step standing path uses catalog resolve."""

from __future__ import annotations

import ast
import inspect
import os
import tempfile

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.standing_job_graph import (
    StandingRoute,
    route_standing_chat,
)
from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    TrustTier,
)
from src.domain.orchestration.models import PhaseStatus
from src.infrastructure.memory.repositories.capability_catalog import (
    CapabilityCatalogRepository,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers import chat as chat_mod


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
            keywords=["wiki", "search", "notes", "research"],
            roles=["assistant"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.assistant",
            kind=CapabilityKind.AGENT,
            name="Assistant",
            summary="Day-to-day coordinator handoff",
            keywords=["assistant", "handoff", "coordinate"],
            roles=["assistant"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )


def test_req_catjob_chat_source_uses_catalog_resolve_not_plan_engine_only():
    """Chat multi-step standing path must call create_job_from_catalog_resolve [anti-theatre]."""
    src = inspect.getsource(chat_mod)
    assert "create_job_from_catalog_resolve" in src
    assert "catalog_resolved" in src
    # Multi-step branch must not require plan_engine formulate for standing catalog path.
    tree = ast.parse(src)
    found_catalog_call = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "create_job_from_catalog_resolve":
                found_catalog_call = True
            if isinstance(func, ast.Attribute) and func.attr == "formulate_plan":
                # Allowed elsewhere (deprecated goal endpoint); standing multi-step must also have catalog.
                pass
    assert found_catalog_call is True


def test_req_catjob_chat_standing_creates_rhe_via_catalog(orch, resolver, store):
    """Standing multi-step intent -> catalog R/H/E job (Chat-equivalent path) [REQ-CATJOB-001]."""
    _seed(resolver)
    multi = (
        "First research the wiki notes, then handoff to the assistant, "
        "finally execute a health verify."
    )
    assert route_standing_chat(multi) == StandingRoute.MULTI_STEP_JOB_GRAPH

    job = orch.create_job_from_catalog_resolve(
        intent=multi,
        session_id="sess_chat_standing",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    phases = store.list_phases_for_job(job.id)
    assert [p.name for p in phases] == ["Research", "Handoff", "Execute"]
    assert getattr(job, "template_id", None) == "catalog_resolve_rhe"
    matched = orch.matched_capability_ids_for_job(job.id)
    assert "tool.wiki_note_search" in matched
    assert all(p.status == PhaseStatus.QUEUED for p in phases)


def test_req_catjob_short_turn_stays_plain_react_routing():
    """Short turns remain SHORT_REACT (plain ReAct), not catalog Job/Phase."""
    assert route_standing_chat("What time is it") == StandingRoute.SHORT_REACT


def test_req_catjob_app_wires_capability_resolver_into_orchestrator():
    """App factory must pass capability_resolver so Chat catalog path is live."""
    from pathlib import Path

    app_src = Path("src/web/app.py").read_text(encoding="utf-8")
    assert "capability_resolver=capability_catalog" in app_src
