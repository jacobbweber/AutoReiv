"""CARD-172: Intent Distill, scenario verify, outer vs inner rinse (TDD)."""

from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from src.application.agent_training_factory.failure_class import (
    FAILURE_IMPLEMENTATION,
    FAILURE_SOP_HOW,
    classify_failure,
)
from src.application.agent_training_factory.question_battery import (
    DEFAULT_INTENT_QUESTIONS,
    implicated_questions,
)
from src.application.agent_training_factory.orchestrator import FactoryOrchestrator
from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.intent_distill import IntentDistillPhase
from src.application.agent_training_factory.phases.scenario_verify import ScenarioVerifyPhase
from src.application.agent_training_factory.registry import (
    DEFAULT_PIPELINE,
    PHASE_AUTHOR,
    PHASE_GROUND,
    PHASE_INTENT_DISTILL,
    PHASE_SCENARIO_VERIFY,
    PHASE_VERIFY,
    PhaseRegistry,
    default_registry,
)
from src.domain.orchestration.factory_packets import (
    EvalPacket,
    FactoryJob,
    FactoryPacket,
)
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


# ---------------------------------------------------------------------------
# Registry / pipeline
# ---------------------------------------------------------------------------


def test_pipeline_order_includes_intent_and_scenario():
    assert DEFAULT_PIPELINE == [
        "intent_distill",
        "ground",
        "blueprint",
        "author",
        "scenario_verify",
        "verify",
        "optimize",
        "promote",
    ]


def test_default_registry_registers_new_phases():
    reg = default_registry()
    assert reg.get(PHASE_INTENT_DISTILL) is not None
    assert reg.get(PHASE_SCENARIO_VERIFY) is not None
    assert reg.get(PHASE_INTENT_DISTILL).id == PHASE_INTENT_DISTILL
    assert reg.get(PHASE_SCENARIO_VERIFY).id == PHASE_SCENARIO_VERIFY


def test_inner_rinse_from_scenario_and_code_verify_goes_to_author():
    reg = PhaseRegistry()
    assert reg.next_phase(PHASE_SCENARIO_VERIFY, "fail") == PHASE_AUTHOR
    assert reg.next_phase(PHASE_VERIFY, "fail") == PHASE_AUTHOR


def test_outer_rinse_goes_to_intent_distill():
    reg = PhaseRegistry()
    assert reg.next_phase(PHASE_SCENARIO_VERIFY, "outer") == PHASE_INTENT_DISTILL
    assert reg.next_phase(PHASE_VERIFY, "outer") == PHASE_INTENT_DISTILL


def test_exhausted_terminates():
    reg = PhaseRegistry()
    assert reg.next_phase(PHASE_SCENARIO_VERIFY, "exhausted") == "failed"
    assert reg.next_phase(PHASE_VERIFY, "exhausted") == "failed"


def test_ground_can_skip_blueprint_to_author():
    reg = PhaseRegistry()
    assert reg.next_phase(PHASE_GROUND, "skip_blueprint") == PHASE_AUTHOR


def test_author_advances_to_scenario_verify():
    reg = PhaseRegistry()
    assert reg.next_phase(PHASE_AUTHOR, "ok") == PHASE_SCENARIO_VERIFY


def test_scenario_ok_advances_to_code_verify():
    reg = PhaseRegistry()
    assert reg.next_phase(PHASE_SCENARIO_VERIFY, "ok") == PHASE_VERIFY


def test_registry_has_no_product_name_branches():
    """Orchestrator/registry must stay domain-agnostic (no Hyper-V ifs)."""
    import inspect
    from src.application.agent_training_factory import registry as reg_mod
    from src.application.agent_training_factory import orchestrator as orch_mod

    for src in (inspect.getsource(reg_mod), inspect.getsource(orch_mod)):
        low = src.lower()
        assert "hyper-v" not in low
        assert "hyperv" not in low
        assert "finance" not in low


# ---------------------------------------------------------------------------
# Question battery
# ---------------------------------------------------------------------------


