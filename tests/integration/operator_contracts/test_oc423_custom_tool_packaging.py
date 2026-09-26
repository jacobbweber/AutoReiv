"""CARD-423 operator contract: native and MCP custom tool lanes.

REQ-423-001..005. Temp user-data only [ADR-0055].
The Tools Studio form still does not write a tool. Native tools persist in
settings and run through ToolPolicyGate plus the sandbox. MCP tools stay on
the existing attach API and are labeled by server.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.domain.gateway.models import ToolDefinition
from src.infrastructure.mcp.client_adapter import MCPClientAdapter

ECHO_CODE = "def run(**kwargs):\n    return {'marker': 'RAN', 'token': kwargs.get('token')}\n"
RISKY_CODE = "def run(**kwargs):\n    return {'marker': 'RISKY_RAN'}\n"
ROOT = Path(__file__).resolve().parents[3]


def _namespaces(client):
    response = client.get("/api/agent_training_factory/capabilities")
    assert response.status_code == 200, response.text
    return response.json()["namespaces"]


def test_oc423_native_lane_runs_without_mcp_and_hitl_parks(operator_client):
    """REQ-423-001, REQ-423-003, REQ-423-005."""
    client, store, wiki = operator_client
    app = client.app
    before_mcp = store.get_setting("mcp_servers")

    scripts = wiki.parent / "script-drop"
    scripts.mkdir()
    (scripts / "alpha.py").write_text("print('alpha')\n", encoding="utf-8")
    (scripts / "beta.sh").write_text("echo beta\n", encoding="utf-8")
    (scripts / "notes.md").write_text("not a script\n", encoding="utf-8")

    talk = client.post(
        "/api/tools_studio/authoring/talk",
        json={
            "intent": "create",
            "draft": {
                "tool_name": "echo_token",
                "behavior": "Echo a token.",
                "path_context": str(scripts),
                "packaging_preference": "native",
            },
        },
    )
    assert talk.status_code == 200, talk.text
    assert talk.json()["packaging_applied"] is False
    assert talk.json()["persisted_tool"] is False
    assert client.get("/api/tools/native").json()["tools"] == []

    plan = client.post("/api/tools/native/plan", json={"directory": str(scripts)})
    assert plan.status_code == 200, plan.text
    planned = plan.json()
    assert planned["registered"] is False
    assert planned["folder_picker"] is False
    assert planned["mcp_required"] is False
    assert sorted(item["suggested_tool_name"] for item in planned["entries"]) == ["alpha", "beta"]
    assert client.get("/api/tools/native").json()["tools"] == []

    missing_run = client.post(
        "/api/tools/native",
        json={
            "name": "echo_token",
            "description": "Echo a token.",
            "code": "token = 'no function'\n",
            "requires_hitl": False,
        },
    )
    assert missing_run.status_code == 400, missing_run.text

    prefixed = client.post(
        "/api/tools/native",
        json={
            "name": "mcp_secret",
            "description": "Should stay on the MCP lane.",
            "code": ECHO_CODE,
            "requires_hitl": False,
        },
    )
    assert prefixed.status_code == 400, prefixed.text
    assert "mcp_" in prefixed.json()["detail"]["message"]

    clash = client.post(
        "/api/tools/native",
        json={
            "name": "activate_skill",
            "description": "Must not replace a platform tool.",
            "code": ECHO_CODE,
            "requires_hitl": False,
        },
    )
    assert clash.status_code == 409, clash.text

    created = client.post(
        "/api/tools/native",
        json={
            "name": "echo_token",
            "description": "Echo a token.",
            "code": ECHO_CODE,
            "requires_hitl": False,
            "risk_level": "low",
            "grant_agent_ids": ["developer"],
            "parameters": {
                "type": "object",
                "properties": {"token": {"type": "string"}},
            },
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["packaging"] == "native"
    assert body["mcp_required"] is False
    assert body["persisted"] is True
    assert body["mounted"] is True
    assert body["origin_label"] == "Native custom"
    assert body["granted_agent_ids"] == ["developer"]
    assert store.get_setting("mcp_servers") == before_mcp

    listed = client.get("/api/tools/native")
    assert listed.status_code == 200, listed.text
    rows = listed.json()["tools"]
    assert [row["name"] for row in rows] == ["echo_token"]
    assert rows[0]["has_code"] is True
    stored = store.get_setting("native_custom_tools")
    assert stored[0]["code"] == ECHO_CODE
    assert "echo_token" not in (store.get_setting("tool_policy") or {}).get("require_confirm_tools", [])

    denied = client.post(
        "/api/tools/native/echo_token/invoke",
        json={"agent_id": "autoreiv", "arguments": {"token": "nope"}, "approval_mode": "ask"},
    )
    assert denied.status_code == 200, denied.text
    denied_body = denied.json()
    assert denied_body["ran"] is False
    assert denied_body["success"] is False
    assert "RAN" not in json.dumps(denied_body.get("output"))
    assert "not in agent allowlist" in str(denied_body.get("error") or "")

    called = client.post(
        "/api/tools/native/echo_token/invoke",
        json={"agent_id": "developer", "arguments": {"token": "desk"}, "approval_mode": "ask"},
    )
    assert called.status_code == 200, called.text
    called_body = called.json()
    assert called_body["mcp_required"] is False
    assert called_body["ran"] is True
    assert called_body["success"] is True
    assert called_body["output"] == {"marker": "RAN", "token": "desk"}

    app.state.tool_registry.unmount_tool("echo_token")
    assert "echo_token" not in app.state.tool_registry
    remounted = app.state.native_custom_tools.mount_persisted()
    assert "echo_token" in remounted
    again = client.post(
        "/api/tools/native/echo_token/invoke",
        json={"agent_id": "developer", "arguments": {"token": "again"}, "approval_mode": "ask"},
    )
    assert again.status_code == 200, again.text
    assert again.json()["output"]["token"] == "again"

    namespaces = _namespaces(client)
    native_ns = next(item for item in namespaces if item["source"] == "native_custom")
    assert native_ns["origin_label"] == "Native custom"
    assert any(tool["name"] == "echo_token" and tool["origin"] == "native_custom" for tool in native_ns["tools"])
    platform_ns = [item for item in namespaces if item["source"] in {"builtin", "platform", "dynamic"}]
    assert platform_ns
    assert all(item["origin_label"] == "Platform" for item in platform_ns)

    developer = app.state.registry.get_agent("developer")
    visible = app.state.kernel._resolve_active_tools(developer, "please run echo_token now")
    assert "echo_token" in [tool.name for tool in visible]

    risky = client.post(
        "/api/tools/native",
        json={
            "name": "risky_note",
            "description": "A native tool that must park.",
            "code": RISKY_CODE,
            "grant_agent_ids": ["developer"],
        },
    )
    assert risky.status_code == 200, risky.text
    assert risky.json()["requires_hitl"] is True
    assert "risky_note" in store.get_setting("tool_policy")["require_confirm_tools"]

    parked = client.post(
        "/api/tools/native/risky_note/invoke",
        json={"agent_id": "developer", "arguments": {}, "approval_mode": "ask"},
    )
    assert parked.status_code == 200, parked.text
    parked_body = parked.json()
    assert parked_body["parked"] is True
    assert parked_body["ran"] is False
    assert "RISKY_RAN" not in json.dumps(parked_body)
    assert parked_body["approval_id"]
    pending = store.get_pending_approvals(session_id=parked_body["session_id"])
    assert any(row["tool_name"] == "risky_note" for row in pending)

    confirmed = client.post(
        "/api/tools/native/risky_note/invoke",
        json={"agent_id": "developer", "arguments": {}, "approval_mode": "run"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["ran"] is True
    assert confirmed.json()["output"]["marker"] == "RISKY_RAN"

    forced = client.post(
        "/api/tools/native",
        json={
            "name": "high_note",
            "description": "High risk cannot opt out of HITL.",
            "code": ECHO_CODE,
            "requires_hitl": False,
            "risk_level": "high",
        },
    )
    assert forced.status_code == 200, forced.text
    assert forced.json()["requires_hitl"] is True

    removed = client.delete("/api/tools/native/echo_token")
    assert removed.status_code == 200, removed.text
    assert "echo_token" not in app.state.tool_registry
    assert all(row["name"] != "echo_token" for row in client.get("/api/tools/native").json()["tools"])
    gone = client.post(
        "/api/tools/native/echo_token/invoke",
        json={"agent_id": "developer", "arguments": {}, "approval_mode": "run"},
    )
    assert gone.status_code == 404, gone.text


def test_oc423_mcp_lane_groups_under_the_attached_server(operator_client):
    """REQ-423-002, REQ-423-005. Attach stays on the existing MCP save API."""
    client, store, _wiki = operator_client

    async def _list_tools(self):
        return [
            ToolDefinition(
                name="mcp_desk_ping",
                description="Ping the desk server",
                parameters={"type": "object", "properties": {}},
            )
        ]

    with patch.object(MCPClientAdapter, "list_tools", _list_tools):
        saved = client.post(
            "/api/settings/mcp",
            json={
                "name": "desk",
                "transport": "stdio",
                "command": ["python", "-c", "pass"],
                "enabled": True,
            },
        )
    assert saved.status_code == 200, saved.text
    assert saved.json()["mounted"] is True
    assert "mcp_desk_ping" in saved.json()["tools"]

    listed = client.get("/api/settings/mcp")
    assert listed.status_code == 200, listed.text
    desk = next(server for server in listed.json() if server["name"] == "desk")
    assert desk["is_mounted"] is True
    assert "mcp_desk_ping" in desk["tools"]

    namespaces = _namespaces(client)
    mcp_ns = next(item for item in namespaces if item["id"] == "mcp:desk")
    assert mcp_ns["source"] == "mcp"
    assert mcp_ns["server_name"] == "desk"
    assert mcp_ns["origin_label"] == "MCP · desk"
    assert any(tool["name"] == "mcp_desk_ping" and tool["origin"] == "mcp" for tool in mcp_ns["tools"])
    assert store.get_setting("native_custom_tools") in (None, [])


def test_oc423_developer_skills_describe_both_lanes(operator_client):
    """REQ-423-004. Skills live on the developer pack, not under .agents/."""
    client, _store, _wiki = operator_client
    native_skill = (ROOT / "platform-packs/developer/skills/native-tool-engineering/SKILL.md").read_text(encoding="utf-8")
    mcp_skill = (ROOT / "platform-packs/developer/skills/mcp-engineering/SKILL.md").read_text(encoding="utf-8")
    assert "register_native_tool" in native_skill
    assert "plan_native_folder" in native_skill
    assert "ToolPolicyGate" in native_skill
    assert "folder picker" in native_skill.lower()
    assert "no MCP server" in native_skill
    assert "native-tool-engineering" in mcp_skill
    assert "one tool per entry" in mcp_skill or "one tool per script" in mcp_skill
    assert "Settings" in mcp_skill
    assert not (ROOT / ".agents/skills/native-tool-engineering").exists()

    developer = client.app.state.registry.get_agent("developer")
    assert developer is not None
    assert "native-tool-engineering" in (developer.allowed_skill or [])
    assert "register_native_tool" in client.app.state.tool_registry
    assert "plan_native_folder" in client.app.state.tool_registry
    assert "register_native_tool" in (developer.pack_tool_names or []) or "register_native_tool" in (
        developer.allowed_tool_names or []
    )


def test_oc511_route_refuses_broken_native_tools_and_lists_checks(operator_client):
    """CARD-511 tests 23-24: 422 with the failed stage; nothing listed; old rows show check null."""
    client, store, _wiki = operator_client
    broken = {
        "c511_syntax_err": ("def run(**kw):\n    return (\n", "static", "SyntaxError"),
        "c511_import_err": ("import nonexistent_c511_mod\n\ndef run(**kw):\n    return 1\n", "import", "ModuleNotFoundError"),
        "c511_raises": ("def run(**kw):\n    raise ValueError('c511 deliberate failure')\n", "sample_call", "ValueError"),
    }
    for name, (code, stage, needle) in broken.items():
        res = client.post(
            "/api/tools/native",
            json={"name": name, "description": name, "code": code, "requires_hitl": False, "risk_level": "low"},
        )
        assert res.status_code == 422, res.text
        detail = res.json()["detail"]
        assert detail["message"].startswith(f"Not registered: {name} failed the {stage.replace('_', ' ')} check")
        assert detail["check"]["stage"] == stage
        assert needle in detail["check"]["error"]
    assert client.get("/api/tools/native").json()["tools"] == []
    assert store.get_setting("native_custom_tools") in (None, [])

    good = client.post(
        "/api/tools/native",
        json={
            "name": "c511_good",
            "description": "echo",
            "code": ECHO_CODE,
            "requires_hitl": False,
            "risk_level": "low",
            "sample_arguments": {"token": "probe"},
        },
    )
    assert good.status_code == 200, good.text
    assert good.json()["check"]["status"] == "passed"
    assert good.json()["check"]["sample_arguments"] == {"token": "probe"}

    rows = store.get_setting("native_custom_tools")
    rows.append({"name": "c511_old", "description": "old", "code": ECHO_CODE, "parameters": {}, "requires_hitl": False, "risk_level": "low"})
    store.set_setting("native_custom_tools", rows)
    listed = {row["name"]: row for row in client.get("/api/tools/native").json()["tools"]}
    assert listed["c511_good"]["check"]["status"] == "passed"
    assert listed["c511_old"]["check"] is None
