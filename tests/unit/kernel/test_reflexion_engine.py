"""
Unit tests for ReflexionLoopEngine [REQ-VERIFY-002, REQ-VERIFY-003].
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.kernel.reflexion_engine import ReflexionLoopEngine
from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import AgentProfile


@pytest.mark.asyncio
async def test_reflexion_loop_succeeds_on_first_pass():
    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(
        return_value=ChatMessage(
            role=Role.ASSISTANT,
            content='{"health_score": 99.0, "status": "healthy"}',
        )
    )

    mock_tool_registry = MagicMock()
    # Tool verify passes
    mock_tool_registry.execute = AsyncMock(
        return_value=MagicMock(
            success=True,
            output={"is_valid": True, "discrepancies": []},
            error=None,
        )
    )

    engine = ReflexionLoopEngine(
        kernel=mock_kernel,
        tool_registry=mock_tool_registry,
    )

    agent = AgentProfile(
        id="system-agent",
        name="System Agent",
        description="SRE",
        system_prompt="SRE",
        allowed_tool_names=["assert_json_schema"],
    )

    result = await engine.run_reflexion_turn(
        agent=agent,
        session_id="sess_verify_1",
        user_content="Output platform health report in JSON with health_score and status",
        verifier_tool_name="assert_json_schema",
        verifier_args={"required_keys": ["health_score", "status"]},
        max_refinements=3,
    )

    assert result["status"] == "verified"
    assert result["attempts_taken"] == 1
    assert result["verification_passed"] is True
    assert "health_score" in result["output"]


@pytest.mark.asyncio
async def test_reflexion_loop_refines_after_discrepancy_and_succeeds():
    mock_kernel = MagicMock()
    # 1st attempt produces bad output, 2nd attempt produces valid output
    mock_kernel.run_turn = AsyncMock(
        side_effect=[
            ChatMessage(role=Role.ASSISTANT, content='{"status": "healthy"}'),
            ChatMessage(role=Role.ASSISTANT, content='{"health_score": 98.0, "status": "healthy"}'),
        ]
    )

    mock_tool_registry = MagicMock()
    # 1st verify fails, 2nd verify passes
    mock_tool_registry.execute = AsyncMock(
        side_effect=[
            MagicMock(
                success=True,
                output={"is_valid": False, "discrepancies": ["Missing required key: 'health_score'"]},
                error=None,
            ),
            MagicMock(
                success=True,
                output={"is_valid": True, "discrepancies": []},
                error=None,
            ),
        ]
    )

    engine = ReflexionLoopEngine(
        kernel=mock_kernel,
        tool_registry=mock_tool_registry,
    )

    agent = AgentProfile(
        id="system-agent",
        name="System Agent",
        description="SRE",
        system_prompt="SRE",
        allowed_tool_names=["assert_json_schema"],
    )

    result = await engine.run_reflexion_turn(
        agent=agent,
        session_id="sess_verify_2",
        user_content="Output platform health JSON",
        verifier_tool_name="assert_json_schema",
        verifier_args={"required_keys": ["health_score", "status"]},
        max_refinements=3,
    )

    assert result["status"] == "verified"
    assert result["attempts_taken"] == 2
    assert result["verification_passed"] is True
    assert len(result["critique_history"]) == 1
    assert "Missing required key: 'health_score'" in result["critique_history"][0]
