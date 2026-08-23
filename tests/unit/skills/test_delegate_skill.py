"""
Unit tests for DelegateSubtaskSkill [REQ-A2A-003, REQ-A2A-005].
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.skills.delegate_skill import DelegateSubtaskSkill


@pytest.mark.asyncio
async def test_delegate_subtask_skill_invokes_orchestrator():
    mock_orchestrator = MagicMock()
    mock_orchestrator.dispatch_handoff = AsyncMock(
        return_value={
            "status": "success",
            "output": "Specialist completed analysis.",
            "recipient_agent_id": "librarian",
        }
    )

    skill = DelegateSubtaskSkill(
        current_agent_id="general-assistant",
        session_id="sess_123",
        orchestrator=mock_orchestrator,
    )

    res = await skill.delegate_task(
        target_agent="librarian",
        task_intent="Find relevant wiki articles about memory architectures",
        context_data={"query": "memory"},
    )

    assert res["status"] == "success"
    assert res["output"] == "Specialist completed analysis."
    assert mock_orchestrator.dispatch_handoff.called
    envelope_arg = mock_orchestrator.dispatch_handoff.call_args[0][0]
    assert envelope_arg.sender_agent_id == "general-assistant"
    assert envelope_arg.recipient_agent_id == "librarian"
    assert envelope_arg.session_id == "sess_123"
