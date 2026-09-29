"""
Unit tests for Per-Agent Remote MCP Server Configuration and Pack Schema [CARD-183].
[REQ-MCP-AGENT-001]
"""


from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization, MCPServerConfig


def test_agent_profile_mcp_servers_field():
    profile = AgentProfile(
        id="hyperv",
        name="Hyper-V Specialist",
        description="Manages Hyper-V virtual infrastructure",
        system_prompt="You manage Hyper-V virtual machines.",
        mcp_servers=[
            MCPServerConfig(
                name="hyperv-remote",
                transport="sse",
                url="http://192.168.1.100:8080/sse",
                headers={"Authorization": "Bearer secret-token"},
                enabled=True,
            )
        ],
    )
    assert len(profile.mcp_servers) == 1
    server = profile.mcp_servers[0]
    assert server.name == "hyperv-remote"
    assert server.transport == "sse"
    assert server.url == "http://192.168.1.100:8080/sse"
    assert server.headers == {"Authorization": "Bearer secret-token"}
    assert server.enabled is True

    # Roundtrip serialization
    dumped = profile.model_dump()
    assert "mcp_servers" in dumped
    assert dumped["mcp_servers"][0]["name"] == "hyperv-remote"
    assert dumped["mcp_servers"][0]["transport"] == "sse"

    restored = AgentProfile.model_validate(dumped)
    assert len(restored.mcp_servers) == 1
    assert restored.mcp_servers[0].url == "http://192.168.1.100:8080/sse"




def test_agent_customization_supports_mcp_servers():
    custom = AgentCustomization(
        agent_id="hyperv",
        mcp_servers=[
            MCPServerConfig(
                name="remote-docker",
                transport="sse",
                url="http://127.0.0.1:9090/sse",
            )
        ],
    )
    assert custom.mcp_servers is not None
    assert len(custom.mcp_servers) == 1
    assert custom.mcp_servers[0].name == "remote-docker"
