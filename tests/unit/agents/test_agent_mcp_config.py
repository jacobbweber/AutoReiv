"""
Unit tests for Per-Agent Remote MCP Server Configuration and Pack Schema [CARD-183].
[REQ-MCP-AGENT-001]
"""

import json
from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import MCPServerConfig, AgentCustomization
from src.application.agent_packs.schema import AgentPackManifest, PackMCPServerConfig


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


def test_agent_pack_manifest_mcp_servers_field():
    manifest = AgentPackManifest(
        id="hyperv",
        name="Hyper-V Specialist",
        description="Remote Hyper-V agent",
        mcp_servers=[
            PackMCPServerConfig(
                name="hyperv-mcp",
                transport="sse",
                url="http://localhost:8080/sse",
                headers={"X-Auth": "hyperv-key"},
                enabled=True,
            )
        ],
    )
    assert len(manifest.mcp_servers) == 1
    s = manifest.mcp_servers[0]
    assert s.name == "hyperv-mcp"
    assert s.transport == "sse"
    assert s.url == "http://localhost:8080/sse"
    assert s.headers == {"X-Auth": "hyperv-key"}

    # JSON serialization
    json_str = manifest.model_dump_json()
    parsed = json.loads(json_str)
    assert "mcp_servers" in parsed
    assert parsed["mcp_servers"][0]["transport"] == "sse"

    loaded = AgentPackManifest.model_validate_json(json_str)
    assert len(loaded.mcp_servers) == 1
    assert loaded.mcp_servers[0].name == "hyperv-mcp"


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
