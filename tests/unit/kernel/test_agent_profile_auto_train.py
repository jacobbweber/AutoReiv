"""
Unit tests for Autonomous Training controls on AgentProfile, AgentCustomization, Guardrails, and Pack Manifest [REQ-FACT-023].
"""

import pytest
from pydantic import ValidationError

from src.application.agent_packs.schema import AgentPackManifest
from src.domain.agents.guardrails import AgentProfileGuardrail
from src.domain.kernel.models import AgentProfile, KernelEvent, KernelEventType
from src.domain.settings.models import AgentCustomization


def test_agent_profile_auto_train_defaults():
    profile = AgentProfile(
        id="test-agent",
        name="Test Agent",
        description="Testing auto-train defaults",
        system_prompt="You are a test agent.",
    )
    assert profile.allow_autonomous_training is False
    assert profile.max_training_retries == 2


def test_agent_profile_auto_train_custom_values():
    profile = AgentProfile(
        id="test-agent",
        name="Test Agent",
        description="Testing auto-train values",
        system_prompt="You are a test agent.",
        allow_autonomous_training=True,
        max_training_retries=4,
    )
    assert profile.allow_autonomous_training is True
    assert profile.max_training_retries == 4


def test_agent_profile_auto_train_retries_bounds():
    with pytest.raises(ValidationError):
        AgentProfile(
            id="test-agent",
            name="Test Agent",
            description="Testing bounds",
            system_prompt="You are a test agent.",
            max_training_retries=0,  # Below minimum of 1
        )

    with pytest.raises(ValidationError):
        AgentProfile(
            id="test-agent",
            name="Test Agent",
            description="Testing bounds",
            system_prompt="You are a test agent.",
            max_training_retries=6,  # Above maximum of 5
        )


def test_agent_customization_auto_train_fields():
    custom = AgentCustomization(
        agent_id="test-agent",
        allow_autonomous_training=True,
        max_training_retries=3,
    )
    assert custom.allow_autonomous_training is True
    assert custom.max_training_retries == 3


def test_guardrail_validates_and_normalizes_auto_train():
    payload = {
        "id": "hyperv",
        "name": "Hyper-V Specialist",
        "description": "Virtual machine manager",
        "system_prompt": "You manage Hyper-V virtual machines.",
        "allow_autonomous_training": True,
        "max_training_retries": 3,
    }
    profile = AgentProfileGuardrail.validate(payload)
    assert profile.allow_autonomous_training is True
    assert profile.max_training_retries == 3


def test_guardrail_clamps_or_defaults_invalid_retries():
    payload = {
        "id": "hyperv",
        "name": "Hyper-V Specialist",
        "description": "Virtual machine manager",
        "system_prompt": "You manage Hyper-V virtual machines.",
        "allow_autonomous_training": "yes",
        "max_training_retries": 99,  # Invalid bound -> should fallback to default 2
    }
    profile = AgentProfileGuardrail.validate(payload)
    assert profile.allow_autonomous_training is True
    assert profile.max_training_retries == 2


def test_pack_manifest_auto_train_fields():
    manifest = AgentPackManifest(
        id="hyperv",
        name="Hyper-V Specialist",
        allow_autonomous_training=True,
        max_training_retries=3,
    )
    assert manifest.allow_autonomous_training is True
    assert manifest.max_training_retries == 3


def test_kernel_event_auto_train_progress():
    event = KernelEvent(
        event_type=KernelEventType.AUTO_TRAIN_PROGRESS,
        content="Synthesizing tool in sandbox...",
        auto_train={"stage": "sandbox_battery", "passed": True},
    )
    assert event.event_type == KernelEventType.AUTO_TRAIN_PROGRESS
    assert event.auto_train["stage"] == "sandbox_battery"
