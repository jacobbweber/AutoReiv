"""
Integration tests for CARD-405: Universal Cognitive Memory Readiness across all agents.

Verifies that all agents (autoreiv, tutor, developer, custom agents) have cognitive
memory tools, system prompt grounding, and safety policy authorizations active
out of the box, while direct remains a strict pass-through.
"""

from __future__ import annotations

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.memory.agent_memory_tools import AgentMemoryTools
from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    ToolCall,
)
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_data_dir(tmp_path):
    return tmp_path


@pytest.fixture
def store(temp_data_dir):
    return SQLiteStateStore(db_path=temp_data_dir / "autoreiv.db")


@pytest.fixture
def gate(store):
    return ToolPolicyGate(store=store)


@pytest.fixture
def registry(temp_data_dir, store):
    reg = ScopedToolRegistry(state_store=store)
    mem_tools = AgentMemoryTools(data_dir=temp_data_dir)
    reg.register_tool(
        name="recall_agent_memory",
        description="Recall facts",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        handler=mem_tools.recall_agent_memory,
    )
    reg.register_tool(
        name="memorize_fact",
        description="Memorize fact",
        parameters={
            "type": "object",
            "properties": {
                "entity": {"type": "string"},
                "attribute": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["entity", "attribute", "value"],
        },
        handler=mem_tools.memorize_fact,
    )
    return reg


def test_universal_memory_tools_exposure_and_policy(registry, gate):
    """Verify tool discovery in registry and safety clearance in gate for all agents."""
    agents = [
        AgentProfile(
            id="autoreiv",
            name="AutoReiv",
            description="Companion and SRE",
            system_prompt="You are AutoReiv.",
            memory_enabled=True,
        ),
        AgentProfile(
            id="tutor",
            name="Tutor",
            description="Educational specialist",
            system_prompt="You are Tutor.",
            memory_enabled=True,
        ),
        AgentProfile(
            id="developer",
            name="Developer",
            description="Software engineer",
            system_prompt="You are Developer.",
            memory_enabled=True,
        ),
        AgentProfile(
            id="custom_researcher",
            name="Custom Researcher",
            description="Custom research agent",
            system_prompt="You are Researcher.",
            memory_enabled=True,
        ),
    ]

    for ag in agents:
        # 1. Scoped registry exposes memory tools
        tools = registry.get_tools_for_agent(ag)
        tool_names = {t.name for t in tools}
        assert "recall_agent_memory" in tool_names, f"{ag.id} missing recall_agent_memory"
        assert "memorize_fact" in tool_names, f"{ag.id} missing memorize_fact"

        # 2. ToolPolicyGate evaluates memory tools as ALLOW
        call_recall = ToolCall(id="c1", name="recall_agent_memory", arguments={"query": "test"})
        dec_recall = gate.evaluate(
            call_recall,
            ag,
            registry_tool_names={"recall_agent_memory", "memorize_fact"},
        )
        assert dec_recall.verdict == ToolPolicyVerdict.ALLOW, f"{ag.id} blocked on recall: {dec_recall.reason}"

        call_mem = ToolCall(
            id="c2",
            name="memorize_fact",
            arguments={"entity": "user", "attribute": "name", "value": "Jacob"},
        )
        dec_mem = gate.evaluate(
            call_mem,
            ag,
            registry_tool_names={"recall_agent_memory", "memorize_fact"},
        )
        assert dec_mem.verdict == ToolPolicyVerdict.ALLOW, f"{ag.id} blocked on memorize: {dec_mem.reason}"

    # Direct agent must NOT receive or be authorized for memory tools
    direct = AgentProfile(
        id="direct",
        name="Direct",
        description="Fast direct proxy",
        system_prompt="Direct pass-through.",
        memory_enabled=False,
    )
    direct_tools = registry.get_tools_for_agent(direct)
    assert len(direct_tools) == 0

    dec_direct = gate.evaluate(
        ToolCall(id="c3", name="recall_agent_memory", arguments={"query": "test"}),
        direct,
        registry_tool_names={"recall_agent_memory", "memorize_fact"},
    )
    assert dec_direct.verdict == ToolPolicyVerdict.BLOCK


@pytest.mark.asyncio
async def test_universal_memory_tools_execution_and_isolation(registry, temp_data_dir):
    """Verify execution authorization and data isolation across different agents."""
    tutor = AgentProfile(
        id="tutor",
        name="Tutor",
        description="Tutor agent",
        system_prompt="You are Tutor.",
        memory_enabled=True,
    )
    autoreiv = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="AutoReiv agent",
        system_prompt="You are AutoReiv.",
        memory_enabled=True,
    )

    # 1. Tutor memorizes a fact
    res1 = await registry.execute(
        tool_call=ToolCall(
            id="t1",
            name="memorize_fact",
            arguments={"entity": "learner", "attribute": "math_mastery", "value": "calculus"},
        ),
        agent=tutor,
    )
    assert res1.success is True, f"Tutor memorize failed: {res1.error}"
    assert res1.output["status"] == "ok"

    # 2. Tutor recalls the fact
    res2 = await registry.execute(
        tool_call=ToolCall(
            id="t2",
            name="recall_agent_memory",
            arguments={"query": "math_mastery"},
        ),
        agent=tutor,
    )
    assert res2.success is True, f"Tutor recall failed: {res2.error}"
    facts = res2.output.get("facts", [])
    assert any(f["value"] == "calculus" for f in facts)

    # 3. AutoReiv recalls math_mastery -> must be empty (isolated database)
    res3 = await registry.execute(
        tool_call=ToolCall(
            id="t3",
            name="recall_agent_memory",
            arguments={"query": "math_mastery"},
        ),
        agent=autoreiv,
    )
    assert res3.success is True
    assert len(res3.output.get("facts", [])) == 0

    # 4. Verify physical database locations
    tutor_db = temp_data_dir / "packs" / "tutor" / "tutor_memory.db"
    autoreiv_db = temp_data_dir / "packs" / "autoreiv" / "autoreiv_memory.db"
    assert tutor_db.exists()
    assert autoreiv_db.exists()


