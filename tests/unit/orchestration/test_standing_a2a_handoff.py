"""CARD-224: A2A handoff inherits standing Job/Phase path (thin slice)."""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.orchestration.handoff_engine import HandoffIsolationEngine
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
from src.domain.kernel.models import AgentProfile, AgentTone, KernelEvent, KernelEventType
from src.domain.orchestration.models import HandoffEnvelope, HandoffPacket, PhaseStatus
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
            roles=["assistant", "autoreiv"],
        )
    )
    resolver.upsert(
        CapabilityIndexEntry.self_authored(
            id="tool.wiki_note_create",
            kind=CapabilityKind.TOOL,
            name="wiki_note_create",
            summary="Create wiki notes",
            keywords=["wiki", "create", "write", "note"],
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
    # Linked child has its own bootstrap checkpoint [CARD-224 Done bar].
    cp = orch.get_latest_checkpoint(child.id)
    assert cp is not None
    assert list(cp.matched_capability_ids or []) == child_ids
    assert cp.job_id == child.id


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

    from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
    from src.domain.gateway.models import ToolCall

    gate = ToolPolicyGate(store)
    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="t",
        system_prompt="t",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=["wiki_note_search", "wiki_note_create", "cli_exec"],
    )
    d_parent = gate.evaluate(
        ToolCall(id="1", name="cli_exec", arguments={"command": "echo hi"}),
        agent,
        matched_capability_ids=parent_ids,
        registry_tool_names={"wiki_note_search", "wiki_note_create", "cli_exec"},
    )
    d_child = gate.evaluate(
        ToolCall(id="2", name="cli_exec", arguments={"command": "echo hi"}),
        agent,
        matched_capability_ids=child_ids,
        registry_tool_names={"wiki_note_search", "wiki_note_create", "cli_exec"},
    )
    assert d_parent.verdict == ToolPolicyVerdict.BLOCK
    assert d_child.verdict == ToolPolicyVerdict.BLOCK
    assert d_parent.policy_source == "capability_subset"
    assert d_child.policy_source == "capability_subset"


def test_dangerous_tool_on_child_still_require_confirm(store, orch, resolver):
    """Dangerous tool in inherited subset still REQUIRE_CONFIRM on child [CARD-224]."""
    _seed(resolver)
    parent = orch.create_job_from_catalog_resolve(
        intent="First research wiki notes, then create a wiki note summary, finally handoff.",
        session_id="sess-req",
        agent_id="assistant",
        role="assistant",
        matched_capability_ids=[
            "tool.wiki_note_search",
            "tool.wiki_note_create",
            "agent.assistant",
        ],
        verify_checker=None,
    )
    child = create_standing_child_job(
        orch,
        parent_job_id=parent.id,
        intent="Child create wiki note",
        session_id="sess-req_child",
        agent_id="assistant",
    )
    child_ids = matched_ids_for_parent(orch, child.id)
    assert "tool.wiki_note_create" in child_ids
    from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
    from src.domain.gateway.models import ToolCall

    gate = ToolPolicyGate(store)
    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="t",
        system_prompt="t",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=["wiki_note_search", "wiki_note_create"],
    )
    d = gate.evaluate(
        ToolCall(id="3", name="wiki_note_create", arguments={"title": "x"}),
        agent,
        matched_capability_ids=child_ids,
        registry_tool_names={"wiki_note_search", "wiki_note_create"},
    )
    assert d.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM


def test_kill_child_resume_same_child_job_id(store, orch, resolver, temp_db_path):
    """Kill mid-phase on child -> resume_after_crash same child_job_id [CARD-224]."""
    _seed(resolver)
    parent = orch.create_job_from_catalog_resolve(
        intent="First research wiki, then handoff to assistant, finally verify.",
        session_id="sess-kill",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    child = create_standing_child_job(
        orch,
        parent_job_id=parent.id,
        intent="Child research",
        session_id="sess-kill_child",
        agent_id="assistant",
    )
    phases = store.list_phases_for_job(child.id)
    orch.start_phase(phases[0].id)
    assert store.get_phase(phases[0].id).status == PhaseStatus.RUNNING
    child_id = child.id
    matched_before = matched_ids_for_parent(orch, child_id)

    store2 = SQLiteStateStore(db_path=temp_db_path)
    orch2 = JobPhaseOrchestrator(store2, capability_resolver=resolver)
    resume = orch2.resume_after_crash(child_id)
    assert resume.ok is True
    assert resume.job.id == child_id
    assert resume.resumed_from_checkpoint is True
    assert matched_ids_for_parent(orch2, child_id) == matched_before
    assert child_ids_do_not_widen(matched_ids_for_parent(orch2, parent.id), matched_before)


class _StreamKernel:
    def __init__(self):
        self.kwargs = None

    async def stream_turn(self, agent, session_id, user_content=None, approval_mode="ask", resume=False, **kwargs):
        self.kwargs = {
            "agent": agent,
            "session_id": session_id,
            "user_content": user_content,
            "approval_mode": approval_mode,
            "resume": resume,
            **kwargs,
        }
        yield KernelEvent(event_type=KernelEventType.TOKEN, content="child ok")
        yield KernelEvent(event_type=KernelEventType.TURN_END, content="child ok", is_finished=True)


@pytest.mark.asyncio
async def test_engine_stamps_parent_child_job_ids_and_binds_child(store, orch, resolver, temp_db_path):
    """HandoffIsolationEngine creates linked child and passes job_id to stream_turn."""
    _seed(resolver)
    parent = orch.create_job_from_catalog_resolve(
        intent="First research wiki, then handoff to assistant, finally verify.",
        session_id="sess-eng",
        agent_id="assistant",
        role="assistant",
        verify_checker=None,
    )
    specialist = AgentProfile(
        id="specialist-agent",
        name="Specialist",
        description="d",
        system_prompt="s",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=["wiki_note_search"],
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
        recipient_agent_id="specialist-agent",
        session_id="sess-eng",
        task_intent="Deepen wiki research",
        context_payload={"parent_job_id": parent.id},
        packet=HandoffPacket(
            goal="Deepen wiki research",
            facts=["parent standing"],
            constraints=["no widen"],
            done_when="summary ready",
            budget={"max_turns": 3},
        ),
    )
    result = await engine.execute_handoff(envelope)
    assert result.status == "completed"
    assert result.parent_job_id == parent.id
    assert result.child_job_id
    assert result.child_job_id != parent.id
    assert linked_child_job_ids(orch, parent.id) == [result.child_job_id]
    assert kernel.kwargs is not None
    assert kernel.kwargs.get("job_id") == result.child_job_id
    cp = orch.get_latest_checkpoint(result.child_job_id)
    assert cp is not None
    assert list(cp.matched_capability_ids or []) == matched_ids_for_parent(orch, parent.id)
