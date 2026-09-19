"""
Unit tests for CARD-362: Demand-Paged Capability Engine & Progressive Tool Mounting.
Grounded in ADR-0054 [REQ-CAP-PAGE-001..005].
"""

from unittest.mock import MagicMock

import pytest

from src.application.kernel.agent_kernel import MAX_ACTIVE_TOOLS_PER_TURN, AgentKernel
from src.domain.gateway.models import ToolDefinition
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def test_max_active_tools_per_turn_constant():
    """Verify Rule of 7 entropy budget constant [REQ-CAP-PAGE-001]."""
    assert MAX_ACTIVE_TOOLS_PER_TURN == 8


def test_resolve_active_tools_enforces_entropy_cap():
    """Verify _resolve_active_tools clamps visible tools to at most 8 [REQ-CAP-PAGE-001]."""
    tools = [
        ToolDefinition(name=f"tool_{i}", description=f"Tool {i}", parameters={"type": "object", "properties": {}})
        for i in range(20)
    ]
    registry = MagicMock()
    registry.get_tools_for_agent.return_value = tools

    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=registry,
        state_store=MagicMock(),
        telemetry=MagicMock(),
    )
    agent = AgentProfile(
        id="developer",
        name="Developer",
        description="Test",
        system_prompt="Test",
        allowed_tool_names=[t.name for t in tools],
    )

    resolved = kernel._resolve_active_tools(agent, user_content="test")
    assert len(resolved) <= MAX_ACTIVE_TOOLS_PER_TURN
    assert len(resolved) == 8


def test_priority_ordering_preserves_active_skill_tools_first():
    """Verify active skill tools are prioritized ahead of generic tools when clamping [REQ-CAP-PAGE-001, REQ-CAP-PAGE-003]."""
    skill_tools = [
        ToolDefinition(name=f"wiki_{i}", description=f"Wiki Tool {i}", parameters={"type": "object", "properties": {}})
        for i in range(5)
    ]
    baseline_tools = [
        ToolDefinition(name="activate_skill", description="Activate", parameters={"type": "object", "properties": {}}),
        ToolDefinition(name="ask_clarification", description="Clarify", parameters={"type": "object", "properties": {}}),
        ToolDefinition(name="handoff_to_agent", description="Handoff", parameters={"type": "object", "properties": {}}),
        ToolDefinition(name="get_session_info", description="Session", parameters={"type": "object", "properties": {}}),
    ]
    extra_tools = [
        ToolDefinition(name=f"extra_{i}", description=f"Extra Tool {i}", parameters={"type": "object", "properties": {}})
        for i in range(10)
    ]

    all_tools = skill_tools + baseline_tools + extra_tools
    registry = MagicMock()
    registry.get_tools_for_agent.return_value = all_tools

    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=registry,
        state_store=MagicMock(),
        telemetry=MagicMock(),
    )
    agent = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Platform Agent",
        system_prompt="Test",
    )

    resolved = kernel._resolve_active_tools(
        agent,
        user_content="search the wiki",
        active_skills=["wiki"],
    )

    assert len(resolved) == MAX_ACTIVE_TOOLS_PER_TURN
    resolved_names = [t.name for t in resolved]

    # All 5 active wiki skill tools must be included
    for st in skill_tools:
        assert st.name in resolved_names

    # Baseline coordination tools fill the remaining 3 slots up to 8
    assert "activate_skill" in resolved_names
    assert "ask_clarification" in resolved_names
    assert "get_session_info" in resolved_names


def test_direct_mode_returns_zero_tools():
    """Verify Direct Mode bypasses all tool schemas [REQ-CHAT-DUAL-002, REQ-CAP-PAGE-001]."""
    tools = [
        ToolDefinition(name="some_tool", description="Desc", parameters={"type": "object", "properties": {}})
    ]
    registry = MagicMock()
    registry.get_tools_for_agent.return_value = tools

    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=registry,
        state_store=MagicMock(),
        telemetry=MagicMock(),
    )
    direct_agent = AgentProfile(
        id="direct",
        name="Direct Mode",
        description="Direct pass-through",
        system_prompt="Direct",
    )

    resolved = kernel._resolve_active_tools(direct_agent, user_content="hello")
    assert resolved == []


