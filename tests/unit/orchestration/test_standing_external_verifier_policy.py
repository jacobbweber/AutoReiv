"""CARD-216 Standing External Verifier Policy [REQ-VERIFY-EXT-001..004].

Red-first: Reflexion/retry only with named binary checker; missing -> skipped_no_checker.
Cites: Shinn Reflexion 2023; Panickssery 2024 same-model judges.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.orchestration.external_verifier_policy import (
    VerifyOutcomeStatus,
    apply_phase_complete_verify_gate,
    resolve_verify_outcome,
)
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import AgentProfile
from src.domain.orchestration.models import HandoffPacket
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.fixture
def orchestrator(temp_db_path):
    return JobPhaseOrchestrator(SQLiteStateStore(db_path=temp_db_path))


def test_req_verify_ext_002_missing_checker_is_skipped_no_checker():
    """Missing checker -> skipped_no_checker; never verification_passed [REQ-VERIFY-EXT-002]."""
    outcome = resolve_verify_outcome(checker=None, checker_passed=None)
    assert outcome.status == VerifyOutcomeStatus.SKIPPED_NO_CHECKER
    assert outcome.verification_passed is False
    assert outcome.status.value == "skipped_no_checker"


def test_req_verify_ext_001_named_checker_binary_pass_and_fail():
    """Named checker binary results map to verified/failed [REQ-VERIFY-EXT-001]."""
    ok = resolve_verify_outcome(checker="assert_json_schema", checker_passed=True)
    assert ok.status == VerifyOutcomeStatus.VERIFIED
    assert ok.verification_passed is True

    bad = resolve_verify_outcome(checker="pytest", checker_passed=False)
    assert bad.status == VerifyOutcomeStatus.FAILED
    assert bad.verification_passed is False


def test_req_verify_ext_002_same_model_critic_never_counts_as_standing_pass():
    """Same-model critic alone must not yield standing verified [REQ-VERIFY-EXT-002]."""
    # Standing policy: builtin/same-model path is not an external checker.
    outcome = resolve_verify_outcome(
        checker=None,
        checker_passed=True,
        used_same_model_critic=True,
    )
    assert outcome.status == VerifyOutcomeStatus.SKIPPED_NO_CHECKER
    assert outcome.verification_passed is False


def test_req_verify_ext_003_phase_complete_gate_records_skipped_no_checker(orchestrator):
    """Phase-complete gate records skipped_no_checker when no checker [REQ-VERIFY-EXT-003]."""
    job = orchestrator.create_job_with_phases(
        goal="ship",
        session_id="sess_ext_verify",
        agent_id="assistant",
        phase_specs=[
            {"name": "Build", "success_rule": "built", "verify_checker": None},
            {"name": "Ship", "success_rule": "shipped"},
        ],
    )
    phases = orchestrator._store.list_phases_for_job(job.id)
    started = orchestrator.start_phase(phases[0].id)
    packet = HandoffPacket(
        goal="ship",
        facts=["built"],
        constraints=[],
        done_when="built",
        budget={},
    )
    gate = apply_phase_complete_verify_gate(
        orchestrator,
        phase_id=started.id,
        output_packet=packet,
        checker_passed=None,
    )
    assert gate["status"] == "skipped_no_checker"
    assert gate["verification_passed"] is False
    # Phase may complete (advance) but must not claim verified.
    refreshed = orchestrator._store.get_phase(started.id)
    assert refreshed.status.value == "done"
    facts = []
    if refreshed.output_packet_json:
        import json

        facts = json.loads(refreshed.output_packet_json).get("facts") or []
    assert any("skipped_no_checker" in str(f) for f in facts)


@pytest.mark.asyncio
async def test_req_verify_ext_003_run_verified_turn_skips_without_named_checker():
    """run_verified_turn without named checker is skipped_no_checker [REQ-VERIFY-EXT-003]."""
    from src.application.kernel.agent_kernel import AgentKernel

    mock_gateway = MagicMock()
    mock_gateway.default_provider_id = "ollama"
    mock_gateway.default_model_id = "qwen3.8:latest"
    store = MagicMock()
    store.get_messages.return_value = []
    store.append_message = MagicMock()
    tool_reg = MagicMock()
    tool_reg.get_tools_for_agent.return_value = []

    kernel = AgentKernel(
        gateway=mock_gateway,
        tool_registry=tool_reg,
        state_store=store,
        telemetry=MagicMock(),
    )
    kernel.run_turn = AsyncMock(
        return_value=ChatMessage(role=Role.ASSISTANT, content="hello without check")
    )

    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="d",
        system_prompt="s",
        allowed_tool_names=[],
    )
    result = await kernel.run_verified_turn(
        agent=agent,
        session_id="sess_no_checker",
        user_content="say hi",
        verifier_tool_name=None,
    )
    assert result["verification_passed"] is False
    assert result["status"] in {"skipped_no_checker", "skipped"}
    # Prefer the standing enum string once wired.
    assert result["status"] == "skipped_no_checker"


def test_req_verify_ext_004_chat_and_observability_surface_status_strings():
    """Chat + Observability surface verified / skipped_no_checker / failed [REQ-VERIFY-EXT-004]."""
    from pathlib import Path

    chat_js = Path("src/web/static/modules/studios/chat.js").read_text(encoding="utf-8")
    obs_js = Path("src/web/static/modules/studios/observability.js").read_text(encoding="utf-8")
    assert "skipped_no_checker" in chat_js
    assert "skipped_no_checker" in obs_js
    for token in ("verified", "failed"):
        assert token in chat_js
        # Observability must mention verify statuses (not only generic 'failed' elsewhere).
        assert "skipped_no_checker" in obs_js or "verify_status" in obs_js


def test_req_verify_ext_citations_in_card():
    """Card cites Shinn Reflexion 2023 and Panickssery 2024 [REQ-VERIFY-EXT-006]."""
    from pathlib import Path

    card = Path(".github/cards/CARD-216-standing-external-verifier-policy.md").read_text(
        encoding="utf-8"
    )
    assert "Shinn" in card and "2023" in card
    assert "Panickssery" in card and "2024" in card
