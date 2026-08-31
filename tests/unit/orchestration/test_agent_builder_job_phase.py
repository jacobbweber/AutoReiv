"""
Agent Builder uses Job/Phase + CARD-099 no-tool planner [REQ-BUILD-009] [REQ-BUILD-011].
"""

from src.application.kernel.plan_engine import (
    AGENT_BUILDER_ID,
    PlanAndExecuteEngine,
    agent_builder_research_fallback,
)
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.domain.agents.profiles import AGENT_BUILDER_PROFILE, get_builtin_profile
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def test_agent_builder_is_in_registry():
    store = SQLiteStateStore(db_path=":memory:")
    registry = BuiltinAgentRegistry(state_store=store)
    profile = registry.get_agent("agent-builder")
    assert profile is not None
    assert profile.id == AGENT_BUILDER_ID
    assert profile.name == "Agent Builder"
    ids = [p.id for p in registry.list_agents()]
    assert "agent-builder" in ids
    assert get_builtin_profile("agent-builder").id == "agent-builder"


def test_default_chat_is_one_job_one_phase(tmp_path):
    store = SQLiteStateStore(db_path=tmp_path / "jobs.db")
    orch = JobPhaseOrchestrator(store)
    job = orch.create_single_phase_job(
        goal="I need a homelab backup skill",
        session_id="sess_ab",
        agent_id="agent-builder",
    )
    phases = store.list_phases_for_job(job.id)
    assert len(phases) == 1
    assert phases[0].name == "Chat"
    assert job.agent_id == "agent-builder"
    assert phases[0].assigned_agent_id == "agent-builder"


def test_research_fallback_does_not_write_skill_md():
    steps = agent_builder_research_fallback()
    assert len(steps) >= 2
    titles = " ".join(s.title.lower() for s in steps)
    assert "survey" in titles
    assert "propose" in titles or "hitl" in titles
    blob = " ".join((s.title + " " + s.description).lower() for s in steps)
    assert "do not write skill.md" in blob
    assert "langgraph" not in blob


def test_planner_parse_fallback_is_research_phases():
    engine = PlanAndExecuteEngine(kernel=None)
    fallback = agent_builder_research_fallback()
    steps = engine._parse_steps_from_response("not-json", fallback=fallback)
    assert [s.title for s in steps] == [s.title for s in fallback]
    generic = engine._parse_steps_from_response("not-json")
    assert generic[0].title == "Analyze Requirements"


def test_planner_prompt_mentions_research_not_write():
    from src.application.kernel import plan_engine as pe

    assert "SKILL.md" in pe._AGENT_BUILDER_PLANNER_USER
    assert "Do not emit a graph" in pe._PLANNER_SYSTEM
    assert AGENT_BUILDER_PROFILE.id == AGENT_BUILDER_ID
