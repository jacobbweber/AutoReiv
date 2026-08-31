from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.sysadmin_tools import SysadminTools
from src.domain.agents.profiles import AUTOREIV_PROFILE


def test_sysadmin_tool_descriptions_network_and_os_aware():
    registry = ScopedToolRegistry()
    skill = SysadminTools()
    skill.register_tools(registry)

    sysinfo_tool = registry._tools.get("system_info")
    assert sysinfo_tool is not None
    desc = sysinfo_tool.definition.description.lower()
    assert "hostname" in desc or "ip" in desc

    cli_tool = registry._tools.get("cli_exec")
    assert cli_tool is not None
    cli_desc = cli_tool.definition.description.lower()
    assert "windows" in cli_desc
    assert "ipconfig" in cli_desc



def test_autoreiv_system_prompt_os_aware():
    prompt = AUTOREIV_PROFILE.system_prompt.lower()
    assert "windows" in prompt
    assert "ipconfig" in prompt