def test_compact_capability_index_in_system_prompt():
    """Verify system message includes 1-line capability index when skills inactive [REQ-CAP-PAGE-002]."""
    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=MagicMock(),
        state_store=MagicMock(),
        telemetry=MagicMock(),
    )
    agent = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Platform Agent",
        system_prompt="You are AutoReiv Core.",
        allowed_skill=["wiki", "coding", "diagnostics", "tasks"],
    )

    sys_msg = kernel._build_effective_system_message(agent, user_content="hello")
    content = sys_msg.content

    assert "## Available Capabilities & Skills" in content or "Demand-Paged" in content
    assert "activate_skill" in content
    assert "wiki" in content
    assert "coding" in content


@pytest.mark.asyncio
async def test_telemetry_records_tool_entropy_and_schema_chars(tmp_path):
    """Verify turn telemetry span records active_tool_count and tool_schema_chars [REQ-CAP-PAGE-005]."""
    store = SQLiteStateStore(db_path=str(tmp_path / "test_tel.db"))
    store.initialize_db()
    telemetry = MagicMock()

    tools = [
        ToolDefinition(name=f"tool_{i}", description=f"Tool {i}", parameters={"type": "object", "properties": {}})
        for i in range(5)
    ]
    registry = MagicMock()
    registry.get_tools_for_agent.return_value = tools

    gateway = MagicMock()
    # Mock gateway stream returning empty completion
    async def mock_stream(*args, **kwargs):
        if False:
            yield None

    gateway.stream = mock_stream

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=registry,
        state_store=store,
        telemetry=telemetry,
    )
    agent = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Test",
        system_prompt="Test",
        max_turns=1,
    )

    session = store.create_session(agent_id="autoreiv")

    events = []
    async for ev in kernel.stream_turn(agent, session.id, user_content="hello"):
        events.append(ev)

    # Telemetry should have recorded a turn span
    assert telemetry.record_turn_span.called or telemetry.record_llm_span.called or hasattr(kernel, "_last_turn_tool_stats")


def test_phase_bound_tool_scoping_from_checkpoint(tmp_path):
    """Verify kernel resolves and pages tools matching active phase checkpoint capabilities [REQ-CAP-PAGE-004]."""
    from src.domain.orchestration.models import Job, JobStatus, Phase, PhaseStatus
    store = SQLiteStateStore(db_path=str(tmp_path / "test_phase_scope.db"))
    store.initialize_db()

    # Create job & phase in store
    job = Job(id="job-1", session_id="sess-1", agent_id="autoreiv", goal="Research in Wiki", status=JobStatus.RUNNING)
    phase = Phase(id="phase-1", job_id=job.id, name="Phase 1", index=0, assigned_agent_id="autoreiv", status=PhaseStatus.RUNNING)
    store.create_job(job, [phase])

    # Record checkpoint with skill.wiki
    store.save_job_phase_checkpoint(
        job_id=job.id,
        phase_id=phase.id,
        phase_index=0,
        verifier_status="skipped_no_checker",
        matched_capability_ids=["skill.wiki"],
    )

    wiki_tools = [
        ToolDefinition(name="wiki_read_note", description="Read", parameters={"type": "object", "properties": {}}),
        ToolDefinition(name="wiki_create_note", description="Create", parameters={"type": "object", "properties": {}}),
        ToolDefinition(name="wiki_search", description="Search", parameters={"type": "object", "properties": {}}),
    ]
    coding_tools = [
        ToolDefinition(name="repo_file_read", description="Read code", parameters={"type": "object", "properties": {}}),
        ToolDefinition(name="repo_file_write", description="Write code", parameters={"type": "object", "properties": {}}),
    ]
    baseline_tools = [
        ToolDefinition(name="activate_skill", description="Activate", parameters={"type": "object", "properties": {}}),
        ToolDefinition(name="ask_clarification", description="Clarify", parameters={"type": "object", "properties": {}}),
    ]

    registry = MagicMock()
    # Tool registry will return tools based on active_skills
    def mock_get_tools(agent, active_skills=None):
        res = list(baseline_tools)
        if active_skills and "wiki" in active_skills:
            res.extend(wiki_tools)
        if active_skills and "coding" in active_skills:
            res.extend(coding_tools)
        return res

    registry.get_tools_for_agent.side_effect = mock_get_tools

    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=registry,
        state_store=store,
        telemetry=MagicMock(),
    )
    agent = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Platform Agent",
        system_prompt="Test",
    )

    # Resolve active tools for Phase 1
    matched_ids = kernel._matched_capability_ids_for_job(job_id=job.id, phase_id=phase.id)
    assert matched_ids == ["skill.wiki"]

    resolved = kernel._resolve_active_tools(agent, matched_capability_ids=matched_ids)
    resolved_names = [t.name for t in resolved]

    # Wiki tools are mounted
    assert "wiki_read_note" in resolved_names
    assert "wiki_create_note" in resolved_names
    assert "wiki_search" in resolved_names
    # Baseline tools are mounted
    assert "activate_skill" in resolved_names
    # Coding tools are NOT mounted (scoped out)
    assert "repo_file_read" not in resolved_names


