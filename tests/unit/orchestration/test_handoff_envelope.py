"""
Unit tests for HandoffEnvelope and SupervisorOrchestrator [REQ-A2A-001, REQ-A2A-002, REQ-A2A-004].
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.kernel.supervisor_orchestrator import SupervisorOrchestrator
from src.domain.gateway.models import ChatMessage, Role
from src.domain.orchestration.models import HandoffEnvelope


def test_handoff_envelope_schema_validation():
    env = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="sysadmin",
        session_id="sess_multi_123",
        task_intent="Inspect disk capacity on /dev/sda",
        context_payload={"host": "nimo-mini-pc", "facts": ["os: ubuntu 24.04"]},
    )
    assert env.sender_agent_id == "general-assistant"
    assert env.recipient_agent_id == "sysadmin"
    assert env.task_intent == "Inspect disk capacity on /dev/sda"
    assert len(env.correlation_id) > 0


@pytest.mark.asyncio
async def test_supervisor_orchestrator_dispatches_to_specialist():
    mock_registry = MagicMock()
    mock_sysadmin = MagicMock()
    mock_sysadmin.id = "sysadmin"
    mock_registry.get_profile = MagicMock(return_value=mock_sysadmin)

    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(
        return_value=ChatMessage(
            role=Role.ASSISTANT,
            content="Disk check complete: 42% utilized, 58GB free.",
        )
    )

    mock_telemetry = MagicMock()

    orchestrator = SupervisorOrchestrator(
        agent_registry=mock_registry,
        agent_kernel=mock_kernel,
        telemetry=mock_telemetry,
    )

    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="sysadmin",
        session_id="sess_test",
        task_intent="Check disk usage",
        context_payload={"environment": "production"},
    )

    result = await orchestrator.dispatch_handoff(envelope)

    assert result["status"] == "success"
    assert "Disk check complete" in result["output"]
    assert result["sender_agent_id"] == "general-assistant"
    assert result["recipient_agent_id"] == "sysadmin"
    assert mock_telemetry.record_handoff_span.called


@pytest.mark.asyncio
async def test_supervisor_orchestrator_rejects_recursion_depth_exceeded():
    mock_registry = MagicMock()
    mock_kernel = MagicMock()
    mock_telemetry = MagicMock()

    orchestrator = SupervisorOrchestrator(
        agent_registry=mock_registry,
        agent_kernel=mock_kernel,
        telemetry=mock_telemetry,
    )

    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="linux-sysadmin",
        session_id="sess_nested",
        task_intent="Nested task",
        depth=3,
    )

    result = await orchestrator.dispatch_handoff(envelope)
    assert result["status"] == "error"
    assert "recursion depth" in result["error"].lower()
    assert mock_telemetry.record_handoff_span.called


@pytest.mark.asyncio
async def test_supervisor_orchestrator_rejects_circular_self_handoff():
    mock_registry = MagicMock()
    mock_kernel = MagicMock()
    mock_telemetry = MagicMock()

    orchestrator = SupervisorOrchestrator(
        agent_registry=mock_registry,
        agent_kernel=mock_kernel,
        telemetry=mock_telemetry,
    )

    envelope = HandoffEnvelope(
        sender_agent_id="linux-sysadmin",
        recipient_agent_id="linux-sysadmin",
        session_id="sess_self",
        task_intent="Self delegating loop",
    )

    result = await orchestrator.dispatch_handoff(envelope)
    assert result["status"] == "error"
    assert "self-handoff" in result["error"].lower()
    assert mock_telemetry.record_handoff_span.called


@pytest.mark.asyncio
async def test_supervisor_orchestrator_resolves_sysadmin_alias():
    mock_registry = MagicMock()
    mock_autoreiv = MagicMock()
    mock_autoreiv.id = "autoreiv"
    mock_registry.get_profile = MagicMock(return_value=mock_autoreiv)

    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(
        return_value=ChatMessage(
            role=Role.ASSISTANT,
            content="AutoReiv inspected system metrics.",
        )
    )

    mock_telemetry = MagicMock()

    orchestrator = SupervisorOrchestrator(
        agent_registry=mock_registry,
        agent_kernel=mock_kernel,
        telemetry=mock_telemetry,
    )

    envelope = HandoffEnvelope(
        sender_agent_id="assistant",
        recipient_agent_id="sysadmin",
        session_id="sess_alias",
        task_intent="Find architecture specs",
    )

    result = await orchestrator.dispatch_handoff(envelope)
    assert result["status"] == "success"
    mock_registry.get_profile.assert_called_with("autoreiv")


def test_handoff_envelope_default_max_turns_is_10():
    env = HandoffEnvelope(
        sender_agent_id="conductor",
        recipient_agent_id="coding",
        session_id="sess_card090",
        task_intent="Implement CARD-001",
    )
    assert env.max_turns == 10


def test_handoff_packet_render_excludes_parent_history():
    from src.domain.orchestration.models import HandoffPacket

    packet = HandoffPacket.from_legacy_envelope(
        task_intent="Ship CARD-098",
        context_payload={
            "history": ["PARENT_SECRET"],
            "messages": ["nope"],
            "facts": ["nimo has 128GB"],
            "constraints": ["do not push"],
            "done_when": "tests green",
            "budget": {"max_turns": 12},
        },
    )
    rendered = packet.render_user_message()
    assert packet.goal == "Ship CARD-098"
    assert "nimo has 128GB" in rendered
    assert "do not push" in rendered
    assert "PARENT_SECRET" not in rendered
    assert "Handoff Packet" in rendered

