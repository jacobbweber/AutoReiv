"""CARD-596: Agent scopes and direct chat.

Each agent keeps to its scope, the user picks who to talk to; only Architect/Toolsmith hand off to Developer.
- AutoReiv, Tutor, and Developer have neither handoff_to_agent nor lookup_agents in resolve_allowed_tools.
- Toolsmith gets handoff_to_agent through native-tool-engineering, which refuses targets other than 'developer'.
- Architect keeps hand_off_card only.
- AutoReiv has no education skills and no coordination skill.
- domain_line builds a short roster of other agents and tells the user which agent to open in Chat without tool calls.
"""

from __future__ import annotations

import pytest

from src.application.agent_skills.allowed_tools import domain_line, resolve_allowed_tools
from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS
from src.application.orchestration.directory_service import AgentDirectoryService
from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.application.skills.orchestration_tools import OrchestrationTools
from src.domain.kernel.models import KernelEvent, KernelEventType
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.content.store import get_store
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_skills.catalog import platform_pack_profile


def test_required_platform_tools_excludes_handoff_and_lookup():
    assert "handoff_to_agent" not in REQUIRED_PLATFORM_TOOLS
    assert "lookup_agents" not in REQUIRED_PLATFORM_TOOLS


def test_agent_tool_permissions():
    autoreiv = platform_pack_profile("autoreiv")
    tutor = platform_pack_profile("tutor")
    dev = platform_pack_profile("developer")
    toolsmith = platform_pack_profile("toolsmith")
    architect = platform_pack_profile("architect")

    auto_tools = set(resolve_allowed_tools(autoreiv))
    assert "handoff_to_agent" not in auto_tools
    assert "lookup_agents" not in auto_tools

    tutor_tools = set(resolve_allowed_tools(tutor))
    assert "handoff_to_agent" not in tutor_tools
    assert "lookup_agents" not in tutor_tools

    dev_tools = set(resolve_allowed_tools(dev))
    assert "handoff_to_agent" not in dev_tools
    assert "lookup_agents" not in dev_tools

    toolsmith_tools = set(resolve_allowed_tools(toolsmith))
    assert "handoff_to_agent" in toolsmith_tools
    assert "lookup_agents" not in toolsmith_tools

    arch_tools = set(resolve_allowed_tools(architect))
    assert "hand_off_card" in arch_tools
    assert "handoff_to_agent" not in arch_tools
    assert "lookup_agents" not in arch_tools


def test_agent_ticked_skills_scopes():
    autoreiv = platform_pack_profile("autoreiv")
    assert "socratic-tutoring" not in autoreiv.allowed_skill
    assert "coordination" not in autoreiv.allowed_skill
    assert "wiki-templates" in autoreiv.allowed_skill

    tutor = platform_pack_profile("tutor")
    education_skills = {
        "socratic-tutoring",
        "start-resume-topic",
        "quiz-turn",
        "flashcard-turn",
        "due-review",
        "education-wiki-curation",
        "progress-summary",
    }
    assert set(tutor.allowed_skill) == education_skills


@pytest.mark.asyncio
async def test_handoff_to_agent_refuses_targets_other_than_developer(tmp_path):
    store = SQLiteStateStore(db_path=tmp_path / "test_state.db")
    registry = BuiltinAgentRegistry(state_store=store)
    registry.register_profile(platform_pack_profile("direct"))
    registry.register_profile(platform_pack_profile("autoreiv"))
    registry.register_profile(platform_pack_profile("developer"))
    directory = AgentDirectoryService(agent_registry=registry, state_store=store)

    class MockStreamKernel:
        async def stream_turn(self, agent, session_id, user_content=None, approval_mode="ask", resume=False):
            yield KernelEvent(event_type=KernelEventType.TOKEN, content="Subagent completed task successfully")
            yield KernelEvent(
                event_type=KernelEventType.TURN_END,
                content="Subagent completed task successfully",
                is_finished=True,
            )

    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel_factory=lambda profile: MockStreamKernel(),
    )
    tools = OrchestrationTools(
        directory_service=directory,
        handoff_engine=engine,
        caller_agent_id="toolsmith",
        session_id="sess_toolsmith",
    )

    # Calling target other than developer fails closed
    res_direct = await tools.handoff_to_agent(target_agent_id="direct", task_directive="check disk")
    assert "developer" in res_direct.lower()
    assert "only allows target 'developer'" in res_direct.lower() or "refused" in res_direct.lower() or "failed" in res_direct.lower()

    res_auto = await tools.handoff_to_agent(target_agent_id="autoreiv", task_directive="check wiki")
    assert "developer" in res_auto.lower()

    # Calling target developer succeeds
    res_dev = await tools.handoff_to_agent(target_agent_id="developer", task_directive="write code")
    assert "completed" in res_dev.lower()


def test_domain_line_roster_and_direct_chat_guidance():
    autoreiv = platform_pack_profile("autoreiv")
    line = domain_line(autoreiv)

    assert "lookup_agents" not in line
    assert "handoff_to_agent" not in line
    assert "Tutor" in line
    assert "Chat" in line
    assert 'end your reply with "You can use Ask Developer to add this."' in line


def test_authoring_and_health_skills_have_no_handoff():
    store = get_store()
    authoring = store.skills.load("agent-authoring")
    assert authoring is not None
    assert "handoff_to_agent" not in authoring.tools
    assert "lookup_agents" not in authoring.tools
    assert "Ask Developer" in authoring.meta.get("description", "") or "Ask Developer" in authoring.body

    health = store.skills.load("platform-health")
    assert health is not None
    assert "handoff_to_agent" not in health.body
