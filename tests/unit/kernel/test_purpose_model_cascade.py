"""
Unit tests for 3-Tier Purpose-to-Model Cascade Resolution [REQ-FORGE-001, REQ-FORGE-002].
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.kernel.agent_kernel import AgentKernel
from src.domain.agents.profiles import BUILTIN_PROFILES
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role
from src.domain.kernel.models import AgentProfile
from src.domain.memory.models import Session
from src.domain.settings.models import ModelPurpose
from tests.unit.agent_packs.catalog import platform_pack_profile


def test_builtin_profiles_have_purposes():
    """Verify shipped agents define valid purpose classifications."""
    profile_map = {p.id: p for p in BUILTIN_PROFILES}
    assert profile_map["agent-builder"].purpose == ModelPurpose.GENERAL
    assert "coding" not in profile_map
    assert "assistant" not in profile_map
    assert platform_pack_profile("assistant").purpose == ModelPurpose.GENERAL
    assert platform_pack_profile("autoreiv").purpose == ModelPurpose.GENERAL


@pytest.mark.asyncio
async def test_kernel_resolves_model_from_global_default_settings():
    """Verify kernel resolves model from global provider_settings when agent is default [REQ-MODEL-003]."""
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        return_value=CompletionResponse(
            model="qwen2.5-coder:7b",
            message=ChatMessage(role=Role.ASSISTANT, content="Execution successful"),
            finish_reason="stop",
        )
    )

    state_store = MagicMock()
    state_store.get_setting.side_effect = lambda key: {
        "provider_settings": {
            "default_provider_id": "ollama",
            "default_model_id": "qwen2.5-coder:7b",
        },
        # Legacy purpose matrix present, but MUST be ignored under REQ-MODEL-003
        "purpose_matrix": {
            "general": "stale-llama:8b",
            "task_execution": "stale-task:7b",
        },
    }.get(key)
    tool_reg = MagicMock()
    telemetry = MagicMock()

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=tool_reg,
        state_store=state_store,
        telemetry=telemetry,
    )

    agent = AgentProfile(
        id="test-coder",
        name="Test Coder",
        description="Coding specialist",
        system_prompt="You code.",
        provider="default",
        model="default",
    )

    session = Session(id="test-session", agent_id=agent.id)

    response = await kernel.run_turn(agent=agent, session_id=session.id, user_content="Write hello world")

    assert response.role == Role.ASSISTANT
    assert gateway.complete.called
    req: CompletionRequest = gateway.complete.call_args[0][0]
    assert req.model == "qwen2.5-coder:7b"


@pytest.mark.asyncio
async def test_kernel_resolves_agent_explicit_provider_and_model():
    """Verify kernel resolves model with explicit provider prefix when configured on agent [REQ-MODEL-001, REQ-MODEL-003]."""
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        return_value=CompletionResponse(
            model="openai/gpt-4o",
            message=ChatMessage(role=Role.ASSISTANT, content="Execution successful"),
            finish_reason="stop",
        )
    )

    state_store = MagicMock()
    state_store.get_setting.return_value = {
        "default_provider_id": "ollama",
        "default_model_id": "llama3.2:3b",
    }
    tool_reg = MagicMock()
    telemetry = MagicMock()

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=tool_reg,
        state_store=state_store,
        telemetry=telemetry,
    )

    agent = AgentProfile(
        id="test-openai-agent",
        name="OpenAI Specialist",
        description="Uses OpenAI",
        system_prompt="Directives",
        provider="openai",
        model="gpt-4o",
    )

    session = Session(id="test-session-openai", agent_id=agent.id)
    response = await kernel.run_turn(agent=agent, session_id=session.id, user_content="Hello")

    assert response.role == Role.ASSISTANT
    assert gateway.complete.called
    req: CompletionRequest = gateway.complete.call_args[0][0]
    assert req.model == "openai/gpt-4o"


@pytest.mark.asyncio
async def test_kernel_respects_explicit_model_override():
    """Verify kernel respects explicit model override over purpose matrix."""
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        return_value=CompletionResponse(
            model="custom-fine-tune:latest",
            message=ChatMessage(role=Role.ASSISTANT, content="Hello"),
            finish_reason="stop",
        )
    )

    state_store = MagicMock()
    state_store.get_setting.return_value = {
        "task_execution": "qwen2.5-coder:7b",
    }
    tool_reg = MagicMock()
    telemetry = MagicMock()

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=tool_reg,
        state_store=state_store,
        telemetry=telemetry,
    )

    agent = AgentProfile(
        id="test-override",
        name="Custom Model Agent",
        description="Uses custom model",
        system_prompt="Custom",
        purpose=ModelPurpose.TASK_EXECUTION,
        model="custom-fine-tune:latest",
    )

    session = Session(id="test-session-2", agent_id=agent.id)

    response = await kernel.run_turn(agent=agent, session_id=session.id, user_content="Hi")

    assert response.role == Role.ASSISTANT
    req: CompletionRequest = gateway.complete.call_args[0][0]
    assert req.model == "custom-fine-tune:latest"
