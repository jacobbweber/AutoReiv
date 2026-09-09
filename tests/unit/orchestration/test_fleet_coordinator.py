"""
Tests for Fleet Coordination Protocol & Homelab Scoped Lookup [CARD-198, REQ-FLEET-006, REQ-FLEET-007].
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.application.orchestration.fleet_coordinator import (
    FleetCoordinator,
    lookup_homelab_docs,
)


def test_lookup_homelab_docs_category_and_query():
    """lookup_homelab_docs finds network documents and returns structured content with frontmatter."""
    # Lookup network vlan matrix
    result = lookup_homelab_docs(category="network", query="VLAN")
    assert result["status"] == "success"
    assert len(result["documents"]) >= 1
    doc = next((d for d in result["documents"] if "vlan_matrix" in d["path"]), None)
    assert doc is not None
    assert doc["metadata"]["doc_type"] == "vlan_matrix"
    assert "10.10.10.0/24" in doc["content"]

    # Lookup compute host spec
    host_result = lookup_homelab_docs(category="compute", query="EPYC")
    assert host_result["status"] == "success"
    assert len(host_result["documents"]) >= 1
    assert any("p-hl01-hvh01" in d["content"] for d in host_result["documents"])

    # Lookup templates
    tmpl_result = lookup_homelab_docs(category="templates")
    assert tmpl_result["status"] == "success"
    assert len(tmpl_result["documents"]) >= 1


@pytest.mark.asyncio
async def test_fleet_coordinator_delegates_to_specialist():
    """FleetCoordinator resolves specialist role and delegates task with injected notes context."""
    coordinator = FleetCoordinator()

    # Mock handoff_to_agent
    mock_output = {
        "status": "success",
        "output": "VLAN 60 planned successfully.",
    }
    with patch.object(coordinator, "_execute_handoff", new=AsyncMock(return_value=mock_output)) as mock_handoff:
        res = await coordinator.delegate_to_fleet_agent(
            specialist_role="architect",
            task_directive="Plan VLAN 60 for IoT subnet.",
            wiki_context_paths=["10-network/vlan_matrix.md"],
        )
        assert res["status"] == "success"
        assert res["target_agent_id"] == "homelab-architect"
        assert mock_handoff.called
        call_kwargs = mock_handoff.call_args[1]
        assert call_kwargs["target_agent_id"] == "homelab-architect"
        assert "Plan VLAN 60 for IoT subnet." in call_kwargs["task_directive"]
        # Injected notes context should be in input_payload or directive
        assert "vlan_matrix" in str(call_kwargs.get("input_payload") or call_kwargs.get("task_directive"))


@pytest.mark.asyncio
async def test_fleet_coordinator_rejects_unknown_specialist():
    """FleetCoordinator rejects invalid or non-fleet specialists."""
    coordinator = FleetCoordinator()
    res = await coordinator.delegate_to_fleet_agent(
        specialist_role="non-existent-role",
        task_directive="Do something invalid.",
    )
    assert res["status"] == "error"
    assert "Unknown specialist role" in res["error"]
