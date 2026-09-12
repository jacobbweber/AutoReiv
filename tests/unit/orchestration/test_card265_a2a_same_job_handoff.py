"""CARD-265: Specialist A2A handoff resumes same job_id (no privilege widen)."""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.standing_a2a_handoff import (
    bind_specialist_same_job,
    child_ids_do_not_widen,
    effective_matched_ids_no_escalate,
    matched_ids_for_parent,
)
from src.application.orchestration.supervisor_specialist_pick import (
    supervisor_specialist_handoff,
)
from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    TrustTier,
)
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile, AgentTone, KernelEvent, KernelEventType
from src.domain.orchestration.models import HandoffEnvelope, HandoffPacket
from src.infrastructure.agents.registry import BuiltinAgentRegistry
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
            roles=["assistant", "autoreiv", "homelab"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.wiki_note_create",
            kind=CapabilityKind.TOOL,
            name="wiki_note_create",
            summary="Create wiki notes",
            keywords=["wiki", "create", "write", "note"],
            roles=["assistant", "autoreiv", "homelab"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.assistant",
            kind=CapabilityKind.AGENT,
            name="Assistant",
            summary="Day-to-day coordinator handoff",
            keywords=["assistant", "handoff", "coordinate", "specialist"],
            roles=["assistant", "autoreiv", "homelab"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )
    resolver.upsert(
        CapabilityIndexEntry(
            id="agent.homelab",
            kind=CapabilityKind.AGENT,
            name="Homelab",
            summary="Homelab specialist",
            keywords=["homelab", "fleet", "specialist", "sysadmin"],
            roles=["homelab", "assistant"],
            trust_tier=TrustTier.TRUSTED,
            source="builtin",
        )
    )


def _parent_job(orch: JobPhaseOrchestrator, resolver: CapabilityCatalogResolver):
    _seed(resolver)
    return orch.create_job_from_catalog_resolve(
        intent="Homelab fleet health with wiki search then specialist summary",
        session_id="sess-265-parent",
        agent_id="assistant",
        role="assistant",
        matched_capability_ids=[
            "tool.wiki_note_search",
            "agent.assistant",
            "agent.homelab",
        ],
    )


class _StreamKernel:
    def __init__(self):
        self.kwargs = None

    async def stream_turn(self, **kwargs):
        self.kwargs = kwargs
        yield KernelEvent(event_type=KernelEventType.TOKEN, content="same-job-ok")
        yield KernelEvent(
            event_type=KernelEventType.TURN_END, content="same-job-ok", is_finished=True
        )


def test_effective_matched_ids_no_escalate_skips_specialist_union():
    parent = ["tool.wiki_note_search", "agent.homelab"]
    specialist_wider = ["wiki_note_search", "cli_exec", "repo_file_write"]
    eff = effective_matched_ids_no_escalate(parent, specialist_tool_names=specialist_wider)
    assert eff == ["tool.wiki_note_search", "agent.homelab"]
    assert "cli_exec" not in "".join(eff)
    assert child_ids_do_not_widen(parent, eff)


def test_bind_specialist_same_job_resumes_same_id(store, orch, resolver):
    parent = _parent_job(orch, resolver)
    parent_ids = matched_ids_for_parent(orch, parent.id)
    assert parent_ids

    bound = bind_specialist_same_job(
        orch,
        job_id=parent.id,
        specialist_agent_id="homelab",
        specialty="homelab fleet",
        park=True,
    )
    assert bound["ok"] is True
    assert bound["job_id"] == parent.id
    assert bound["same_job_id"] == parent.id
    assert bound["parent_job_id"] == parent.id
    assert bound.get("child_job_id") in (None, parent.id)
    assert bound["matched_capability_ids"] == parent_ids
    assert child_ids_do_not_widen(parent_ids, bound["matched_capability_ids"])
    assert bound["privilege_escalated"] is False

    events = store.list_standing_journey_events(parent.id)
    kinds = [e.get("kind") if isinstance(e, dict) else getattr(e, "kind", None) for e in events]
    assert any(
        k in {"a2a_same_job_handoff", "standing.a2a_same_job_handoff"} for k in kinds
    )

    gate = ToolPolicyGate(store)
    agent = AgentProfile(
        id="homelab",
        name="Homelab",
        description="t",
        system_prompt="t",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=["cli_exec", "wiki_note_search"],
    )
    decision = gate.evaluate(
        ToolCall(id="t1", name="cli_exec", arguments={"command": "echo x"}),
        agent,
        matched_capability_ids=bound["matched_capability_ids"],
        registry_tool_names={"cli_exec", "wiki_note_search"},
    )
    assert decision.verdict == ToolPolicyVerdict.BLOCK
    assert decision.policy_source == "capability_subset"


def test_supervisor_pick_defaults_to_same_job(store, orch, resolver):
    parent = _parent_job(orch, resolver)
    phases = store.list_phases_for_job(parent.id)
    assert phases
    phase = phases[0]
    orch.start_phase(phase.id)

    result = supervisor_specialist_handoff(
        orch,
        phase_id=phase.id,
        specialty="homelab specialist",
        on_no_match="fail_closed",
    )
    assert result["ok"] is True
    assert result["parent_job_id"] == parent.id
    assert result["same_job_id"] == parent.id
    assert result.get("child_job_id") in (None, parent.id)
    assert result["action"] == "handoff"
    assert result["privilege_escalated"] is False
    assert child_ids_do_not_widen(
        result["matched_capability_ids"],
        result.get("effective_matched_capability_ids") or result["matched_capability_ids"],
    )


@pytest.mark.asyncio
async def test_engine_same_job_bind_stamps_result(store, orch, resolver):
    parent = _parent_job(orch, resolver)
    parent_ids = matched_ids_for_parent(orch, parent.id)

    specialist = AgentProfile(
        id="homelab",
        name="Homelab",
        description="d",
        system_prompt="s",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=["wiki_note_search", "cli_exec"],  # wider — must not escalate
        max_turns=5,
    )
    registry = BuiltinAgentRegistry(profiles=[specialist], state_store=store)
    kernel = _StreamKernel()
    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=kernel,
        job_orchestrator=orch,
    )
    envelope = HandoffEnvelope(
        sender_agent_id="assistant",
        recipient_agent_id="homelab",
        session_id="sess-265-engine",
        task_intent="Summarize fleet health in one sentence",
        context_payload={"parent_job_id": parent.id},  # default = same job
        packet=HandoffPacket(
            goal="one sentence summary",
            facts=["parent matched wiki search only"],
            constraints=["no cli_exec", "same job_id"],
            done_when="one sentence returned",
            budget={"max_turns": 3},
        ),
    )
    result = await engine.execute_handoff(envelope)
    assert result.status == "completed"
    assert result.parent_job_id == parent.id
    assert result.same_job_id == parent.id
    assert result.child_job_id in (None, parent.id)
    assert kernel.kwargs is not None
    assert kernel.kwargs.get("job_id") == parent.id
    assert matched_ids_for_parent(orch, parent.id) == parent_ids


@pytest.mark.asyncio
async def test_engine_linked_child_opt_in_still_works(store, orch, resolver):
    parent = _parent_job(orch, resolver)
    specialist = AgentProfile(
        id="homelab",
        name="Homelab",
        description="d",
        system_prompt="s",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=["wiki_note_search"],
        max_turns=5,
    )
    kernel = _StreamKernel()
    engine = HandoffIsolationEngine(
        kernel=kernel,
        agent_registry=BuiltinAgentRegistry(profiles=[specialist], state_store=store),
        state_store=store,
        job_orchestrator=orch,
    )
    envelope = HandoffEnvelope(
        sender_agent_id="assistant",
        recipient_agent_id="homelab",
        session_id="sess-265-linked",
        task_intent="child path",
        context_payload={"parent_job_id": parent.id, "linked_child_job": True},
        packet=HandoffPacket(
            goal="child",
            facts=[],
            constraints=[],
            done_when="done",
            budget={"max_turns": 3},
        ),
    )
    result = await engine.execute_handoff(envelope)
    assert result.parent_job_id == parent.id
    assert result.child_job_id
    assert result.child_job_id != parent.id
    assert not result.same_job_id
    assert kernel.kwargs.get("job_id") == result.child_job_id
