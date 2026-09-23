"""
CARD-429: agent-builder is not a live agent. Developer owns capability authoring.
The planner no longer switches prompts by agent id.
"""

from src.application.kernel.plan_engine import PlanAndExecuteEngine
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.domain.agents.profiles import get_builtin_profile
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_packs.catalog import platform_pack_profile


def test_agent_builder_is_not_in_registry():
    store = SQLiteStateStore(db_path=":memory:")
    registry = BuiltinAgentRegistry(state_store=store)
    assert registry.get_agent("agent-builder") is None
    assert get_builtin_profile("agent-builder") is None
    ids = [p.id for p in registry.list_agents()]
    assert "agent-builder" not in ids


def test_default_chat_is_one_job_one_phase(tmp_path):
    store = SQLiteStateStore(db_path=tmp_path / "jobs.db")
    orch = JobPhaseOrchestrator(store)
    job = orch.create_single_phase_job(
        goal="I need a homelab backup skill",
        session_id="sess_dev",
        agent_id="developer",
    )
    phases = store.list_phases_for_job(job.id)
    assert len(phases) == 1
    assert phases[0].name == "Chat"
    assert job.agent_id == "developer"
    assert phases[0].assigned_agent_id == "developer"


def test_planner_uses_one_prompt_for_every_agent():
    engine = PlanAndExecuteEngine(kernel=None)
    generic = engine._parse_steps_from_response("not-json")
    assert generic[0].title == "Analyze Requirements"
    from src.application.kernel import plan_engine as pe

    assert not hasattr(pe, "_AGENT_BUILDER_PLANNER_USER")
    assert not hasattr(pe, "agent_builder_research_fallback")
    assert "Do not emit a graph" in pe._PLANNER_SYSTEM


def test_developer_pack_holds_builder_tools():
    dev = platform_pack_profile("developer")
    assert "propose_skill" in dev.allowed_tool_names
    assert "commit_skill_pack" in dev.allowed_tool_names
    assert "scaffold_agent_pack" in dev.allowed_tool_names
    assert "save_agent_specification" not in dev.allowed_tool_names
