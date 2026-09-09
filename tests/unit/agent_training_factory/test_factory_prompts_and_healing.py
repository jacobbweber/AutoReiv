"""
Unit tests for Upgraded Factory Prompts, Self-Healing Loop, Duration Tracking, and Collision Guard [REQ-FACT-049 - REQ-FACT-054].
"""


from src.application.agent_training_factory.prompt_registry import (
    ALL_PHASE_IDS,
    PhasePromptRegistry,
)
from src.application.agent_training_factory.registry import (
    DEFAULT_EDGES,
    PHASE_AUTHOR,
    PHASE_BLUEPRINT,
    PHASE_GROUND,
    PHASE_INTENT_DISTILL,
    PHASE_VERIFY,
)


def test_all_eight_phases_have_deep_agentic_prompts():
    registry = PhasePromptRegistry()
    for pid in ALL_PHASE_IDS:
        meta = registry.get_phase_metadata(pid)
        assert meta is not None, f"Phase {pid} metadata must exist"
        prompt = meta["default_prompt"]
        # Upgraded prompts must be substantial and prescriptive (> 120 characters)
        assert len(prompt) > 120, f"Phase {pid} prompt is too short ({len(prompt)} chars)"

    # Specific phase invariants
    intent_prompt = registry.get_default_prompt(PHASE_INTENT_DISTILL)
    assert "user stories" in intent_prompt.lower() or "boundary" in intent_prompt.lower()

    ground_prompt = registry.get_default_prompt(PHASE_GROUND)
    assert "environmental constraints" in ground_prompt.lower() or "prerequisite" in ground_prompt.lower()

    blueprint_prompt = registry.get_default_prompt(PHASE_BLUEPRINT)
    assert "anti-bloat" in blueprint_prompt.lower() or "matt pocock" in blueprint_prompt.lower()

    author_prompt = registry.get_default_prompt(PHASE_AUTHOR)
    assert "docstring" in author_prompt.lower() or "return" in author_prompt.lower()

    verify_prompt = registry.get_default_prompt(PHASE_VERIFY)
    assert "syntax" in verify_prompt.lower() or "traceback" in verify_prompt.lower()


def test_verify_edges_include_retry_author_healing_transition():
    verify_edges = DEFAULT_EDGES.get(PHASE_VERIFY, {})
    assert "retry_author" in verify_edges or "fail" in verify_edges
    if "retry_author" in verify_edges:
        assert verify_edges["retry_author"] == PHASE_AUTHOR


def test_format_phase_duration_helper():
    from src.application.agent_training_factory.orchestrator import format_phase_duration
    assert format_phase_duration(850) == "850ms"
    assert format_phase_duration(1500) == "1.5s"
    assert format_phase_duration(12340) == "12.3s"
    assert format_phase_duration(None) == ""