def test_default_question_battery_has_seven_locked_intents():
    assert len(DEFAULT_INTENT_QUESTIONS) == 7
    ids = [q["id"] for q in DEFAULT_INTENT_QUESTIONS]
    assert ids == [
        "outcome",
        "constraints",
        "medium",
        "professional_sop",
        "official_guidance",
        "unknowns",
        "scenarios",
    ]
    for q in DEFAULT_INTENT_QUESTIONS:
        assert q["text"].strip()
        assert isinstance(q.get("implicated_by"), list)


def test_implicated_questions_reask_subset_on_sop_failure():
    fail = "Missing SOP for bootable media procedure; medium misunderstanding"
    subset = implicated_questions(fail)
    ids = [q["id"] for q in subset]
    assert "professional_sop" in ids or "medium" in ids
    assert len(subset) < len(DEFAULT_INTENT_QUESTIONS)
    assert len(subset) >= 1


def test_implicated_questions_fallback_all_when_no_match():
    subset = implicated_questions("completely unrelated xyz failure token")
    assert len(subset) == len(DEFAULT_INTENT_QUESTIONS)


# ---------------------------------------------------------------------------
# Failure class (domain-agnostic)
# ---------------------------------------------------------------------------


def test_classify_sop_how_keywords():
    assert classify_failure("Missing SOP for the role task") == FAILURE_SOP_HOW
    assert classify_failure("unknown procedure in runbook") == FAILURE_SOP_HOW
    assert classify_failure("medium misunderstanding: wrong target medium") == FAILURE_SOP_HOW


def test_classify_implementation_default():
    assert classify_failure("Safety Guardrail Alert: Path traversal") == FAILURE_IMPLEMENTATION
    assert classify_failure("AST parse error in tool") == FAILURE_IMPLEMENTATION


def test_classify_scenario_misses_as_sop_when_coverage_gap():
    assert (
        classify_failure(
            "Scenario Verify FAILED",
            scenario_misses=["Professional SOP covers bootable media path"],
        )
        == FAILURE_SOP_HOW
    )


def test_classify_no_product_keywords_required():
    """Classifier must not key off product names."""
    import inspect
    from src.application.agent_training_factory import failure_class as fc

    src = inspect.getsource(fc).lower()
    assert "hyperv" not in src
    assert "hyper-v" not in src
    assert "finance" not in src


# ---------------------------------------------------------------------------
# Persistence fixtures
# ---------------------------------------------------------------------------


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
def factory_repo(temp_db_path):
    store = SQLiteStateStore(db_path=temp_db_path)
    store.initialize_db()
    return FactoryPacketRepository(store)


def test_factory_job_persists_outer_rinse_fields(factory_repo):
    job = FactoryJob(
        id="fjob_outer_persist",
        target_agent_id="demo",
        session_id="sess_o",
        status="queued",
        seed_intent="demo intent",
        outer_rinse_count=1,
        max_outer_rinses=2,
        failure_class=FAILURE_SOP_HOW,
        current_node_id=PHASE_INTENT_DISTILL,
    )
    factory_repo.save_job(job)
    fetched = factory_repo.get_job("fjob_outer_persist")
    assert fetched is not None
    assert fetched.outer_rinse_count == 1
    assert fetched.max_outer_rinses == 2
    assert fetched.failure_class == FAILURE_SOP_HOW


# ---------------------------------------------------------------------------
# Intent Distill phase
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intent_distill_writes_structured_answers_packet(factory_repo, monkeypatch):
    job = FactoryJob(
        id="fjob_distill",
        target_agent_id="demo",
        session_id="sess_d",
        status="running",
        seed_intent="Operate a host via CLI with a professional SOP",
        objectives=["Prove capability with done-when scenarios"],
        current_node_id=PHASE_INTENT_DISTILL,
    )
    factory_repo.save_job(job)

    async def _fake_llm(gateway, system, user, fallback, max_tokens=0, timeout=0):
        return fallback

    monkeypatch.setattr(
        "src.application.agent_training_factory.phases.intent_distill.phase_llm_json",
        _fake_llm,
    )
    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None, wiki=None)
    result = await IntentDistillPhase().run(ctx)
    assert result.outcome == "ok"
    assert "answers" in result.artifacts
    answers = result.artifacts["answers"]
    assert isinstance(answers, dict)
    assert "outcome" in answers
    pkts = [p for p in factory_repo.list_packets(job.id) if p.sender_role == "intent_distill"]
    assert pkts
    assert pkts[-1].payload.get("answers")


