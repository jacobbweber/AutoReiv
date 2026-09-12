"""CARD-222: Routines join standing Job/Phase path (same as Chat)."""

from __future__ import annotations

import ast
import inspect
import os
import tempfile
from pathlib import Path
from typing import AsyncIterator

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.standing_job_graph import (
    StandingRoute,
    route_standing_chat,
)
from src.application.routines.executor import RoutineExecutor
from src.application.routines.scheduler import RoutineScheduler
from src.application.telemetry.collector import TelemetryCollector
from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    TrustTier,
)
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
)
from src.domain.orchestration.models import PhaseStatus
from src.domain.routines.models import Routine, RoutineStatus, ScheduleType
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.repositories.capability_catalog import (
    CapabilityCatalogRepository,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

MULTI_STEP_PROMPT = (
    "First research the wiki notes for fleet health, then handoff findings "
    "to the assistant, finally execute a platform health verify."
)

class MockScriptedLLM(LLMProviderPort):
    provider_id: str = "mock"

    def __init__(self, response_text: str = "Standing routine phase complete."):
        self.response_text = response_text

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(
            model=request.model,
            message=ChatMessage(role=Role.ASSISTANT, content=self.response_text),
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(content=self.response_text, is_finished=True, finish_reason="stop")

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
def collector(store):
    return TelemetryCollector(store=store)

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
            roles=["assistant", "autoreiv", "general-assistant"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.assistant",
            kind=CapabilityKind.AGENT,
            name="Assistant",
            summary="Day-to-day coordinator handoff",
            keywords=["assistant", "handoff", "coordinate"],
            roles=["assistant", "autoreiv", "general-assistant"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )

@pytest.fixture
def executor(store, collector, orch, tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    agent_reg, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=collector,
        wiki_root=str(tmp_path / "wiki"),
        skills_dir=str(skills_dir),
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(MockScriptedLLM())
    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=tool_reg,
        state_store=store,
        telemetry=collector,
    )
    return RoutineExecutor(
        agent_registry=agent_reg,
        kernel=kernel,
        state_store=store,
        telemetry=collector,
        job_orchestrator=orch,
    )

def test_req_routstand_001_scheduler_is_trigger_only():
    """Cron/scheduler must only call executor - no parallel thin ReAct loop [REQ-ROUTSTAND-001]."""
    src = inspect.getsource(RoutineScheduler)
    assert "execute_routine" in src
    assert "create_job_from_catalog_resolve" not in src
    assert "AgentKernel" not in src
    assert "run_turn" not in src

def test_req_routstand_002_executor_source_uses_catalog_resolve():
    """RoutineExecutor multi-step path must call create_job_from_catalog_resolve [REQ-ROUTSTAND-002]."""
    src = inspect.getsource(RoutineExecutor)
    assert "create_job_from_catalog_resolve" in src
    tree = ast.parse(src)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "create_job_from_catalog_resolve":
                found = True
    assert found is True

@pytest.mark.asyncio
async def test_req_routstand_002_multi_step_creates_rhe_job(store, executor, resolver, orch):
    """Multi-step routine fire -> catalog R/H/E + matched IDs + durable job_id [REQ-ROUTSTAND-002]."""
    _seed(resolver)
    assert route_standing_chat(MULTI_STEP_PROMPT) == StandingRoute.MULTI_STEP_JOB_GRAPH

    r = Routine(
        id="r-standing-multi",
        name="Standing Multi",
        agent_id="autoreiv",
        prompt=MULTI_STEP_PROMPT,
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
    )
    store.save_routine(r)

    run = await executor.execute_routine(r)

    assert run.status == RoutineStatus.SUCCESS
    job_id = getattr(run, "job_id", None) or (r.metadata or {}).get("last_standing_job_id")
    assert job_id, "routine fire must yield durable standing job_id"
    job = store.get_job(job_id)
    assert job is not None
    assert getattr(job, "template_id", None) == "catalog_resolve_rhe"
    phases = store.list_phases_for_job(job_id)
    names = [p.name for p in phases]
    # CARD-231: research-before-plan when catalog thin/gap; else Formulate/Execute
    assert names[-1] == "Execute"
    assert "Formulate" in names
    assert names == ["Research", "Formulate", "Execute"] or names == ["Formulate", "Execute"]
    matched = orch.matched_capability_ids_for_job(job_id)
    assert matched, "matched capability IDs must persist on checkpoint"
    updated = store.get_routine("r-standing-multi")
    assert (updated.metadata or {}).get("last_standing_job_id") == job_id

@pytest.mark.asyncio
async def test_req_routstand_004_kill_mid_phase_resume_same_job_id(store, executor, resolver, orch):
    """routine fire -> durable job_id -> kill mid-phase -> resume same job_id [REQ-ROUTSTAND-004]."""
    _seed(resolver)
    r = Routine(
        id="r-standing-resume",
        name="Standing Resume",
        agent_id="autoreiv",
        prompt=MULTI_STEP_PROMPT,
        schedule_type=ScheduleType.CRON,
        cron_expression="0 * * * *",
    )
    store.save_routine(r)

    run = await executor.execute_routine(r)
    job_id = getattr(run, "job_id", None) or (store.get_routine(r.id).metadata or {}).get(
        "last_standing_job_id"
    )
    assert job_id

    phases = store.list_phases_for_job(job_id)
    target = None
    for p in phases:
        if p.status == PhaseStatus.QUEUED:
            orch.start_phase(p.id)
            target = p
            break
    if target is None:
        cp = orch.get_latest_checkpoint(job_id)
        assert cp is not None
        assert cp.job_id == job_id

    resume = orch.resume_after_crash(job_id)
    assert store.get_job(job_id).id == job_id
    matched_before = orch.matched_capability_ids_for_job(job_id)
    orch2 = JobPhaseOrchestrator(store, capability_resolver=resolver)
    orch2.resume_after_crash(job_id)
    assert store.get_job(job_id).id == job_id
    matched_after = orch2.matched_capability_ids_for_job(job_id)
    assert matched_after == matched_before
    assert resume.needs_replan is False or resume.resumed_from_checkpoint or resume.ok

@pytest.mark.asyncio
async def test_req_routstand_005_short_prompt_stays_plain_react(store, executor):
    """Short routine prompts stay SHORT_REACT / plain kernel path [REQ-ROUTSTAND-005]."""
    short = "Check health now"
    assert route_standing_chat(short) == StandingRoute.SHORT_REACT
    r = Routine(
        id="r-standing-short",
        name="Short",
        agent_id="autoreiv",
        prompt=short,
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=60,
    )
    store.save_routine(r)
    run = await executor.execute_routine(r)
    assert run.status == RoutineStatus.SUCCESS
    job_id = getattr(run, "job_id", None)
    meta_job = (store.get_routine(r.id).metadata or {}).get("last_standing_job_id")
    assert not job_id and not meta_job

def test_req_routstand_002_app_wires_job_orchestrator_into_executor():
    """App must pass job_orchestrator into RoutineExecutor [anti-theatre]."""
    app_src = Path("src/web/app.py").read_text(encoding="utf-8")
    assert "RoutineExecutor(" in app_src
    assert "job_orchestrator" in app_src

@pytest.mark.asyncio
async def test_standing_phase_llm_timeout_fails_job_not_orphan(store, executor, resolver, orch, monkeypatch):
    """LLM hang must fail_phase with checkpoint — not leave orphan RUNNING [reliability]."""
    import asyncio

    from src.application.orchestration import standing_job_graph as sjg

    _seed(resolver)
    monkeypatch.setattr(sjg, "STANDING_PHASE_LLM_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(
        "src.application.routines.executor.STANDING_PHASE_LLM_TIMEOUT_SECONDS", 0.05
    )
    monkeypatch.setenv("STANDING_PHASE_LLM_TIMEOUT_SECONDS", "0.05")
    monkeypatch.setenv("STANDING_PHASE_LLM_RETRIES", "0")

    async def _hang(*_a, **_k):
        await asyncio.sleep(30)
        raise AssertionError("should have timed out")

    monkeypatch.setattr(executor.kernel, "run_turn", _hang)

    r = Routine(
        id="r-standing-timeout",
        name="Standing Timeout",
        agent_id="autoreiv",
        prompt=MULTI_STEP_PROMPT,
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
    )
    store.save_routine(r)
    run = await executor.execute_routine(r)

    job_id = getattr(run, "job_id", None) or (store.get_routine(r.id).metadata or {}).get(
        "last_standing_job_id"
    )
    assert job_id, "durable job_id must exist even on timeout"
    job = store.get_job(job_id)
    assert job.status == PhaseStatus.FAILED or job.status.value == "failed"
    phases = store.list_phases_for_job(job_id)
    assert any(p.status == PhaseStatus.FAILED for p in phases)
    assert not any(p.status == PhaseStatus.RUNNING for p in phases)
    cp = orch.get_latest_checkpoint(job_id)
    assert cp is not None
    assert cp.job_id == job_id
    assert run.status == RoutineStatus.FAILED


@pytest.mark.asyncio
async def test_standing_phase_llm_retries_then_succeeds(store, executor, resolver, monkeypatch):
    """First-attempt timeout retries, then success — not fail_phase [REQ-PLLM-001]."""
    import asyncio

    from src.application.orchestration import standing_job_graph as sjg

    _seed(resolver)
    monkeypatch.setattr(sjg, "STANDING_PHASE_LLM_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(
        "src.application.routines.executor.STANDING_PHASE_LLM_TIMEOUT_SECONDS", 0.05
    )
    monkeypatch.setenv("STANDING_PHASE_LLM_TIMEOUT_SECONDS", "0.05")
    monkeypatch.setenv("STANDING_PHASE_LLM_RETRIES", "2")

    calls = {"n": 0}

    async def _flaky(*_a, **_k):
        calls["n"] += 1
        if calls["n"] < 3:
            await asyncio.sleep(1.0)
        class _Msg:
            content = "recovered after retry"
        return _Msg()

    monkeypatch.setattr(executor.kernel, "run_turn", _flaky)

    r = Routine(
        id="r-standing-retry-ok",
        name="Standing Retry Ok",
        agent_id="autoreiv",
        prompt=MULTI_STEP_PROMPT,
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
    )
    store.save_routine(r)
    run = await executor.execute_routine(r)
    assert calls["n"] >= 3
    assert run.status == RoutineStatus.SUCCESS
    job_id = getattr(run, "job_id", None) or (store.get_routine(r.id).metadata or {}).get(
        "last_standing_job_id"
    )
    assert job_id
    phases = store.list_phases_for_job(job_id)
    assert not any(p.status == PhaseStatus.FAILED for p in phases)
    assert not any(p.status == PhaseStatus.RUNNING for p in phases)

