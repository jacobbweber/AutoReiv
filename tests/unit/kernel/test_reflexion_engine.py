"""
Unit tests for ReflexionLoopEngine [REQ-VERIFY-002, REQ-VERIFY-003].
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.kernel.reflexion_engine import ReflexionLoopEngine, parse_critic_payload
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

def test_parse_critic_payload_accepts_fenced_json():
    parsed = parse_critic_payload('```json\n{"is_valid": false, "discrepancies": ["missing step"]}\n```')
    assert parsed is not None
    assert parsed["is_valid"] is False
    assert parsed["discrepancies"] == ["missing step"]


def test_parse_critic_payload_rejects_empty_and_non_json():
    assert parse_critic_payload("") is None
    assert parse_critic_payload("looks fine to me") is None
    assert parse_critic_payload('{"ok": true}') is None


@pytest.mark.asyncio
async def test_reflexion_skips_when_no_verifier_or_critic():
    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(
        return_value=ChatMessage(role=Role.ASSISTANT, content="Done.")
    )
    engine = ReflexionLoopEngine(kernel=mock_kernel, tool_registry=MagicMock())
    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Wiki",
        system_prompt="Help",
        allowed_tool_names=[],
    )
    result = await engine.run_reflexion_turn(
        agent=agent,
        session_id="sess_skip",
        user_content="Say hello",
    )
    assert result["status"] == "skipped"
    assert result["verification_passed"] is False
    mock_kernel.gateway.complete.assert_not_called()


@pytest.mark.asyncio
async def test_builtin_critic_passes_on_valid_json():
    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(
        return_value=ChatMessage(role=Role.ASSISTANT, content="The report is complete.")
    )
    mock_kernel.gateway.complete = AsyncMock(
        return_value=MagicMock(
            message=ChatMessage(
                role=Role.ASSISTANT,
                content='{"is_valid": true, "discrepancies": []}',
            )
        )
    )
    engine = ReflexionLoopEngine(kernel=mock_kernel, tool_registry=MagicMock())
    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Wiki",
        system_prompt="Help",
        allowed_tool_names=[],
    )
    result = await engine.run_reflexion_turn(
        agent=agent,
        session_id="sess_critic_pass",
        user_content="Write the report",
        use_builtin_critic=True,
        max_refinements=3,
    )
    assert result["status"] == "verified"
    assert result["verification_passed"] is True
    assert result["attempts_taken"] == 1
    mock_kernel.gateway.complete.assert_awaited()


@pytest.mark.asyncio
async def test_builtin_critic_fails_closed_on_invalid_json():
    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(
        return_value=ChatMessage(role=Role.ASSISTANT, content="Looks good.")
    )
    mock_kernel.gateway.complete = AsyncMock(
        return_value=MagicMock(message=ChatMessage(role=Role.ASSISTANT, content="not json"))
    )
    engine = ReflexionLoopEngine(kernel=mock_kernel, tool_registry=MagicMock())
    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Wiki",
        system_prompt="Help",
        allowed_tool_names=[],
    )
    result = await engine.run_reflexion_turn(
        agent=agent,
        session_id="sess_critic_bad_json",
        user_content="Write the report",
        use_builtin_critic=True,
        max_refinements=2,
    )
    assert result["status"] == "unverified_budget_exhausted"
    assert result["verification_passed"] is False
    assert result["attempts_taken"] == 2
    assert any("valid JSON" in item for item in result["critique_history"])


@pytest.mark.asyncio
async def test_builtin_critic_fails_closed_on_empty_output():
    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(
        return_value=ChatMessage(role=Role.ASSISTANT, content="   ")
    )
    mock_kernel.gateway.complete = AsyncMock()
    engine = ReflexionLoopEngine(kernel=mock_kernel, tool_registry=MagicMock())
    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Wiki",
        system_prompt="Help",
        allowed_tool_names=[],
    )
    result = await engine.run_reflexion_turn(
        agent=agent,
        session_id="sess_empty",
        user_content="Write the report",
        use_builtin_critic=True,
        max_refinements=1,
    )
    assert result["verification_passed"] is False
    assert result["status"] == "unverified_budget_exhausted"
    mock_kernel.gateway.complete.assert_not_called()


@pytest.mark.asyncio
async def test_builtin_critic_refines_when_critic_rejects():
    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(
        side_effect=[
            ChatMessage(role=Role.ASSISTANT, content="Draft v1"),
            ChatMessage(role=Role.ASSISTANT, content="Draft v2 complete"),
        ]
    )
    mock_kernel.gateway.complete = AsyncMock(
        side_effect=[
            MagicMock(
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content='{"is_valid": false, "discrepancies": ["missing conclusion"]}',
                )
            ),
            MagicMock(
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content='{"is_valid": true, "discrepancies": []}',
                )
            ),
        ]
    )
    engine = ReflexionLoopEngine(kernel=mock_kernel, tool_registry=MagicMock())
    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Wiki",
        system_prompt="Help",
        allowed_tool_names=[],
    )
    result = await engine.run_reflexion_turn(
        agent=agent,
        session_id="sess_critic_refine",
        user_content="Write the report",
        use_builtin_critic=True,
        max_refinements=3,
    )
    assert result["status"] == "verified"
    assert result["attempts_taken"] == 2
    assert "missing conclusion" in result["critique_history"][0]

