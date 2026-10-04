"""CARD-527: built-in tools never get an Ask Developer card; the two named tools stay under 8 KB."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.routines.telemetry_friction_auditor import run_telemetry_friction_audit
from src.domain.gateway.models import ChatMessage, Role, ToolDefinition
from src.domain.observability.models import CODE_CHANGE, TOOL_ESCALATION, FrictionIncident, FrictionSignatureType
from src.domain.observability.tool_skill_resolver import ToolSkillResolver
from src.domain.orchestration.models import Proposal, ProposalKind, ProposalStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


async def _noop(**_):
    return "ok"


def _registry() -> ScopedToolRegistry:
    reg = ScopedToolRegistry()
    reg.register_tool("c527_builtin_dump", "built-in", {"type": "object", "properties": {}}, _noop)
    reg.register_tool("get_recent_errors", "built-in", {"type": "object", "properties": {}}, _noop)
    reg.register_tool(
        "c527_runtime_dump", "runtime", {"type": "object", "properties": {}}, _noop, origin="native_custom"
    )
    reg.mount_mcp_tool(ToolDefinition(name="mcp_srv_dump", description="mcp", parameters={}), _noop)
    return reg


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    for sid, tools in (("alpha-skill", ["shared_tool"]), ("beta-skill", ["shared_tool"])):
        (d / "skills" / sid).mkdir(parents=True)
        (d / "skills" / sid / "SKILL.md").write_text(
            "---\nname: " + sid + "\ntools:\n" + "".join(f"  - {t}\n" for t in tools) + "---\n# " + sid + "\n",
            encoding="utf-8",
        )
    return d


@pytest.fixture
def store(tmp_path: Path) -> SQLiteStateStore:
    s = SQLiteStateStore(db_path=str(tmp_path / "t.db"))
    s.initialize_db()
    return s


def _incident(tool: str, agent: str = "autoreiv") -> FrictionIncident:
    return FrictionIncident(
        id="fric_c527",
        session_id="sess_c527",
        agent_id=agent,
        tool_name=tool,
        signature=FrictionSignatureType.PAYLOAD_BLOAT,
        evidence="big",
        payload_bytes=20146,
        severity="high",
    )


def test_registry_builtin_names_exclude_runtime_and_mcp_tools():
    assert _registry().builtin_tool_names() == {"c527_builtin_dump", "get_recent_errors"}
    assert _registry().get_tool_origin("mcp_srv_dump") == "mcp"


def test_builtin_tool_gets_a_code_change_card_not_ask_developer(data_dir):
    r = ToolSkillResolver(data_dir=data_dir)
    rec = r.synthesize_recommendation(_incident("c527_builtin_dump"), builtin_tools=_registry().builtin_tool_names())
    assert rec.remedy_kind == CODE_CHANGE
    assert rec.summary == "Built-in tool c527_builtin_dump needs a code change in AutoReiv (unbounded payload)."
    assert rec.proposed_patch.startswith("Built-in tool: c527_builtin_dump needs a code change in AutoReiv")
    assert "20146 bytes" in rec.proposed_patch and "Ask Developer" not in rec.proposed_patch
    assert r.apply_with_reason(rec) == (False, "code_change")


@pytest.mark.parametrize("tool", ["c527_runtime_dump", "mcp_srv_dump", "c527_unknown_dump"])
def test_runtime_mcp_and_unknown_tools_keep_ask_developer(data_dir, tool):
    rec = ToolSkillResolver(data_dir=data_dir).synthesize_recommendation(
        _incident(tool), builtin_tools=_registry().builtin_tool_names()
    )
    assert rec.remedy_kind == TOOL_ESCALATION


@pytest.mark.parametrize("tool", ["get_recent_errors", "list_available_skills_and_tools"])
def test_the_two_named_tools_get_a_limit_runbook_patch(data_dir, tool):
    rec = ToolSkillResolver(data_dir=data_dir).synthesize_recommendation(_incident(tool), builtin_tools={tool})
    assert rec.remedy_kind == "runbook_patch"
    assert f"When calling {tool}, always specify limit" in rec.proposed_patch


def test_the_agents_own_skill_wins_over_the_first_skill_listing_the_tool(data_dir):
    r = ToolSkillResolver(data_dir=data_dir)
    assert r.resolve_tool_to_skill("autoreiv", "shared_tool") == ("alpha-skill", "skills/alpha-skill/SKILL.md")
    assert r.resolve_tool_to_skill("autoreiv", "shared_tool", ["beta-skill"]) == (
        "beta-skill",
        "skills/beta-skill/SKILL.md",
    )
    # A ticked skill that does not list the tool (or a bad id) falls back to the first one.
    assert r.resolve_tool_to_skill("autoreiv", "shared_tool", ["missing", "../x"])[0] == "alpha-skill"


def test_audit_uses_the_registry_and_the_agents_ticked_skills(store, data_dir):
    class _Agents:
        def get_profile(self, agent_id):
            return {"allowed_skill": ["beta-skill"]} if agent_id == "autoreiv" else None

    sess = store.create_session(agent_id="autoreiv", title="C527")
    for i, tool in enumerate(["c527_builtin_dump", "c527_runtime_dump", "mcp_srv_dump", "shared_tool"]):
        store.save_message(
            session_id=sess.id,
            agent_id="autoreiv",
            message=ChatMessage(role=Role.TOOL, content="x" * 20000, name=tool, tool_call_id=f"c{i}"),
        )
    reg = _registry()
    reg.register_tool("shared_tool", "built-in", {"type": "object", "properties": {}}, _noop)
    result = run_telemetry_friction_audit(
        store, data_dir, lookback_hours=24, tool_registry=reg, agent_registry=_Agents()
    )
    by_tool = {r["tool_name"]: r for r in result["recommendations"]}
    assert by_tool["c527_builtin_dump"]["remedy_kind"] == CODE_CHANGE
    assert by_tool["shared_tool"]["remedy_kind"] == CODE_CHANGE
    assert by_tool["shared_tool"]["skill_id"] == "beta-skill"
    assert by_tool["c527_runtime_dump"]["remedy_kind"] == TOOL_ESCALATION
    assert by_tool["mcp_srv_dump"]["remedy_kind"] == TOOL_ESCALATION


def _client(store, data_dir):
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    from src.web.routers import observability

    app = FastAPI()
    app.include_router(observability.router)
    app.state.store = store
    app.state.data_dir = str(data_dir)
    app.state.tool_registry = _registry()
    return TestClient(app)


def _stage(store, rec):
    store.create_proposal(
        Proposal(
            id=rec.id,
            kind=ProposalKind.SKILL,
            payload_json=rec.model_dump_json(),
            status=ProposalStatus.DRAFT,
            requested_by_job_id="telemetry-friction-auditor",
        )
    )


def test_apply_and_escalate_refuse_a_code_change_card_plainly(store, data_dir):
    rec = ToolSkillResolver(data_dir=data_dir).synthesize_recommendation(
        _incident("c527_builtin_dump"), builtin_tools={"c527_builtin_dump"}
    )
    _stage(store, rec)
    c = _client(store, data_dir)
    base = "/api/observability/friction/recommendations"
    res = c.post(f"{base}/{rec.id}/apply")
    assert res.status_code == 409
    assert res.json()["detail"].startswith("This is a built-in AutoReiv tool: it needs a code change")
    assert c.post(f"{base}/{rec.id}/escalate", json={"developer_session_id": "d"}).status_code == 409
    assert c.post(f"{base}/{rec.id}/dismiss").status_code == 200
    assert {r["id"]: r for r in c.get(base).json()}[rec.id]["status"] == "dismissed"


def test_audit_route_passes_the_registry(store, data_dir):
    sess = store.create_session(agent_id="autoreiv", title="C527 route")
    store.save_message(
        session_id=sess.id,
        agent_id="autoreiv",
        message=ChatMessage(role=Role.TOOL, content="x" * 20000, name="c527_builtin_dump", tool_call_id="c1"),
    )
    body = _client(store, data_dir).post("/api/observability/friction/audit", json={"lookback_hours": 24}).json()
    assert [r["remedy_kind"] for r in body["recommendations"]] == [CODE_CHANGE]


def test_apply_patches_a_shipped_only_skill_through_a_user_copy(store, tmp_path):
    from src.infrastructure.content import store as content_store

    data = tmp_path / "data2"
    platform = tmp_path / "platform"
    (platform / "skills" / "health").mkdir(parents=True)
    (platform / "skills" / "health" / "SKILL.md").write_text(
        "---\nname: health\ntools:\n  - get_recent_errors\n---\n# Health\n", encoding="utf-8"
    )
    data.mkdir()
    content_store.configure(data, platform)
    try:
        r = ToolSkillResolver(data_dir=data, platform_dir=platform / "skills")
        rec = r.synthesize_recommendation(_incident("get_recent_errors"), builtin_tools={"get_recent_errors"})
        assert rec.skill_path == "skills/health/SKILL.md" and rec.remedy_kind == "runbook_patch"
        _stage(store, rec)
        res = _client(store, data).post(f"/api/observability/friction/recommendations/{rec.id}/apply")
        assert res.status_code == 200, res.text
        user_copy = (data / "skills" / "health" / "SKILL.md").read_text(encoding="utf-8")
        assert "When calling get_recent_errors, always specify limit" in user_copy
        assert "based_on:" in user_copy  # a proper user copy of the shipped skill
        assert "get_recent_errors" in (platform / "skills" / "health" / "SKILL.md").read_text(encoding="utf-8")
        assert "Common Pitfalls" not in (platform / "skills" / "health" / "SKILL.md").read_text(encoding="utf-8")
    finally:
        content_store.reset_store()


# ---------------------------------------------------------------- the two built-in tools stay under 8 KB


def test_get_recent_errors_stays_under_8kb_by_default(tmp_path):
    from src.application.skills.system_agent_tools import SystemAgentTools

    class _Telemetry:
        def get_recent_errors(self, limit=20, agent_id=None):
            return [
                {
                    "id": f"s{i}",
                    "timestamp": "2026-10-04T00:00:00",
                    "agent_id": "autoreiv",
                    "session_id": "x",
                    "span_type": "tool",
                    "name": "cli_exec",
                    "duration_ms": 1.0,
                    "error_message": "Traceback " + "y" * 3000,
                    "metadata": {"blob": "z" * 2000},
                }
                for i in range(limit)
            ]

    tools = SystemAgentTools.__new__(SystemAgentTools)
    tools.telemetry = _Telemetry()
    rows = tools.get_recent_errors()
    assert 1 <= len(rows) <= 10
    assert len(json.dumps(rows)) < 8192
    assert all("metadata" not in r and len(r["error_message"]) <= 303 for r in rows)
    assert rows[0]["id"] == "s0"  # newest kept
    with_meta = tools.get_recent_errors(limit=50, include_metadata=True)
    assert len(json.dumps(with_meta)) < 8192 and "metadata" in with_meta[0]


def test_catalog_stays_under_8kb_pages_and_filters(monkeypatch):
    from types import SimpleNamespace

    from src.application.skills import agent_builder_tools as abt
    from src.infrastructure.content import store as content_store

    reg = ScopedToolRegistry()
    for i in range(160):
        reg.register_tool(f"c527_tool_{i:03d}", "Does a long thing. " * 20, {"type": "object"}, _noop)
    skills = [
        SimpleNamespace(id=f"skill-{i:03d}", meta={"name": f"Skill {i}", "description": "Long words " * 30})
        for i in range(90)
    ]
    fake = SimpleNamespace(skills=SimpleNamespace(list=lambda: skills))
    monkeypatch.setattr(content_store, "get_store", lambda: fake)
    builder = abt.AgentBuilderTools.__new__(abt.AgentBuilderTools)
    builder.tool_registry = reg

    first = asyncio.run(builder.list_available_skills_and_tools())
    assert len(json.dumps(first)) < 8192
    assert first["total_tools"] == 160 and first["total_skills"] == 90
    assert first["catalog_tools"] and first["skills"]
    assert first["next_offset"] and "offset=" in first["more"]
    seen = {r["name"] for r in first["catalog_tools"]}
    offset = first["next_offset"]
    while offset is not None:
        page = asyncio.run(builder.list_available_skills_and_tools(offset=offset))
        assert len(json.dumps(page)) < 8192
        seen |= {r["name"] for r in page["catalog_tools"]}
        offset = page["next_offset"]
    assert len(seen) == 160  # paging skips nothing

    found = asyncio.run(builder.list_available_skills_and_tools(query="C527_TOOL_15"))
    assert found["total_tools"] == 10 and found["total_skills"] == 0 and found["next_offset"] is None
