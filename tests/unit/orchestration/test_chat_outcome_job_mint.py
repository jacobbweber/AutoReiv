"""CARD-236: Chat outcome ask always mints standing Job [REQ-JOBMINT-001..004].

Wave-2 gap: CoS #2 Wiki create with done-when used ReAct wiki_note_create and
journey jobs=[] — standing Chat must mint a durable Job before phase 1.
"""

from __future__ import annotations

import inspect
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.observability.standing_journey import build_standing_journey
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.outcome_intake import (
    derive_success_rule,
    is_outcome_shaped,
    is_testable_success_rule,
)
from src.application.orchestration.standing_job_graph import (
    StandingRoute,
    route_standing_chat,
)
from src.domain.capabilities.models import CapabilityIndexEntry, CapabilityKind
from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import KernelEvent, KernelEventType
from src.infrastructure.memory.repositories.capability_catalog import (
    CapabilityCatalogRepository,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app
from src.web.routers import chat as chat_mod

# Exact operator ask #2 from session 44bf694d (wave-2 eval).
COS_ASK_2_WIKI = (
    "Create a short Wiki note that explains what a Job is in AutoReiv, "
    "with a clear done-when: the note exists in Wiki and I can open it."
)


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


def _seed_wiki(resolver: CapabilityCatalogResolver) -> None:
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.wiki_note_create",
            kind=CapabilityKind.TOOL,
            name="wiki_note_create",
            summary="Create a wiki note in the vault",
            keywords=["wiki", "note", "create", "write", "author"],
            roles=["assistant"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.wiki_note_read",
            kind=CapabilityKind.TOOL,
            name="wiki_note_read",
            summary="Read a wiki note",
            keywords=["wiki", "note", "read", "open"],
            roles=["assistant"],
        )
    )


# --- REQ-JOBMINT-001 --------------------------------------------------------


def test_req_jobmint_001_cos_ask2_wiki_is_outcome_shaped():
    """CoS #2 Wiki + done-when must classify as outcome-shaped [REQ-JOBMINT-001]."""
    assert is_outcome_shaped(COS_ASK_2_WIKI) is True
    assert route_standing_chat(COS_ASK_2_WIKI) == StandingRoute.MULTI_STEP_JOB_GRAPH


def test_req_jobmint_001_wiki_write_variants_route_to_job_graph():
    """Wiki-write deliverables (create/write/save note) mint Jobs, not ReAct-only."""
    variants = [
        COS_ASK_2_WIKI,
        "Write a wiki note titled What is a Job in AutoReiv and save it.",
        "Please create a Wiki note explaining what a Job is in AutoReiv.",
        "Author a short wiki note about Jobs; done when the note exists.",
        "Save a new wiki note that documents the standing Job spine.",
    ]
    for ask in variants:
        assert is_outcome_shaped(ask) is True, f"expected outcome-shaped: {ask!r}"
        assert route_standing_chat(ask) == StandingRoute.MULTI_STEP_JOB_GRAPH, ask


def test_req_jobmint_001_done_when_hyphen_extracts_testable_rule():
    """Hyphenated done-when: must yield a testable success_rule [REQ-JOBMINT-001]."""
    rule = derive_success_rule(COS_ASK_2_WIKI)
    assert is_testable_success_rule(rule)
    low = rule.lower()
    assert "exists" in low
    # Prefer the operator's stop condition, not a vague synthesize-only wrap of the whole ask.
    assert "outcome verified" not in low
    assert low.startswith("done when")