@pytest.mark.asyncio
async def test_universal_system_prompt_grounding_cold_start(temp_data_dir, store, registry):
    """Verify system prompt grounding on cold start (0 facts) across all agents."""
    gateway = MultiProviderGateway()
    collector = TelemetryCollector(store=store)
    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=registry,
        state_store=store,
        telemetry=collector,
        data_dir=temp_data_dir,
    )

    tutor = AgentProfile(
        id="tutor",
        name="Tutor",
        description="Tutor agent",
        system_prompt="You are Tutor.",
        memory_enabled=True,
    )
    autoreiv = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="AutoReiv agent",
        system_prompt="You are AutoReiv.",
        memory_enabled=True,
    )
    direct = AgentProfile(
        id="direct",
        name="Direct",
        description="Direct pass-through",
        system_prompt="You are Direct.",
        memory_enabled=False,
    )

    # Cold start check for Tutor
    msg_tutor = kernel._build_effective_system_message(
        agent=tutor,
        user_content="Hello, what can you remember?",
    )
    prompt_tutor = msg_tutor.content
    assert "[Agent Brain - Cognitive Memory System]" in prompt_tutor
    assert "tutor_memory.db" in prompt_tutor
    assert "recall_agent_memory" in prompt_tutor
    assert "memorize_fact" in prompt_tutor

    # Cold start check for AutoReiv
    msg_autoreiv = kernel._build_effective_system_message(
        agent=autoreiv,
        user_content="Hello AutoReiv",
    )
    prompt_autoreiv = msg_autoreiv.content
    assert "[Agent Brain - Cognitive Memory System]" in prompt_autoreiv
    assert "autoreiv_memory.db" in prompt_autoreiv

    # Direct agent check (must NOT have memory prompt block)
    msg_direct = kernel._build_effective_system_message(
        agent=direct,
        user_content="Hello Direct",
    )
    prompt_direct = msg_direct.content
    assert "[Agent Brain - Cognitive Memory System]" not in prompt_direct

    # Now store a fact in Tutor's memory and check populated shelf prompt
    tutor_repo = AgentMemoryRepository(agent_id="tutor", data_dir=temp_data_dir)
    tutor_repo.initialize_schema()
    tutor_repo.add_semantic_fact("learner", "current_topic", "Quantum Mechanics", category="academic")

    msg_tutor_populated = kernel._build_effective_system_message(
        agent=tutor,
        user_content="Quantum Mechanics",
    )
    prompt_tutor_populated = msg_tutor_populated.content
    assert "[Agent Brain - Cognitive Memory System]" in prompt_tutor_populated
    assert "[Agent Brain - Recalled Relevant Facts]" in prompt_tutor_populated
    assert "learner.current_topic: Quantum Mechanics" in prompt_tutor_populated


class MockMemoryLLM(LLMProviderPort):
    """Mock LLM returning structured candidate fact extraction JSON."""

    provider_id: str = "mock"

    def __init__(self, response_text: str):
        self.response_text = response_text

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(
            model=request.model,
            message=ChatMessage(role=Role.ASSISTANT, content=self.response_text),
            finish_reason="stop",
        )


@pytest.mark.asyncio
async def test_goal_job_background_memory_extraction(temp_data_dir):
    """Verify background turn extraction successfully writes into <agent_id>_memory.db."""
    from src.web.routers.chat import _background_extract_turn_memory

    mock_llm = MockMemoryLLM(
        response_text='```json\n[{"entity": "project", "attribute": "db_driver", "value": "sqlite", "category": "architecture", "action": "ADD"}]\n```'
    )

    await _background_extract_turn_memory(
        agent_id="tutor",
        user_text="We have chosen SQLite as our primary database driver.",
        assistant_text="Confirmed. I have noted that SQLite is our primary database driver.",
        session_id="sess_goal_1",
        llm_service=mock_llm,
        data_dir=temp_data_dir,
    )

    repo = AgentMemoryRepository(agent_id="tutor", data_dir=temp_data_dir)
    facts = repo.list_semantic_facts()
    assert len(facts) >= 1
    assert facts[0]["entity"] == "project"
    assert facts[0]["value"] == "sqlite"

    summaries = repo.list_session_summaries()
    assert len(summaries) >= 1
    assert "sess_goal_1" in summaries[0]["session_id"]
