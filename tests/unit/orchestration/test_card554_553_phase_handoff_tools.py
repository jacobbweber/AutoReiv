"""CARD-554 + CARD-553 (one plan): a job phase that hands off, or runs as its assigned agent, works with that agent's
own tools, and the planning phase only plans.

CARD-553 REQ-553-001: a job's matched capability subset narrows only the agent the job was minted for. Another agent
(a Developer Execute phase, or a handoff target) gets resolve_allowed_tools(agent) narrowed only by per-turn selection.
The tool policy gate stays the single enforcement point (ADR-0061).
CARD-554 REQ-554-001: in a Formulate (planning) phase the gate blocks handoff_to_agent and work tools (writes, exec),
and they are not mounted. REQ-554-002: a handoff from inside a running phase does not park that phase, so the phase
still completes. REQ-554-003: the Formulate assignment says it plans only, names the agent that runs Execute, and
does not carry the "MUST call repo_file_read" constraint (that belongs to Execute).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.kernel.agent_kernel import AgentKernel
from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.domain.gateway.models import ToolCall, ToolDefinition
from src.domain.kernel.models import AgentProfile, AgentTone, KernelEvent, KernelEventType
from src.domain.orchestration.models import HandoffEnvelope, HandoffPacket, Job, JobStatus, Phase, PhaseStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

AUTOREIV_SUBSET = ["tool.list_available_skills_and_tools", "tool.propose_agent_specification"]


def _tool(name: str) -> ToolDefinition:
    return ToolDefinition(name=name, description=name.replace("_", " "), parameters={"type": "object", "properties": {}})


@pytest.fixture
def store(tmp_path):
    s = SQLiteStateStore(db_path=str(tmp_path / "t.db"))
    s.initialize_db()
    return s


@pytest.fixture
def job(store):
    j = Job(id="job_553", session_id="sess_553", agent_id="autoreiv", goal="Count defs in allowed_tools.py", status=JobStatus.RUNNING)
    formulate = Phase(id="ph_formulate", job_id=j.id, name="Formulate", index=0, assigned_agent_id="autoreiv", status=PhaseStatus.DONE)
    execute = Phase(id="ph_execute", job_id=j.id, name="Execute", index=1, assigned_agent_id="developer", status=PhaseStatus.RUNNING)
    store.create_job(j, [formulate, execute])
    store.save_job_phase_checkpoint(
        job_id=j.id, phase_id=formulate.id, phase_index=0, verifier_status="skipped_no_checker",
        matched_capability_ids=AUTOREIV_SUBSET,
    )
    return j


def _developer(bind_skills):
    ticks = bind_skills({"coding": ["repo_file_read", "repo_file_list"], "sandbox": ["execute_code"], "shell": ["cli_exec"]})
    return AgentProfile(id="developer", name="Developer", description="d", system_prompt="s", tone=AgentTone.TECHNICAL, allowed_skill=ticks)


def _autoreiv(bind_skills):
    ticks = bind_skills({"authoring": ["list_available_skills_and_tools"], "projects": ["write_project_file", "read_project_file"]})
    return AgentProfile(id="autoreiv", name="AutoReiv", description="a", system_prompt="s", tone=AgentTone.TECHNICAL, allowed_skill=ticks)


def _kernel(store, tools):
    registry = MagicMock()
    registry.get_tools_for_agent.return_value = tools
    registry.list_tools.return_value = tools
    return AgentKernel(gateway=MagicMock(), tool_registry=registry, state_store=store, telemetry=MagicMock())


# --- CARD-553 ---------------------------------------------------------------------------------------------------


def test_job_subset_narrows_only_the_agent_the_job_was_minted_for(store, job, bind_skills):
    kernel = _kernel(store, [])
    assert kernel._matched_capability_ids_for_job(job.id, agent=_autoreiv(bind_skills)) == AUTOREIV_SUBSET
    assert kernel._matched_capability_ids_for_job(job.id, phase_id="ph_execute", agent=_developer(bind_skills)) is None
    assert kernel._matched_capability_ids_for_job(job.id, agent=_developer(bind_skills)) is None  # handoff child


def test_developer_execute_phase_mounts_its_own_tools(store, job, bind_skills):
    dev = _developer(bind_skills)
    tools = [_tool(n) for n in ("activate_skill", "handoff_to_agent", "repo_file_read", "repo_file_list", "execute_code", "cli_exec")]
    kernel = _kernel(store, tools)
    ids = kernel._matched_capability_ids_for_job(job.id, phase_id="ph_execute", agent=dev)
    names = [t.name for t in kernel._resolve_active_tools(dev, "read allowed_tools.py and run code", matched_capability_ids=ids)]
    assert {"repo_file_read", "execute_code", "cli_exec"} <= set(names)


def test_gate_lets_developer_run_code_inside_an_autoreiv_job(store, job, bind_skills):
    dev = _developer(bind_skills)
    kernel = _kernel(store, [])
    gate = ToolPolicyGate(store)
    for name in ("execute_code", "cli_exec", "repo_file_read"):
        decision = gate.evaluate(
            ToolCall(id="t", name=name, arguments={"command": "python -V"} if name == "cli_exec" else {}),
            dev,
            matched_capability_ids=kernel._matched_capability_ids_for_job(job.id, agent=dev),
        )
        assert decision.verdict != ToolPolicyVerdict.BLOCK, (name, decision.reason)
    # Developer's own allowed set is still the limit (single enforcement point): an unticked tool stays blocked.
    blocked = gate.evaluate(ToolCall(id="t", name="write_project_file", arguments={}), dev,
                            matched_capability_ids=kernel._matched_capability_ids_for_job(job.id, agent=dev))
    assert blocked.verdict == ToolPolicyVerdict.BLOCK and blocked.policy_source == "agent_allowlist"


# --- CARD-554 ---------------------------------------------------------------------------------------------------


def test_is_planning_phase_matches_formulate_only():
    from src.application.orchestration.phase_roles import is_planning_phase

    assert is_planning_phase(Phase(id="a", job_id="j", name="Formulate", index=0, assigned_agent_id="autoreiv"))
    assert not is_planning_phase(Phase(id="b", job_id="j", name="Execute", index=1, assigned_agent_id="developer"))
    assert not is_planning_phase(None)


def test_gate_blocks_handoff_and_work_tools_in_a_planning_phase(store, bind_skills):
    ar = _autoreiv(bind_skills)
    gate = ToolPolicyGate(store)

    def verdict(name, planning):
        return gate.evaluate(ToolCall(id="t", name=name, arguments={}), ar, planning_phase=planning)

    for name in ("handoff_to_agent", "write_project_file"):
        d = verdict(name, True)
        assert d.verdict == ToolPolicyVerdict.BLOCK and d.policy_source == "planning_phase", name
        assert "plan" in d.reason.lower()
    for name in ("lookup_agents", "read_project_file", "list_available_skills_and_tools"):
        assert verdict(name, True).verdict != ToolPolicyVerdict.BLOCK, name
    assert verdict("handoff_to_agent", False).verdict != ToolPolicyVerdict.BLOCK


def test_kernel_knows_the_planning_phase_and_does_not_mount_work_tools(store, job, bind_skills):
    ar = _autoreiv(bind_skills)
    tools = [_tool(n) for n in ("activate_skill", "handoff_to_agent", "lookup_agents", "write_project_file", "read_project_file")]
    kernel = _kernel(store, tools)
    assert kernel._is_planning_phase("ph_formulate") is True
    assert kernel._is_planning_phase("ph_execute") is False
    assert kernel._is_planning_phase(None) is False
    names = {t.name for t in kernel._resolve_active_tools(ar, "plan it", matched_capability_ids=None, planning_phase=True)}
    assert "handoff_to_agent" not in names and "write_project_file" not in names
    assert {"lookup_agents", "read_project_file"} <= names


def test_planning_block_names_the_execute_agent():
    from src.application.orchestration.phase_roles import format_planning_phase_block

    phases = [
        Phase(id="f", job_id="j", name="Formulate", index=0, assigned_agent_id="autoreiv"),
        Phase(id="e", job_id="j", name="Execute", index=1, assigned_agent_id="developer"),
    ]
    text = format_planning_phase_block(phases, phases[0])
    assert "Execute" in text and "developer" in text.lower()
    assert "hand off" in text.lower() and "plan only" in text.lower()


class _StreamKernel:
    async def stream_turn(self, **kwargs):
        yield KernelEvent(event_type=KernelEventType.TURN_END, content="done", is_finished=True)


@pytest.mark.asyncio
async def test_handoff_inside_a_running_phase_does_not_park_it(store):
    from src.application.capabilities.resolver import CapabilityCatalogResolver
    from src.application.orchestration.handoff_engine import HandoffIsolationEngine
    from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
    from src.domain.capabilities.models import CapabilityIndexEntry, CapabilityKind
    from src.infrastructure.agents.registry import BuiltinAgentRegistry
    from src.infrastructure.memory.repositories.capability_catalog import CapabilityCatalogRepository

    resolver = CapabilityCatalogResolver(CapabilityCatalogRepository(store))
    resolver.upsert(CapabilityIndexEntry.self_authored(
        id="tool.wiki_note_search", kind=CapabilityKind.TOOL, name="wiki_note_search", summary="Search wiki notes",
        keywords=["wiki", "search", "notes"], roles=["autoreiv"],
    ))
    orch = JobPhaseOrchestrator(store, capability_resolver=resolver)
    parent = orch.create_job_from_catalog_resolve(
        intent="Search the wiki notes then summarize", session_id="sess-554", agent_id="autoreiv", role="autoreiv",
        matched_capability_ids=["tool.wiki_note_search"],
    )
    phase = store.list_phases_for_job(parent.id)[0]
    orch.start_phase(phase.id)

    dev = AgentProfile(id="developer", name="Developer", description="d", system_prompt="s", tone=AgentTone.TECHNICAL, max_turns=5)
    engine = HandoffIsolationEngine(
        agent_registry=BuiltinAgentRegistry(profiles=[dev], state_store=store), state_store=store,
        kernel=_StreamKernel(), job_orchestrator=orch,
    )
    result = await engine.execute_handoff(HandoffEnvelope(
        sender_agent_id="autoreiv", recipient_agent_id="developer", session_id="sess-554::phase::x",
        task_intent="read a file", context_payload={"parent_job_id": parent.id},
        packet=HandoffPacket(goal="read a file", facts=[], constraints=[], done_when="read", budget={"max_turns": 3}),
    ))
    assert result.status == "completed"
    assert store.get_phase(phase.id).status == PhaseStatus.RUNNING
    orch.complete_phase(phase.id, HandoffPacket(goal="g", facts=["planned"], constraints=[], done_when="d", budget={}))
    assert store.get_phase(phase.id).status == PhaseStatus.DONE


@pytest.mark.asyncio
async def test_formulate_assignment_plans_only_and_leaves_repo_reads_to_execute(store, tmp_path):
    from src.application.orchestration.repo_code_grounding import ACTION_REQUIRE_READ, RepoGroundingDecision
    from src.web.routers.chat import execute_goal_job_phases

    sid = "sess_554"
    store.create_session(agent_id="autoreiv", title="Code ask", session_id=sid)
    j = Job(id="job_554", agent_id="autoreiv", goal="Read src/application/agent_packs/allowed_tools.py and count defs", session_id=sid)
    formulate = Phase(id="ph_f554", job_id=j.id, name="Formulate", index=0, assigned_agent_id="autoreiv")
    execute = Phase(id="ph_e554", job_id=j.id, name="Execute", index=1, assigned_agent_id="developer")
    store.create_job(j, [formulate, execute])
    orch = MagicMock()
    orch.start_phase.side_effect = lambda pid: store.get_phase(pid)
    decision = RepoGroundingDecision(action=ACTION_REQUIRE_READ, reason="need_read", topic_query="allowed_tools",
                                     suggested_paths=("src/application/agent_packs/allowed_tools.py",))
    autoreiv, developer = MagicMock(id="autoreiv"), MagicMock(id="developer")
    registry = MagicMock()
    registry.get_profile.side_effect = lambda a: {"autoreiv": autoreiv, "developer": developer}.get(a)
    with patch("src.web.routers.chat._stream_turn_bound", new_callable=AsyncMock) as bound, \
            patch("src.web.routers.chat.apply_standing_repo_code_grounding", return_value=decision), \
            patch("src.web.routers.chat.is_repo_code_ask", return_value=True):
        bound.return_value = "parked"
        await execute_goal_job_phases(
            queue=asyncio.Queue(), kernel=MagicMock(), orch=orch, store=store, reflexion_engine=MagicMock(),
            profile=autoreiv, job=j, session_id=sid, self_verify=False, approval_mode="ask",
            data_dir=str(tmp_path / "data"), registry=registry,
        )
    assignment = bound.await_args.kwargs["user_content"]
    assert "plan only" in assignment.lower() and "developer" in assignment.lower()
    assert "You MUST call catalog tool `repo_file_read`" not in assignment
