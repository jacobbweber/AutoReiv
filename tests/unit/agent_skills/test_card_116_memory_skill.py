"""
Unit tests for CARD-116: Memory fields on AgentProfile, AgentPackManifest,
and database exclusion from pack zip exports.
"""


from src.domain.agents.guardrails import AgentProfileGuardrail
from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization


def test_agent_profile_memory_fields_defaults():
    profile = AgentProfile(
        id="analyst-bot",
        name="Analyst Bot",
        description="Analyzes data",
        system_prompt="You are a data analyst agent.",
    )
    assert hasattr(profile, "memory_enabled")
    assert profile.memory_enabled is True
    assert hasattr(profile, "memory_retention_days")
    assert profile.memory_retention_days == 30
    assert hasattr(profile, "pinned_memory")
    assert profile.pinned_memory == ""


def test_agent_profile_guardrail_validates_memory():
    data = {
        "id": "research-bot",
        "name": "Research Bot",
        "system_prompt": "You conduct deep research.",
        "memory_enabled": True,
        "memory_retention_days": 60,
        "pinned_memory": "Never delete source URLs.",
    }
    profile = AgentProfileGuardrail.validate(data)
    assert profile.memory_enabled is True
    assert profile.memory_retention_days == 60
    assert profile.pinned_memory == "Never delete source URLs."


def test_agent_customization_memory_fields():
    custom = AgentCustomization(
        agent_id="research-bot",
        memory_enabled=False,
        memory_retention_days=14,
        pinned_memory="Always use metric units.",
    )
    assert custom.memory_enabled is False
    assert custom.memory_retention_days == 14
    assert custom.pinned_memory == "Always use metric units."