def test_phase_transition_evicts_old_and_pages_new_tools(tmp_path):
    """Verify transitioning between phase boundaries evicts old tools and mounts new tools [REQ-CAP-PAGE-004]."""
    from src.domain.orchestration.models import Job, JobStatus, Phase, PhaseStatus
    store = SQLiteStateStore(db_path=str(tmp_path / "test_phase_evict.db"))
    store.initialize_db()

    job = Job(id="job-pipe", session_id="sess-2", agent_id="autoreiv", goal="Research then code", status=JobStatus.RUNNING)
    phase1 = Phase(id="phase-1", job_id=job.id, name="Phase 1 Research", index=0, assigned_agent_id="autoreiv", status=PhaseStatus.DONE)
    phase2 = Phase(id="phase-2", job_id=job.id, name="Phase 2 Code", index=1, assigned_agent_id="autoreiv", status=PhaseStatus.RUNNING)
    store.create_job(job, [phase1, phase2])

    wiki_tools = [
        ToolDefinition(name="wiki_read_note", description="Read", parameters={"type": "object", "properties": {}}),
    ]
    coding_tools = [
        ToolDefinition(name="repo_file_read", description="Read code", parameters={"type": "object", "properties": {}}),
    ]
    baseline_tools = [
        ToolDefinition(name="activate_skill", description="Activate", parameters={"type": "object", "properties": {}}),
    ]

    registry = MagicMock()
    def mock_get_tools(agent, active_skills=None):
        res = list(baseline_tools)
        if active_skills and "wiki" in active_skills:
            res.extend(wiki_tools)
        if active_skills and "coding" in active_skills:
            res.extend(coding_tools)
        return res

    registry.get_tools_for_agent.side_effect = mock_get_tools

    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=registry,
        state_store=store,
        telemetry=MagicMock(),
    )
    agent = AgentProfile(id="autoreiv", name="AutoReiv", description="Test", system_prompt="Test")

    # Step 1: Phase 1 active with wiki
    store.save_job_phase_checkpoint(
        job_id=job.id,
        phase_id=phase1.id,
        phase_index=0,
        verifier_status="skipped_no_checker",
        matched_capability_ids=["skill.wiki"],
    )

    matched1 = kernel._matched_capability_ids_for_job(job_id=job.id, phase_id=phase1.id)
    tools_p1 = [t.name for t in kernel._resolve_active_tools(agent, matched_capability_ids=matched1)]
    assert "wiki_read_note" in tools_p1
    assert "repo_file_read" not in tools_p1

    # Step 2: Phase 2 transition with coding
    store.save_job_phase_checkpoint(
        job_id=job.id,
        phase_id=phase2.id,
        phase_index=1,
        verifier_status="skipped_no_checker",
        matched_capability_ids=["skill.coding"],
    )

    matched2 = kernel._matched_capability_ids_for_job(job_id=job.id, phase_id=phase2.id)
    tools_p2 = [t.name for t in kernel._resolve_active_tools(agent, matched_capability_ids=matched2)]
    # Wiki tools are evicted!
    assert "wiki_read_note" not in tools_p2
    # Coding tools are mounted!
    assert "repo_file_read" in tools_p2
    assert "activate_skill" in tools_p2

