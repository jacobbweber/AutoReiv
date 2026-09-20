"""Unit tests for CARD-383: Canonical agent resolution & de-duplication."""

from pathlib import Path

from src.application.orchestration.job_phase_orchestrator import (
    resolve_specialist_agent_for_capabilities,
)
from src.domain.agents.profiles import (
    DEFAULT_PLATFORM_AGENT_ID,
    LEGACY_AGENT_ALIASES,
    canonical_agent_id,
)
from src.web.routers.education import GradePayload, UpsertItemPayload


def test_default_platform_agent_id_is_autoreiv():
    """Verify DEFAULT_PLATFORM_AGENT_ID is canonical 'autoreiv'."""
    assert DEFAULT_PLATFORM_AGENT_ID == "autoreiv"


def test_canonical_agent_id_maps_all_legacy_aliases():
    """Verify canonical_agent_id maps legacy aliases to autoreiv."""
    expected_aliases = [
        "assistant",
        "wiki",
        "general-assistant",
        "general",
        "librarian",
        "system-librarian",
        "system-agent",
        "system",
        "linux-sysadmin",
        "sysadmin",
        "auditor-critic",
        "forge",
    ]
    for alias in expected_aliases:
        assert canonical_agent_id(alias) == "autoreiv", f"Alias {alias} should resolve to autoreiv"
        assert alias in LEGACY_AGENT_ALIASES

    # CARD-388: developer and tutor are first-class platform agents, not aliases
    assert canonical_agent_id("developer") == "developer"
    assert canonical_agent_id("tutor") == "tutor"
    assert "developer" not in LEGACY_AGENT_ALIASES
    assert "tutor" not in LEGACY_AGENT_ALIASES

    # Preserves catalog/specialist and unknown custom agents
    assert canonical_agent_id("coding") == "coding"
    assert canonical_agent_id("conductor") == "conductor"
    assert canonical_agent_id("review") == "review"
    assert canonical_agent_id("hyperv") == "hyperv"
    assert canonical_agent_id("custom_agent_99") == "custom_agent_99"
    assert canonical_agent_id("homelab") == "homelab"


def test_negative_assertion_handoff_engine_has_no_local_alias_map():
    """Negative assertion: handoff_engine.py must not declare a duplicate alias_map."""
    source_file = Path("src/application/orchestration/handoff_engine.py").read_text(encoding="utf-8")
    assert "alias_map = {" not in source_file, "Local alias_map in handoff_engine.py must be pruned!"
    assert "canonical_agent_id(" in source_file


def test_negative_assertion_supervisor_orchestrator_has_no_local_alias_map():
    """Negative assertion: supervisor_orchestrator.py must not declare a duplicate alias_map."""
    source_file = Path("src/application/kernel/supervisor_orchestrator.py").read_text(encoding="utf-8")
    assert "alias_map = {" not in source_file, "Local alias_map in supervisor_orchestrator.py must be pruned!"
    assert "canonical_agent_id(" in source_file


def test_negative_assertion_orchestrator_has_no_hardcoded_legacy_tuples():
    """Negative assertion: job_phase_orchestrator.py must not hardcode legacy tuple checks."""
    source_file = Path("src/application/orchestration/job_phase_orchestrator.py").read_text(encoding="utf-8")
    assert '("assistant", "wiki", "developer", "coding")' not in source_file
    assert 'in ("assistant", "wiki")' not in source_file
    assert "canonical_agent_id(" in source_file


def test_specialist_agent_resolution_uses_canonical_agent():
    """Verify resolve_specialist_agent_for_capabilities maps legacy inputs to canonical autoreiv."""
    assert resolve_specialist_agent_for_capabilities([], "assistant") == "autoreiv"
    assert resolve_specialist_agent_for_capabilities([], "wiki") == "autoreiv"
    assert resolve_specialist_agent_for_capabilities([], "developer") == "developer"
    assert resolve_specialist_agent_for_capabilities([], "tutor") == "tutor"
    assert resolve_specialist_agent_for_capabilities([], "custom_bot") == "custom_bot"

    # Capability matching
    assert resolve_specialist_agent_for_capabilities(["agent.assistant"], "autoreiv") == "autoreiv"
    assert resolve_specialist_agent_for_capabilities(["agent.custom_specialist"], "autoreiv") == "custom_specialist"
    assert resolve_specialist_agent_for_capabilities(["tool.tutor_flashcard"], "autoreiv") == "autoreiv"


def test_education_router_payloads_default_to_canonical_autoreiv():
    """Verify education models default to autoreiv rather than legacy tutor."""
    grade = GradePayload(item_id="test-1")
    assert grade.agent_id == "autoreiv"

    upsert = UpsertItemPayload(topic="math", wiki_path="math.md", prompt="2+2?", expected_answer="4")
    assert upsert.agent_id == "autoreiv"
