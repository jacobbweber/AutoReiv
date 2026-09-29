"""Unit tests for Developer Agent capability consolidation [CARD-181, CARD-366, REQ-CONSOL-001]."""

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.agent_skills.schema import CHAT_HIDDEN_BY_ID, is_visible_in_chat
from tests.unit.agent_skills.catalog import platform_pack_profile


def test_autoreiv_pack_profile_delegates_developer_capabilities():
    """AutoReiv profile delegates shell/coding to developer via handoff_to_agent."""
    profile = platform_pack_profile("autoreiv")
    assert profile.id == "autoreiv"
    assert profile.show_in_chat is True
    assert "cli_exec" not in list(resolve_allowed_tools(profile))
    assert "sdlc-engineering" not in profile.allowed_skill
    assert "handoff_to_agent" in list(resolve_allowed_tools(profile))



def test_legacy_sdlc_trio_hidden_from_chat():
    for legacy_id in ("conductor", "coding", "review"):
        assert legacy_id in CHAT_HIDDEN_BY_ID
        assert is_visible_in_chat({"id": legacy_id, "show_in_chat": True}) is False
