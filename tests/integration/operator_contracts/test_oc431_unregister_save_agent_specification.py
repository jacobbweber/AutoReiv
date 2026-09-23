"""CARD-431 operator contract: save_agent_specification leaves the catalog.

REQ-431-001: Tools Studio catalog (GET /api/agent_training_factory/capabilities)
does not list save_agent_specification after boot.
REQ-431-002: scaffold_agent_pack stays registered and Developer can call it
when the turn asks to scaffold an agent pack.
REQ-431-003: a fresh boot database has no pending_approvals row for that tool.
Unregister is allowed only when that set is empty.
REQ-431-004: agent-builder is not a live agent.

Temp user-data only [ADR-0055].
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

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


def test_oc431_catalog_omits_save_and_developer_can_scaffold(operator_client):
    client, store, wiki = operator_client
    user_data = wiki.parent
    _refuse_live(user_data)

    caps = client.get("/api/agent_training_factory/capabilities")
    assert caps.status_code == 200
    names = _catalog_names(caps.json())
    assert "save_agent_specification" not in names
    assert "scaffold_agent_pack" in names
    assert "propose_skill" in names
    assert "propose_tool" in names
    assert "propose_agent_specification" in names

    tools = client.app.state.tool_registry
    assert tools.get_tool_definition("save_agent_specification") is None
    assert tools.get_tool_definition("scaffold_agent_pack") is not None

    registry = client.app.state.registry
    assert registry.get_agent("agent-builder") is None
    listed = client.get("/api/agents")
    assert listed.status_code == 200
    assert "agent-builder" not in {row["id"] for row in listed.json()}

    developer = registry.get_agent("developer")
    assert developer is not None
    assert "scaffold_agent_pack" in (developer.allowed_tool_names or [])
    assert "save_agent_specification" not in (developer.allowed_tool_names or [])

    visible = client.app.state.kernel._resolve_active_tools(
        developer,
        "scaffold an agent pack named notes-clerk",
    )
    visible_names = {tool.name for tool in visible}
    assert "scaffold_agent_pack" in visible_names
    assert "save_agent_specification" not in visible_names

    assert "save_agent_specification" not in _DEFAULT_REQUIRE_CONFIRM
    hitl = client.app.state.kernel.hitl_engine
    assert isinstance(hitl, HITLApprovalEngine)
    assert "save_agent_specification" not in hitl.high_risk_tools

    pending = store.get_pending_approvals()
    assert [row for row in pending if row.get("tool_name") == "save_agent_specification"] == []

    spec = {
        "id": "notes-clerk",
        "name": "Notes Clerk",
        "description": "Writes a short pack for CARD-431.",
        "system_prompt": "You keep short notes.",
        "tone": "concise",
        "purpose": "general",
        "show_in_chat": True,
        "skills": [
            {
                "id": "notes-runbook",
                "name": "Notes Runbook",
                "description": "How this specialist writes notes.",
                "body": "# Notes\n\nWrite the note. Stop when it is saved.\n",
            }
        ],
    }
    built = asyncio.run(
        tools.execute(
            ToolCall(id="oc431-scaffold", name="scaffold_agent_pack", arguments={"spec": spec}),
            developer,
        )
    )
    assert built.success is True
    assert built.output["success"] is True
    assert built.output["agent_id"] == "notes-clerk"
    pack_skill = user_data / "packs" / "notes-clerk" / "skills" / "notes-runbook" / "SKILL.md"
    assert pack_skill.is_file()
    assert "Write the note" in pack_skill.read_text(encoding="utf-8")
    assert registry.get_agent("notes-clerk") is not None
    assert registry.get_agent("agent-builder") is None

    missing = asyncio.run(
        tools.execute(
            ToolCall(
                id="oc431-save",
                name="save_agent_specification",
                arguments={"spec": {"id": "should-not-exist"}},
            ),
            developer,
        )
    )
    assert missing.success is False
    assert registry.get_agent("should-not-exist") is None
