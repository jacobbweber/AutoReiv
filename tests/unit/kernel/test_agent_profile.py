"""
Unit tests for Agent Profile & Tone Formatter [REQ-KERNEL-001].
"""

import pytest
from pydantic import ValidationError

from src.domain.kernel.errors import (
    KernelError,
    ToolPermissionDeniedError,
)
from src.domain.kernel.models import (
    AgentProfile,
    AgentTone,
    KernelEvent,
    KernelEventType,
    ToolResult,
)


def test_agent_profile_creation_valid():
    profile = AgentProfile(
        id="general-assistant",
        name="General Assistant",
        description="Daily personal orchestrator",
        system_prompt="You are a helpful AI assistant.",
        tone=AgentTone.FRIENDLY,
        model="default",
        allowed_tool_names=["task_tracker"],
        max_turns=10,
    )
    assert profile.id == "general-assistant"
    assert profile.name == "General Assistant"
    assert profile.tone == AgentTone.FRIENDLY
    assert profile.allowed_tool_names == ["task_tracker"]
    assert profile.max_turns == 10


def test_agent_profile_empty_id_raises_validation_error():
    with pytest.raises(ValidationError):
        AgentProfile(
            id="",
            name="No ID",
            description="Invalid",
            system_prompt="Prompt",
        )


def test_agent_profile_tone_formatting():
    profile = AgentProfile(
        id="sysadmin",
        name="Linux Sysadmin",
        description="Server admin",
        system_prompt="You are an SRE.",
        tone=AgentTone.TECHNICAL,
    )
    full_prompt = profile.get_effective_system_prompt()
    assert "You are an SRE." in full_prompt
    assert "Tone directive: Technical" in full_prompt


def test_agent_profile_default_tone_no_suffix():
    profile = AgentProfile(
        id="plain",
        name="Plain Agent",
        description="Plain",
        system_prompt="Base prompt.",
        tone=AgentTone.DEFAULT,
    )
    full_prompt = profile.get_effective_system_prompt()
    assert full_prompt == "Base prompt."


def test_tool_result_model():
    res = ToolResult(
        call_id="call_001",
        tool_name="get_stats",
        output={"cpu": "12%"},
        success=True,
        duration_ms=45.2,
    )
    assert res.call_id == "call_001"
    assert res.output["cpu"] == "12%"
    assert res.success is True
    assert res.error is None


def test_kernel_event_model():
    event = KernelEvent(
        event_type=KernelEventType.TOKEN,
        content="Streaming word",
        reasoning_content="",
    )
    assert event.event_type == KernelEventType.TOKEN
    assert event.content == "Streaming word"


def test_kernel_errors():
    err = ToolPermissionDeniedError(
        "Agent 'general-assistant' not authorized for tool 'bash'",
        agent_id="general-assistant",
        tool_name="bash",
    )
    assert isinstance(err, KernelError)
    assert err.agent_id == "general-assistant"
    assert err.tool_name == "bash"
