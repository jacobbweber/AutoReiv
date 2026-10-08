"""CARD-665: the Formulate (planning) step calls only tools it was given, and says so honestly otherwise.

Found on 2026-10-05: in a wiki job's Formulate step the model called wiki_template_list, system_info and a skill id
(platform-health), 2 per job run. Each one was refused and wasted a round. The step's text named them: its success
rule said "Formulate plan using matched capabilities: tool.wiki_template_list, ...", and the matched list and skill
index name skills and tools that are not in the tools sent on that call.

- The planner is told exactly which tools it can call. That list is the set the kernel sends on the call: the
  agent's granted tools (ticked skills plus platform tools), narrowed by the job's match and plan-only rules.
- Matched skills and tools it cannot call are named as such ("a skill, not a tool", "not granted to you").
- The Formulate success rule no longer tells the planner to use every matched id.
- A call to anything else is refused before policy, approval or execution. A skill id is refused as a skill, not
  as a missing tool, so the reply gets no Ask Developer offer to build it.
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.reply_rules import ASK_DEVELOPER_LINE, ask_developer_ending
from src.application.kernel.tool_registry import NO_SUCH_TOOL, ScopedToolRegistry
from src.application.safety.tool_policy_gate import ToolPolicyGate
from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.orchestration.models import Job, JobStatus, Phase, PhaseStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

REPO = Path(__file__).resolve().parents[3]
MATCHED = ["tool.wiki_note_search", "tool.wiki_template_list", "tool.system_info", "tool.wiki_note_create",
           "skill.education-wiki-curation"]
REGISTERED = set(REQUIRED_PLATFORM_TOOLS) | {
    "wiki_note_search", "wiki_note_read", "wiki_note_create", "wiki_template_list", "system_info", "skill_view",
}


@pytest.fixture
def store(tmp_path):
    s = SQLiteStateStore(db_path=str(tmp_path / "t.db"))
    s.initialize_db()
    return s


@pytest.fixture
def job(store):
    j = Job(id="job_665", session_id="sess_665", agent_id="autoreiv", goal="Summarize my gardening notes",
            status=JobStatus.RUNNING)
    formulate = Phase(id="ph_f", job_id=j.id, name="Formulate", index=0, assigned_agent_id="autoreiv",
                      status=PhaseStatus.RUNNING)
    execute = Phase(id="ph_e", job_id=j.id, name="Execute", index=1, assigned_agent_id="autoreiv",
                    status=PhaseStatus.QUEUED)
    store.create_job(j, [formulate, execute])
    store.save_job_phase_checkpoint(job_id=j.id, phase_id=formulate.id, phase_index=0,
                                    verifier_status="none", matched_capability_ids=MATCHED)
    return j


@pytest.fixture
def agent(bind_skills):
    ticks = bind_skills({
        "wiki-knowledge": ["wiki_note_search", "wiki_note_read", "wiki_note_create"],
        "platform-health": ["system_info"],
    })
    return AgentProfile(id="autoreiv", name="AutoReiv", description="a", system_prompt="s",
                        tone=AgentTone.TECHNICAL, allowed_skill=ticks)


class _Counting(ScopedToolRegistry):
    def __init__(self):
        super().__init__()
        self.ran: list[str] = []
        for name in sorted(REGISTERED):
            self.register_tool(name, f"{name} tool", {"type": "object", "properties": {}},
                               (lambda n: (lambda **kw: self.ran.append(n) or "ok"))(name))


def _kernel(store, registry=None):
    hitl = MagicMock()
    kernel = AgentKernel(gateway=MagicMock(), tool_registry=registry or _Counting(), state_store=store,
                         telemetry=MagicMock(), tool_policy_gate=ToolPolicyGate(store), hitl_engine=hitl)
    return kernel, hitl


def test_offered_tool_names_are_what_the_planning_call_sends_and_only_granted_tools(store, job, agent):
    kernel, _ = _kernel(store)
    offered = kernel.offered_tool_names(agent, job_id=job.id, phase_id="ph_f")
    sent = [t.name for t in kernel._resolve_active_tools(agent, matched_capability_ids=MATCHED, planning_phase=True)]
    assert sorted(offered) == sorted(sent)
    granted = resolve_allowed_tools(agent)
    assert all(name in granted for name in offered)
    assert "wiki_note_search" in offered and "system_info" in offered
    assert "wiki_template_list" not in offered  # matched, but no ticked skill grants it
    assert "wiki_note_create" not in offered  # granted, but a planning step does not change anything
    assert not any(name.startswith("skill.") or name in agent.allowed_skill for name in offered)


def test_offered_tool_names_outside_a_job_ignore_the_last_turns_match(store, agent):
    kernel, _ = _kernel(store)
    kernel._turn_matched_capability_ids = ["tool.wiki_note_search"]  # stale state from an earlier turn
    offered = kernel.offered_tool_names(agent)
    assert {"wiki_note_read", "wiki_note_create", "system_info"} <= set(offered)


def test_planning_tools_block_names_exactly_what_can_be_called():
    from src.application.orchestration.phase_roles import format_planning_tools_block

    offered = ["wiki_note_search", "system_info", "ask_clarification"]
    granted = offered + ["wiki_note_create", "wiki_note_read"]
    text = format_planning_tools_block(offered, MATCHED, granted=granted, skills=["wiki-knowledge", "platform-health"])
    callable_line = next(line for line in text.splitlines() if line.startswith("TOOLS YOU CAN CALL IN THIS PHASE"))
    assert callable_line.endswith("ask_clarification, system_info, wiki_note_search.")
    for name in ("wiki_template_list", "wiki_note_create", "education-wiki-curation", "platform-health"):
        assert name not in callable_line
    assert "education-wiki-curation (a skill, not a tool)" in text
    assert "wiki_template_list (not granted to you)" in text
    assert "wiki_note_create (granted to you, not used while planning)" in text
    assert "do not call" in text.lower()
    assert "say so in the plan" in text.lower()


def test_planning_tools_block_with_nothing_offered_says_answer_in_text():
    from src.application.orchestration.phase_roles import format_planning_tools_block

    assert "none: write the plan in text" in format_planning_tools_block([], []).lower()


def test_planning_tools_block_for_uses_the_kernels_offered_set(store, job, agent):
    from src.application.orchestration.phase_roles import planning_tools_block_for

    kernel, _ = _kernel(store)
    text = planning_tools_block_for(kernel, agent, job_id=job.id, phase_id="ph_f", matched_ids=MATCHED)
    offered = sorted(kernel.offered_tool_names(agent, job_id=job.id, phase_id="ph_f"))
    assert f"TOOLS YOU CAN CALL IN THIS PHASE: {', '.join(offered)}." in text


def test_chat_job_runner_adds_the_tools_block_to_the_formulate_assignment():
    tree = ast.parse((REPO / "src" / "web" / "routers" / "chat.py").read_text(encoding="utf-8"))
    called = {
        node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert "planning_tools_block_for" in called


@pytest.mark.parametrize("name", ["wiki_template_list", "system_info", "wiki_note_create"])
def test_a_planning_call_outside_the_offered_tools_is_refused_and_never_runs(store, job, agent, name):
    registry = _Counting()
    kernel, hitl = _kernel(store, registry)
    offered = set(kernel.offered_tool_names(agent, job_id=job.id, phase_id="ph_f")) - {"system_info"}
    res = kernel._gate_tool_call(ToolCall(id="c1", name=name, arguments={}), "sess_665", agent,
                                 job_id=job.id, planning_phase=True, offered=offered)
    assert res is not None and res.success is False
    assert res.error.startswith("tool_not_offered:")
    assert registry.ran == [] and not hitl.method_calls  # not run, not parked for approval


@pytest.mark.parametrize("name", ["platform-health", "skill.platform-health", "skill.education-wiki-curation"])
def test_a_skill_id_called_as_a_tool_is_refused_as_a_skill(store, job, agent, name):
    registry = _Counting()
    kernel, _ = _kernel(store, registry)
    offered = set(kernel.offered_tool_names(agent, job_id=job.id, phase_id="ph_f"))
    call = ToolCall(id="c1", name=name, arguments={})
    res = kernel._gate_tool_call(call, "sess_665", agent, planning_phase=True, offered=offered)
    skill = name.removeprefix("skill.")
    assert f"'{skill}' is a skill (runbook), not a tool" in res.error
    assert NO_SUCH_TOOL not in res.error
    assert "Tools you can call now:" in res.error
    assert asyncio.run(registry.execute(call, agent, offered=offered)).error == res.error
    assert registry.ran == []
    history = [
        ChatMessage(role=Role.USER, content="plan it"),
        ChatMessage(role=Role.TOOL, content=res.error, name=name, tool_call_id="c1"),
    ]
    reply = "Plan: 1. Search the notes. 2. Write the summary in the next phase."
    assert not ask_developer_ending(reply, history, None, set(offered)).endswith(ASK_DEVELOPER_LINE)


def test_an_unknown_name_is_still_a_missing_tool(store, agent):
    kernel, _ = _kernel(store)
    res = kernel._gate_tool_call(ToolCall(id="c1", name="send_fax", arguments={}), "s", agent,
                                 offered={"wiki_note_search"})
    assert NO_SUCH_TOOL in res.error and "is a skill" not in res.error


def test_formulate_success_rule_does_not_tell_the_planner_to_use_every_matched_id(store):
    from src.application.capabilities.resolver import CapabilityCatalogResolver
    from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
    from src.infrastructure.memory.repositories.capability_catalog import CapabilityCatalogRepository

    orch = JobPhaseOrchestrator(store, capability_resolver=CapabilityCatalogResolver(CapabilityCatalogRepository(store)))
    job = orch.create_job_from_catalog_resolve(
        intent="Summarize my gardening notes", session_id="s", agent_id="autoreiv", role="autoreiv",
        matched_capability_ids=MATCHED,
    )
    formulate = next(p for p in store.list_phases_for_job(job.id) if p.name == "Formulate")
    assert "Summarize my gardening notes" in formulate.success_rule
    for cid in MATCHED:
        assert cid not in formulate.success_rule
    assert orch.matched_capability_ids_for_job(job.id) == MATCHED  # the match itself is kept
