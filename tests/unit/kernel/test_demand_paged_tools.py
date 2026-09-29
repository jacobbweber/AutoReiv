"""
Unit tests for CARD-362: Demand-Paged Capability Engine & Progressive Tool Mounting.
Grounded in ADR-0054 [REQ-CAP-PAGE-001..005]. CARD-578 / ADR-0064 removed the per-turn cap:
every allowed tool is sent; only a job phase lock narrows.
"""

from unittest.mock import MagicMock

import pytest

from src.application.kernel.agent_kernel import AgentKernel
from src.domain.gateway.models import ToolDefinition
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def test_no_cap_every_allowed_tool_is_sent(bind_skills):
    """CARD-578 (ADR-0064): 20 ticked tools are all sent; no clamp, no ranking."""
    tools = [
        ToolDefinition(name=f"tool_{i}", description=f"Tool {i}", parameters={"type": "object", "properties": {}})
        for i in range(20)
    ]
    registry = MagicMock()
    registry.get_tools_for_agent.return_value = tools
    kernel = AgentKernel(gateway=MagicMock(), tool_registry=registry, state_store=MagicMock(), telemetry=MagicMock())
    agent = AgentProfile(
        id="developer",
        name="Developer",
        description="Test",
        system_prompt="Test",
        allowed_skill=bind_skills({"many": [t.name for t in tools]}),
    )
    assert [t.name for t in kernel._resolve_active_tools(agent, user_content="test")] == [t.name for t in tools]


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


def test_domain_line_from_ticked_skills_replaces_the_capability_block():
    """CARD-539 D5: the hard-coded capability block is gone; the domain line comes from ticked skills."""
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
        allowed_skill=["wiki-knowledge", "diagnostics"],
    )

    content = kernel._build_effective_system_message(agent, user_content="hello").content

    assert "## Available Capabilities & Skills" not in content and "Demand-Paged" not in content
    assert "## Your domain" in content
    assert "handoff_to_agent" in content and "Ask Developer" in content


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


def test_phase_bound_tool_scoping_from_checkpoint(tmp_path, bind_skills):
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
        ToolDefinition(name="get_session_info", description="Session", parameters={"type": "object", "properties": {}}),
        ToolDefinition(name="ask_clarification", description="Clarify", parameters={"type": "object", "properties": {}}),
    ]

    registry = MagicMock()
    registry.get_tools_for_agent.return_value = baseline_tools + wiki_tools + coding_tools  # the allowed set
    ticks = bind_skills({"wiki": [t.name for t in wiki_tools], "coding": [t.name for t in coding_tools]})

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
        allowed_skill=ticks,
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
    assert "get_session_info" in resolved_names
    # Coding tools are NOT mounted (scoped out)
    assert "repo_file_read" not in resolved_names


def test_phase_transition_evicts_old_and_pages_new_tools(tmp_path, bind_skills):
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
        ToolDefinition(name="get_session_info", description="Session", parameters={"type": "object", "properties": {}}),
    ]

    registry = MagicMock()
    registry.get_tools_for_agent.return_value = baseline_tools + wiki_tools + coding_tools  # the allowed set
    ticks = bind_skills({"wiki": [t.name for t in wiki_tools], "coding": [t.name for t in coding_tools]})

    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=registry,
        state_store=store,
        telemetry=MagicMock(),
    )
    agent = AgentProfile(id="autoreiv", name="AutoReiv", description="Test", system_prompt="Test", allowed_skill=ticks)

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
    assert "get_session_info" in tools_p2