@pytest.mark.asyncio
async def test_intent_distill_outer_rinse_reasks_only_implicated(factory_repo, monkeypatch):
    job = FactoryJob(
        id="fjob_distill_outer",
        target_agent_id="demo",
        session_id="sess_do",
        status="running",
        seed_intent="CLI role with SOP gaps",
        current_node_id=PHASE_INTENT_DISTILL,
        outer_rinse_count=1,
        failure_class=FAILURE_SOP_HOW,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="eval",
            sender_role="scenario_verify",
            recipient_role="intent_distill",
            node_id=PHASE_SCENARIO_VERIFY,
            payload={
                "passed": False,
                "failure_class": FAILURE_SOP_HOW,
                "critic_notes": "Missing SOP; medium misunderstanding",
                "message": "Scenario Verify FAILED — outer rinse",
                "missing_scenarios": ["Professional SOP covers medium path"],
            },
        )
    )
    captured: Dict[str, Any] = {}

    async def _fake_llm(gateway, system, user, fallback, max_tokens=0, timeout=0):
        captured["user"] = user
        return fallback

    monkeypatch.setattr(
        "src.application.agent_training_factory.phases.intent_distill.phase_llm_json",
        _fake_llm,
    )
    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None)
    result = await IntentDistillPhase().run(ctx)
    assert result.outcome == "ok"
    asked = result.artifacts.get("questions_asked") or []
    assert 1 <= len(asked) < 7
    assert "REFLEXION" in captured.get("user", "") or "lesson" in captured.get("user", "").lower()


# ---------------------------------------------------------------------------
# Scenario Verify
# ---------------------------------------------------------------------------


def _author_with_scenarios(job_id: str, skill_body: str) -> FactoryPacket:
    # Put covering tokens in executable string literals (not comments/docstrings).
    tool_py = (
        "def manage_demo(action='status', dry_run=False, **kwargs):\n"
        f"    coverage = {skill_body!r}\n"
        "    return {'success': True, 'action': action, 'coverage': coverage}\n"
    )
    return FactoryPacket(
        job_id=job_id,
        packet_type="work",
        sender_role="author",
        recipient_role="scenario_verify",
        node_id=PHASE_AUTHOR,
        payload={
            "tool_name": "manage_demo",
            "files_map": {
                "tools/manage_demo.py": tool_py,
                "skills/demo/SKILL.md": skill_body,
            },
            "message": "Author produced manage_demo",
        },
    )


def _blueprint_packet(job_id: str, scenarios: List[str]) -> FactoryPacket:
    return FactoryPacket(
        job_id=job_id,
        packet_type="gap",
        sender_role="blueprint",
        recipient_role="author",
        node_id="blueprint",
        payload={
            "blueprint": {
                "skills": [{"id": "demo", "name": "Demo", "tools": ["manage_demo"]}],
                "tools": [{"name": "manage_demo", "actions": ["status"]}],
                "scenarios": scenarios,
            },
            "message": "Blueprint",
        },
    )