def test_req_jobmint_001_outcome_wiki_creates_durable_job_row(orch, resolver, store):
    """Outcome Wiki-create ask → durable Job before phase 1; never empty [REQ-JOBMINT-001]."""
    _seed_wiki(resolver)
    job = orch.create_job_from_catalog_resolve(
        intent=COS_ASK_2_WIKI,
        session_id="sess_jobmint_001",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    assert job.id
    assert (job.success_rule or "").strip()
    reloaded = store.get_job(job.id)
    assert reloaded is not None
    assert reloaded.session_id == "sess_jobmint_001"
    phases = store.list_phases_for_job(job.id)
    assert len(phases) >= 1
    jobs = store.list_jobs_for_session("sess_jobmint_001")
    assert len(jobs) >= 1
    assert jobs[0].id == job.id


# --- REQ-JOBMINT-002 --------------------------------------------------------


def test_req_jobmint_002_journey_spans_for_minted_job(orch, resolver, store):
    """Observability standing-journey by job_id shows intake → phases [REQ-JOBMINT-002]."""
    _seed_wiki(resolver)
    job = orch.create_job_from_catalog_resolve(
        intent=COS_ASK_2_WIKI,
        session_id="sess_jobmint_002",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    journey = build_standing_journey(store, job_id=job.id)
    assert journey.get("ok") is not False
    assert journey["job_id"] == job.id
    timeline = journey.get("timeline") or []
    spans = journey.get("spans") or []
    assert timeline or spans, "journey must be non-empty after mint"
    # Phases exist on the job (intake → phase structure).
    phases = store.list_phases_for_job(job.id)
    assert len(phases) >= 1


# --- REQ-JOBMINT-003 --------------------------------------------------------


def test_req_jobmint_003_short_chitchat_stays_plain_react_no_job(orch, store):
    """Short chitchat stays ReAct — no Job mint [REQ-JOBMINT-003]."""
    chitchat = "Hey — what’s the weather metaphor for a control plane in one sentence?"
    assert is_outcome_shaped(chitchat) is False
    assert route_standing_chat(chitchat) == StandingRoute.SHORT_REACT
    assert store.list_jobs_for_session("sess_jobmint_chitchat") == []


# --- REQ-JOBMINT-004 / Chat stream path -------------------------------------


async def _fake_stream_turn(
    agent,
    session_id,
    user_content=None,
    approval_mode="ask",
    resume=False,
    **kwargs,
):
    job_id = kwargs.get("job_id")
    phase_id = kwargs.get("phase_id")
    agent_id = getattr(agent, "id", None)
    yield KernelEvent(
        event_type=KernelEventType.REACT_STATE,
        react={
            "react_state": "THINKING",
            "job_id": job_id,
            "phase_id": phase_id,
            "assigned_agent_id": agent_id,
        },
    )
    yield KernelEvent(event_type=KernelEventType.TOKEN, content="wiki note ready")
    yield KernelEvent(
        event_type=KernelEventType.REACT_STATE,
        react={
            "react_state": "DONE",
            "job_id": job_id,
            "phase_id": phase_id,
            "assigned_agent_id": agent_id,
        },
    )
    yield KernelEvent(
        event_type=KernelEventType.TURN_END,
        content="wiki note ready",
        is_finished=True,
    )


@pytest.fixture
def jobmint_app():
    store = SQLiteStateStore(db_path=":memory:")
    app = create_app(state_store=store)
    app.state.store.create_session(
        session_id="sess_jobmint_stream", agent_id="assistant", title="Jobmint"
    )
    app.state.store.create_session(
        session_id="sess_jobmint_chitchat_stream",
        agent_id="assistant",
        title="Chitchat",
    )
    # Seed wiki capabilities so catalog resolve is non-empty.
    cap = getattr(app.state, "capability_catalog", None)
    if cap is not None:
        _seed_wiki(cap)
    app.state.kernel.gateway.complete = AsyncMock(
        return_value=MagicMock(
            message=ChatMessage(role=Role.ASSISTANT, content='{"steps": []}')
        )
    )
    app.state.kernel.run_turn = AsyncMock(
        side_effect=AssertionError("outcome mint must not use run_turn planner")
    )
    app.state.kernel.stream_turn = _fake_stream_turn
    return app


@pytest.mark.asyncio
async def test_req_jobmint_001_004_chat_stream_wiki_ask_mints_job(jobmint_app):
    """Live Chat stream path: Wiki outcome ask → job_created + jobs non-empty."""
    transport = ASGITransport(app=jobmint_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "sess_jobmint_stream",
                "content": COS_ASK_2_WIKI,
                "goal_mode": False,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: job_created" in body
        assert "outcome_intake" in body or "catalog_resolve" in body

    jobs = jobmint_app.state.store.list_jobs_for_session("sess_jobmint_stream")
    assert jobs, "REQ-JOBMINT-001: never jobs=[] after successful outcome reply"
    job = jobs[0]
    assert (job.success_rule or "").strip()
    journey = build_standing_journey(jobmint_app.state.store, job_id=job.id)
    assert journey["job_id"] == job.id
    assert (journey.get("timeline") or journey.get("spans")), "REQ-JOBMINT-002"


@pytest.mark.asyncio
async def test_req_jobmint_003_chat_stream_chitchat_no_job(jobmint_app):
    """Chat stream chitchat → no job_created / jobs=[] [REQ-JOBMINT-003]."""
    transport = ASGITransport(app=jobmint_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "sess_jobmint_chitchat_stream",
                "content": "Hey — what’s the weather metaphor for a control plane in one sentence?",
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: job_created" not in body

    jobs = jobmint_app.state.store.list_jobs_for_session("sess_jobmint_chitchat_stream")
    assert jobs == []


def test_req_jobmint_001_chat_source_fail_closed_no_silent_react_bypass():
    """Outcome-shaped standing path must not silently fall through to plain ReAct.

    If orch is missing, Chat must error (anti-theatre) rather than ReAct-fulfill
    a Wiki write with jobs=[].
    """
    src = inspect.getsource(chat_mod.chat_stream)
    assert "route_standing_chat" in src
    assert "create_job_from_catalog_resolve" in src
    # Fail-closed marker for outcome mint when orch unavailable.
    assert (
        "JOBMINT" in src
        or "outcome_mint" in src
        or "cannot mint standing Job" in src
        or "fail-closed" in src.lower()
        or "fail_closed_outcome" in src
    )
