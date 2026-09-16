"""Unit tests for CARD-337: Platform Direct Agent [REQ-TEL-001]."""

from src.application.agent_packs.schema import (
    PLATFORM_PACK_IDS,
    is_platform_pack,
    is_visible_in_chat,
)
from tests.unit.agent_packs.catalog import load_platform_manifest


def test_direct_pack_is_platform_pack():
    """[REQ-TEL-001] Direct agent must be registered in PLATFORM_PACK_IDS."""
    assert "direct" in PLATFORM_PACK_IDS
    assert is_platform_pack("direct")


def test_direct_pack_manifest_zero_tools_zero_skills():
    """[REQ-TEL-001] Direct agent manifest must have zero tools, zero skills, and show_in_chat=True."""
    manifest = load_platform_manifest("direct")
    assert manifest.schema_version == "1.1"
    assert manifest.id == "direct"
    assert manifest.name == "Direct"
    assert is_visible_in_chat(manifest) is True

    # Zero tools mounted
    assert manifest.pack_tool_names == []
    # Zero skills mounted
    assert manifest.skills == []
    assert manifest.allowed_skill == []

    # Direct system prompt exists and is concise
    assert manifest.system_prompt is not None
    assert len(manifest.system_prompt) > 0
    assert "direct" in manifest.system_prompt.lower()


def test_direct_agent_resolves_zero_tools():
    """[REQ-TEL-001] Direct agent must resolve zero tools even with platform scoping."""
    from src.application.agent_packs.schema import resolve_scoped_tools
    from src.application.kernel.tool_registry import ScopedToolRegistry
    from src.domain.kernel.models import AgentProfile

    manifest = load_platform_manifest("direct")
    assert resolve_scoped_tools(manifest) == []

    profile = AgentProfile(
        id="direct",
        name="Direct",
        description="A direct agent",
        system_prompt="Direct persona",
    )
    assert resolve_scoped_tools(profile) == []

    reg = ScopedToolRegistry()
    reg.register_tool(
        name="dummy_tool",
        description="test",
        parameters={"type": "object"},
        handler=lambda: None,
    )
    assert reg.get_tools_for_agent(profile) == []