@pytest.mark.asyncio
async def test_scenario_verify_fails_independently_when_scenarios_missing(factory_repo):
    scenarios = [
        "Operator can complete outcome via CLI",
        "Professional SOP documents the medium path",
    ]
    job = FactoryJob(
        id="fjob_scen_fail",
        target_agent_id="demo",
        session_id="sess_sf",
        status="running",
        seed_intent="demo",
        current_node_id=PHASE_SCENARIO_VERIFY,
        max_verify_rinses=3,
        max_outer_rinses=2,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(_blueprint_packet(job.id, scenarios))
    # Skill covers only first scenario keywords
    factory_repo.save_packet(
        _author_with_scenarios(
            job.id,
            "---\nname: Demo\n---\n# Runbook\n\nOperator can complete outcome via CLI.\n",
        )
    )
    ctx = PhaseContext(job=job, repo=factory_repo)
    result = await ScenarioVerifyPhase().run(ctx)
    assert result.outcome in ("fail", "outer")
    assert result.artifacts.get("passed") is False
    missing = result.artifacts.get("missing_scenarios") or []
    assert any("Professional SOP" in m or "medium" in m.lower() for m in missing)


@pytest.mark.asyncio
async def test_scenario_verify_passes_when_all_covered(factory_repo):
    scenarios = [
        "Operator can complete outcome via CLI",
        "Professional SOP documents the medium path",
    ]
    job = FactoryJob(
        id="fjob_scen_ok",
        target_agent_id="demo",
        session_id="sess_so",
        status="running",
        seed_intent="demo",
        current_node_id=PHASE_SCENARIO_VERIFY,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(_blueprint_packet(job.id, scenarios))
    factory_repo.save_packet(
        _author_with_scenarios(
            job.id,
            "---\nname: Demo\n---\n# Runbook\n\n"
            "Operator can complete outcome via CLI.\n"
            "Professional SOP documents the medium path.\n",
        )
    )
    result = await ScenarioVerifyPhase().run(PhaseContext(job=job, repo=factory_repo))
    assert result.outcome == "ok"
    assert result.artifacts.get("passed") is True


@pytest.mark.asyncio
async def test_inner_rinse_does_not_re_ground(factory_repo):
    """Implementation fail from scenario verify rinses to Author, not Ground."""
    scenarios = ["Must cover unique claim alpha-zeta"]
    job = FactoryJob(
        id="fjob_inner",
        target_agent_id="demo",
        session_id="sess_in",
        status="running",
        seed_intent="demo",
        current_node_id=PHASE_SCENARIO_VERIFY,
        verify_rinse_count=0,
        max_verify_rinses=3,
        max_outer_rinses=2,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(_blueprint_packet(job.id, scenarios))
    factory_repo.save_packet(
        _author_with_scenarios(job.id, "---\nname: Demo\n---\n# Runbook\n\nNothing useful.\n")
    )
    # Force implementation class via critic-style miss without SOP keywords:
    # ScenarioVerify classifies coverage gaps as sop_how by default when scenario text
    # looks procedural; for this test we monkeypatch classify to implementation.
    import src.application.agent_training_factory.phases.scenario_verify as sv

    orig = sv.classify_failure

    def _impl(*args, **kwargs):
        return FAILURE_IMPLEMENTATION

    sv.classify_failure = _impl  # type: ignore
    try:
        orch = FactoryOrchestrator(repo=factory_repo, poll_interval=0.01)
        await orch.step_job(job.id)
    finally:
        sv.classify_failure = orig  # type: ignore

    j = factory_repo.get_job(job.id)
    assert j is not None
    assert j.current_node_id == PHASE_AUTHOR
    assert j.verify_rinse_count == 1
    assert j.outer_rinse_count == 0


@pytest.mark.asyncio
async def test_outer_rinse_triggers_intent_distill_and_increments(factory_repo):
    scenarios = ["Professional SOP must document unknown procedure for the medium"]
    job = FactoryJob(
        id="fjob_outer",
        target_agent_id="demo",
        session_id="sess_ou",
        status="running",
        seed_intent="demo",
        current_node_id=PHASE_SCENARIO_VERIFY,
        verify_rinse_count=0,
        max_verify_rinses=3,
        outer_rinse_count=0,
        max_outer_rinses=2,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(_blueprint_packet(job.id, scenarios))
    factory_repo.save_packet(
        _author_with_scenarios(job.id, "---\nname: Demo\n---\n# Runbook\n\nstub\n")
    )
    orch = FactoryOrchestrator(repo=factory_repo, poll_interval=0.01)
    await orch.step_job(job.id)
    j = factory_repo.get_job(job.id)
    assert j is not None
    assert j.current_node_id == PHASE_INTENT_DISTILL
    assert j.outer_rinse_count == 1
    assert j.failure_class == FAILURE_SOP_HOW


@pytest.mark.asyncio
async def test_outer_rinse_cap_terminates(factory_repo):
    scenarios = ["Missing SOP procedure must be grounded"]
    job = FactoryJob(
        id="fjob_outer_cap",
        target_agent_id="demo",
        session_id="sess_oc",
        status="running",
        seed_intent="demo",
        current_node_id=PHASE_SCENARIO_VERIFY,
        outer_rinse_count=1,
        max_outer_rinses=2,
        max_verify_rinses=3,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(_blueprint_packet(job.id, scenarios))
    factory_repo.save_packet(
        _author_with_scenarios(job.id, "---\nname: Demo\n---\n# Runbook\n\nstub\n")
    )
    orch = FactoryOrchestrator(repo=factory_repo, poll_interval=0.01)
    await orch.step_job(job.id)
    j = factory_repo.get_job(job.id)
    assert j is not None
    assert j.status == "failed"
    assert j.outer_rinse_count == 2


class AlwaysFailBattery:
    async def run_battery(self, **kwargs):
        return EvalPacket(
            checks_executed=["stage_2_safety"],
            passed=False,
            stage_1_functional=False,
            stage_2_safety=False,
            stage_3_idempotency=False,
            stage_4_critic=False,
            critic_notes="Safety Guardrail Alert: simulated implementation fail",
            duration_ms=1.0,
        )


@pytest.mark.asyncio
async def test_code_verify_implementation_fail_inner_not_outer(factory_repo):
    job = FactoryJob(
        id="fjob_code_inner",
        target_agent_id="demo",
        session_id="sess_ci",
        status="running",
        seed_intent="demo",
        current_node_id=PHASE_VERIFY,
        verify_rinse_count=0,
        max_verify_rinses=3,
        outer_rinse_count=0,
        max_outer_rinses=2,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="verify",
            node_id=PHASE_AUTHOR,
            payload={
                "tool_name": "manage_demo",
                "files_map": {
                    "tools/manage_demo.py": "def manage_demo(**kwargs):\n    return {'success': True}\n",
                    "skills/demo/SKILL.md": "# Runbook\n",
                },
            },
        )
    )
    orch = FactoryOrchestrator(
        repo=factory_repo, battery_service=AlwaysFailBattery(), poll_interval=0.01
    )
    await orch.step_job(job.id)
    j = factory_repo.get_job(job.id)
    assert j is not None
    assert j.current_node_id == PHASE_AUTHOR
    assert j.verify_rinse_count == 1
    assert j.outer_rinse_count == 0


@pytest.mark.asyncio
async def test_code_verify_sop_notes_trigger_outer(factory_repo):
    class SopFailBattery:
        async def run_battery(self, **kwargs):
            return EvalPacket(
                checks_executed=["stage_4_critic"],
                passed=False,
                stage_1_functional=True,
                stage_2_safety=True,
                stage_3_idempotency=True,
                stage_4_critic=False,
                critic_notes="Critic: missing SOP and medium misunderstanding in skill",
                duration_ms=1.0,
            )

    job = FactoryJob(
        id="fjob_code_outer",
        target_agent_id="demo",
        session_id="sess_co",
        status="running",
        seed_intent="demo",
        current_node_id=PHASE_VERIFY,
        verify_rinse_count=0,
        max_verify_rinses=3,
        outer_rinse_count=0,
        max_outer_rinses=2,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="verify",
            node_id=PHASE_AUTHOR,
            payload={
                "tool_name": "manage_demo",
                "files_map": {
                    "tools/manage_demo.py": "def manage_demo(**kwargs):\n    return {'success': True}\n",
                    "skills/demo/SKILL.md": "# Runbook\n",
                },
            },
        )
    )
    orch = FactoryOrchestrator(
        repo=factory_repo, battery_service=SopFailBattery(), poll_interval=0.01
    )
    await orch.step_job(job.id)
    j = factory_repo.get_job(job.id)
    assert j is not None
    assert j.current_node_id == PHASE_INTENT_DISTILL
    assert j.outer_rinse_count == 1
    assert j.failure_class == FAILURE_SOP_HOW
