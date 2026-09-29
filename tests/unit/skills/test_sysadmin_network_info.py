from unittest.mock import patch

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.skills.sysadmin_tools import SysadminTools
from tests.unit.agent_skills.catalog import platform_pack_profile


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



def test_autoreiv_profile_has_telemetry_and_developer_has_no_cli_exec():
    autoreiv = platform_pack_profile("autoreiv")
    pinned = ["system_info", "get_recent_errors", "inspect_system_health"]
    assert set(pinned) <= set(list(resolve_allowed_tools(autoreiv)))
    assert "cli_exec" not in list(resolve_allowed_tools(autoreiv))

    developer = platform_pack_profile("developer")
    assert "cli_exec" not in list(resolve_allowed_tools(developer))  # CARD-562: no shell/code runner on Developer
