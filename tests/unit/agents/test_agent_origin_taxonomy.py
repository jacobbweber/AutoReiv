
from src.domain.kernel.models import AgentOrigin, AgentProfile


def test_agent_origin_enum_values():
    assert AgentOrigin.FILE.value == "file"
    assert AgentOrigin.SYSTEM.value == "system"
    assert AgentOrigin.PLATFORM.value == "platform"
    assert AgentOrigin.CUSTOM.value == "custom"
    assert AgentOrigin("file") == AgentOrigin.FILE
    assert AgentOrigin("system") == AgentOrigin.SYSTEM
    assert AgentOrigin("platform") == AgentOrigin.PLATFORM
    assert AgentOrigin("custom") == AgentOrigin.CUSTOM


def test_agent_profile_default_origin():
    profile = AgentProfile(
        id="test-agent",
        name="Test Agent",
        description="A test agent",
        system_prompt="Test prompt",
    )
    assert profile.origin == AgentOrigin.FILE
    assert profile.origin.value == "file"


def test_agent_profile_explicit_origin():
    profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Core platform agent",
        system_prompt="Platform prompt",
        origin=AgentOrigin.FILE,
    )
    assert profile.origin == AgentOrigin.FILE
    assert profile.origin.value == "file"




