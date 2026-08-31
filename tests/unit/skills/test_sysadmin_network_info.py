from unittest.mock import patch

from src.application.kernel.tool_ranker import ToolRanker
from src.application.skills.sysadmin_tools import SysadminTools
from src.domain.gateway.models import ToolDefinition
from tests.unit.agent_packs.catalog import platform_pack_profile


def test_get_system_info_returns_hostname_and_ip():
    skill = SysadminTools()
    info = skill.get_system_info()

    assert "hostname" in info
    assert isinstance(info["hostname"], str)
    assert len(info["hostname"]) > 0

    assert "primary_ip" in info
    assert isinstance(info["primary_ip"], str)

    assert "ip_addresses" in info
    assert isinstance(info["ip_addresses"], list)
    assert len(info["ip_addresses"]) >= 1



def test_get_system_info_offline_fallback():
    skill = SysadminTools()
    with patch("socket.gethostname", side_effect=OSError("Network unreachable")):
        info = skill.get_system_info()
        assert info["hostname"] == "localhost"
        assert info["primary_ip"] == "127.0.0.1"
        assert info["ip_addresses"] == ["127.0.0.1"]



def test_autoreiv_profile_pins_cli_exec():
    autoreiv = platform_pack_profile("autoreiv")
    pinned = ["system_info", "get_recent_errors", "cli_exec"]
    assert set(pinned) <= set(autoreiv.allowed_tool_names)

    # Verify ToolRanker unconditionally includes cli_exec even for an unrelated query
    tools = [
        ToolDefinition(name="system_info", description="Sys info"),
        ToolDefinition(name="get_recent_errors", description="Errors"),
        ToolDefinition(name="cli_exec", description="Run shell command"),
        ToolDefinition(name="wiki_read", description="Read wiki note"),
        ToolDefinition(name="wiki_search", description="Search wiki note"),
        ToolDefinition(name="wiki_list", description="List wiki notes"),
        ToolDefinition(name="delegate_task", description="Delegate to agent"),
        ToolDefinition(name="handoff_to_agent", description="Handoff to agent"),
    ]

    ranked = ToolRanker.rank_tools(
        query="What is the wiki structure of our repository?",
        tools=tools,
        pinned_tool_names=pinned,
        max_tools=6,
    )

    active_names = [t.name for t in ranked]
    assert "cli_exec" in active_names
    assert "system_info" in active_names
    assert "get_recent_errors" in active_names
