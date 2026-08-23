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


def test_builtin_profiles_have_purposes():
    """Verify all built-in profiles define valid purpose classifications."""
    profile_map = {p.id: p for p in BUILTIN_PROFILES}
    assert profile_map["linux-sysadmin"].purpose == ModelPurpose.TASK_EXECUTION
    assert profile_map["auditor-critic"].purpose == ModelPurpose.REASONING
    assert profile_map["librarian"].purpose == ModelPurpose.AUXILIARY
    assert profile_map["general-assistant"].purpose == ModelPurpose.GENERAL
    assert profile_map["system-agent"].purpose == ModelPurpose.GENERAL


@pytest.mark.asyncio
async def test_kernel_resolves_model_from_purpose_matrix():
    """Verify kernel resolves model from purpose matrix when agent model is 'default'."""
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        return_value=CompletionResponse(
            model="qwen2.5-coder:7b",
            message=ChatMessage(role=Role.ASSISTANT, content="Execution successful"),
            finish_reason="stop",
        )
    )

    state_store = MagicMock()
    state_store.get_setting.return_value = {
        "general": "llama3.1:8b",
        "task_execution": "qwen2.5-coder:7b",
        "reasoning": "qwen3.6:35b",
        "auxiliary": "nemotron-mini:latest",
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
        id="test-coder",
        name="Test Coder",
        description="Coding specialist",
        system_prompt="You code.",
        purpose=ModelPurpose.TASK_EXECUTION,
        model="default",
    )

    session = Session(id="test-session", agent_id=agent.id)

    response = await kernel.run_turn(agent=agent, session_id=session.id, user_content="Write hello world")

    assert response.role == Role.ASSISTANT
    assert gateway.complete.called
    req: CompletionRequest = gateway.complete.call_args[0][0]
    assert req.model == "qwen2.5-coder:7b"


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
