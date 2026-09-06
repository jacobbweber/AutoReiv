"""Unit tests for Agent Training Factory registry and Wiki front-matter v1 [CARD-171]."""

from src.application.agent_training_factory.registry import (
    DEFAULT_PIPELINE,
    PHASE_AUTHOR,
    PHASE_VERIFY,
    PhaseRegistry,
    default_registry,
)
from src.application.agent_training_factory.wiki_frontmatter import (
    FACTORY_NOTE_TYPE,
    build_factory_frontmatter,
    is_factory_grounding_note,
    validate_factory_frontmatter,
)


def test_default_pipeline_order():
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


def test_default_registry_has_all_phases():
    reg = default_registry()
    for pid in DEFAULT_PIPELINE:
        assert reg.get(pid) is not None
        assert reg.get(pid).id == pid


def test_verify_fail_rinses_to_author():
    reg = PhaseRegistry()
    assert reg.next_phase(PHASE_VERIFY, "fail") == PHASE_AUTHOR
    assert reg.next_phase(PHASE_VERIFY, "ok") == "optimize"


def test_legacy_node_normalization():
    reg = default_registry()
    assert reg.normalize_node("socratic_handshake") == "intent_distill"
    assert reg.normalize_node("discovery_probe") == "ground"
    assert reg.normalize_node("coder_node") == "author"
    assert reg.normalize_node("sandbox_battery_node") == "verify"
    assert reg.normalize_node("hitl_deploy_gate_node") == "promote"


def test_frontmatter_contract_v1_valid():
    meta = build_factory_frontmatter(
        agent_id="hyperv",
        medium="cli",
        factory_job_id="fjob_abc",
        status="grounded",
    )
    assert meta["type"] == FACTORY_NOTE_TYPE
    assert meta["agent_id"] == "hyperv"
    assert meta["medium"] == "cli"
    assert meta["factory_job_id"] == "fjob_abc"
    assert validate_factory_frontmatter(meta) == []
    assert is_factory_grounding_note(meta) is True


def test_frontmatter_contract_v1_missing_keys():
    errs = validate_factory_frontmatter({"type": FACTORY_NOTE_TYPE})
    assert "missing required key: agent_id" in errs
    assert "missing required key: medium" in errs


def test_frontmatter_rejects_wrong_type():
    errs = validate_factory_frontmatter(
        {"type": "note", "agent_id": "x", "medium": "cli"}
    )
    assert any("factory-grounding" in e for e in errs)
