"""CARD-431 operator contract: save_agent_specification leaves the catalog.

REQ-431-001: Tools Studio catalog (GET /api/tools_studio/capabilities)
does not list save_agent_specification after boot.
REQ-431-002: (CARD-569) the pack tools are gone too; agents are made in Agent Studio.
REQ-431-003: a fresh boot database has no pending_approvals row for that tool.
Unregister is allowed only when that set is empty.
REQ-431-004: agent-builder is not a live agent.

Temp user-data only [ADR-0055].
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from src.application.agent_packs.allowed_tools import resolve_allowed_tools
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.safety.tool_policy_gate import _DEFAULT_REQUIRE_CONFIRM
from src.domain.gateway.models import ToolCall


def _refuse_live(user_data: Path) -> None:
    local_app = os.environ.get("LOCALAPPDATA") or ""
    if not local_app:
        return
    live_root = (Path(local_app) / "AutoReiv").resolve()
    ud = str(user_data.resolve()).replace("\\", "/").lower()
    live = str(live_root).replace("\\", "/").lower()
    assert ud != live and not ud.startswith(live + "/"), f"operator contracts must not use live user-data: {user_data}"


def _catalog_names(payload: dict) -> set[str]:
    names: set[str] = set()
    for namespace in payload.get("namespaces") or []:
        for tool in namespace.get("tools") or []:
            name = str(tool.get("name") or "").strip()
            if name:
                names.add(name)
    return names


def test_oc431_catalog_omits_save_and_pack_tools(operator_client):
    """CARD-569: save_agent_specification and the pack tools are gone; agents are made in Agent Studio."""
    client, store, wiki = operator_client
    _refuse_live(wiki.parent)

    caps = client.get("/api/tools_studio/capabilities")
    assert caps.status_code == 200
    names = _catalog_names(caps.json())
    for gone in (
        "save_agent_specification",
        "scaffold_agent_pack",
        "export_agent_pack",
        "import_agent_pack",
        "inspect_agent_pack",
        "propose_agent_specification",
    ):
        assert gone not in names, gone

    tools = client.app.state.tool_registry
    assert tools.get_tool_definition("save_agent_specification") is None
    assert tools.get_tool_definition("scaffold_agent_pack") is None
    assert tools.get_tool_definition("inspect_agent") is not None

    registry = client.app.state.registry
    assert registry.get_agent("agent-builder") is None
    listed = client.get("/api/agents")
    assert listed.status_code == 200
    assert "agent-builder" not in {row["id"] for row in listed.json()}

    developer = registry.get_agent("developer")
    assert developer is not None
    assert "save_agent_specification" not in list(resolve_allowed_tools(developer))
    assert "save_agent_specification" not in _DEFAULT_REQUIRE_CONFIRM
    hitl = client.app.state.kernel.hitl_engine
    assert isinstance(hitl, HITLApprovalEngine)
    assert "save_agent_specification" not in hitl.high_risk_tools

    pending = store.get_pending_approvals()
    assert [row for row in pending if row.get("tool_name") == "save_agent_specification"] == []

    missing = asyncio.run(
        tools.execute(
            ToolCall(id="oc431-save", name="save_agent_specification", arguments={"spec": {"id": "should-not-exist"}}),
            developer,
        )
    )
    assert missing.success is False
    assert registry.get_agent("should-not-exist") is None
