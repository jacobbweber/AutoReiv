"""CARD-520: tool_escalation rename, migration, Observability Ask Developer and truthful Apply [REQ-520-001..014]."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.domain.gateway.models import ChatMessage, Role
from src.domain.observability.models import FrictionIncident, FrictionSignatureType, RunbookRecommendation
from src.domain.observability.tool_skill_resolver import ToolSkillResolver
from src.domain.orchestration.models import Proposal, ProposalKind, ProposalStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

ROOT = Path(__file__).resolve().parents[3]
OLD = "factory" + "_escalation"  # split so the sweep test does not match this file's intent


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    skill = d / "skills" / "wiki"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: wiki\ntools:\n  - wiki_note_read\n  - wiki_note_search\n---\n# Wiki\n\n## Common Pitfalls & Forbidden Paths\n- x\n",
        encoding="utf-8",
    )
    return d


@pytest.fixture
def store(tmp_path: Path) -> SQLiteStateStore:
    s = SQLiteStateStore(db_path=str(tmp_path / "t.db"))
    s.initialize_db()
    return s


def _incident(tool: str, size: int = 20790, sig=FrictionSignatureType.PAYLOAD_BLOAT, session: str = "sess_c520"):
    return FrictionIncident(
        id="fric_c520", session_id=session, agent_id="autoreiv", tool_name=tool, signature=sig,
        evidence="big", payload_bytes=size, severity="high",
    )


# ---------------------------------------------------------------- writers (REQ-520-003, 012)

def test_resolver_writes_tool_escalation_with_tool_fields_and_plain_wording(data_dir):
    rec = ToolSkillResolver(data_dir=data_dir).synthesize_recommendation(_incident("wiki_note_read"))
    assert rec.remedy_kind == "tool_escalation"
    assert rec.tool_name == "wiki_note_read"
    assert rec.payload_bytes == 20790
    assert rec.session_id == "sess_c520"
    assert rec.summary == "wiki_note_read needs pagination or a filter (unbounded payload)."
    assert rec.proposed_patch == "Ask Developer to add pagination or a filter to wiki_note_read: it returned 20790 bytes (limit 8 KB)."
    assert "Factory" not in rec.summary + rec.proposed_patch


def test_patch_recommendations_also_carry_the_tool_name(data_dir):
    rec = ToolSkillResolver(data_dir=data_dir).synthesize_recommendation(_incident("wiki_note_search"))
    assert rec.remedy_kind == "runbook_patch"
    assert rec.tool_name == "wiki_note_search"


# ---------------------------------------------------------------- model reader (REQ-520-004)

def test_model_reads_the_old_remedy_name_as_tool_escalation():
    rec = RunbookRecommendation(
        id="rec_old", agent_id="autoreiv", friction_type="payload_bloat", summary="s", proposed_patch="p", remedy_kind=OLD,
    )
    assert rec.remedy_kind == "tool_escalation"


# ---------------------------------------------------------------- apply reasons (REQ-520-010)

def test_apply_with_reason_explains_every_outcome(data_dir):
    r = ToolSkillResolver(data_dir=data_dir)
    esc = r.synthesize_recommendation(_incident("wiki_note_read"))
    assert r.apply_with_reason(esc) == (False, "tool_escalation")
    patch = r.synthesize_recommendation(_incident("wiki_note_search"))
    assert r.apply_with_reason(patch) == (True, "applied")
    assert r.apply_with_reason(patch) == (True, "already_present")
    orphan = r.synthesize_recommendation(_incident("totally_unknown_list", sig=FrictionSignatureType.SEARCH_THRASHING))
    assert orphan.skill_path is None
    assert r.apply_with_reason(orphan) == (False, "no_skill")
    gone = patch.model_copy(update={"skill_path": "skills/missing/SKILL.md", "proposed_patch": "- new"})
    assert r.apply_with_reason(gone) == (False, "missing_file")
    assert r.apply_recommendation(esc) is False  # bool wrapper kept for the auditor


# ---------------------------------------------------------------- routes (REQ-520-004, 009, 010)

def _client(store, data_dir):
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    from src.web.routers import observability

    app = FastAPI()
    app.include_router(observability.router)
    app.state.store = store
    app.state.data_dir = str(data_dir)
    return TestClient(app)


def _stage(store, rec: RunbookRecommendation):
    store.create_proposal(Proposal(id=rec.id, kind=ProposalKind.SKILL, payload_json=rec.model_dump_json(),
                                   status=ProposalStatus.DRAFT, requested_by_job_id="telemetry-friction-auditor"))


def test_apply_route_answers_409_404_or_200_with_plain_messages(store, data_dir):
    r = ToolSkillResolver(data_dir=data_dir)
    esc = r.synthesize_recommendation(_incident("wiki_note_read"))
    patch = r.synthesize_recommendation(_incident("wiki_note_search"))
    orphan = r.synthesize_recommendation(_incident("totally_unknown_list", sig=FrictionSignatureType.SEARCH_THRASHING))
    gone = patch.model_copy(update={"id": "rec_gone", "skill_path": "skills/missing/SKILL.md"})
    for rec in (esc, patch, orphan, gone):
        _stage(store, rec)
    c = _client(store, data_dir)
    base = "/api/observability/friction/recommendations"
    res = c.post(f"{base}/{esc.id}/apply")
    assert res.status_code == 409
    assert res.json()["detail"] == "This recommendation needs a tool change, not a runbook patch. Use Ask Developer."
    res = c.post(f"{base}/{orphan.id}/apply")
    assert res.status_code == 409
    assert res.json()["detail"] == "No skill lists totally_unknown_list, so there is nothing to patch."
    assert c.post(f"{base}/rec_gone/apply").status_code == 404
    assert c.post(f"{base}/{patch.id}/apply").status_code == 200


def test_list_normalizes_old_records_and_derives_the_tool_name(store, data_dir):
    ledger = data_dir / "skills" / "_friction_recommendations.json"
    ledger.write_text(json.dumps([{
        "id": "rec_legacy", "agent_id": "autoreiv", "skill_path": None, "friction_type": "payload_bloat",
        "summary": "Escalate c520_inventory_dump to Factory Studio (unbounded payload).",
        "proposed_patch": "Escalate c520_inventory_dump to Factory Studio: Tool lacks pagination/filter parameters to constrain large payloads (20790 bytes).",
        "remedy_kind": OLD, "status": "pending",
    }]), encoding="utf-8")
    recs = _client(store, data_dir).get("/api/observability/friction/recommendations").json()
    legacy = next(r for r in recs if r["id"] == "rec_legacy")
    assert legacy["remedy_kind"] == "tool_escalation"
    assert legacy["tool_name"] == "c520_inventory_dump"
    assert legacy["payload_bytes"] == 20790


def test_escalate_marks_the_recommendation_and_an_audit_does_not_recreate_it(store, data_dir):
    from src.application.routines.telemetry_friction_auditor import run_telemetry_friction_audit

    sess = store.create_session(agent_id="autoreiv", title="C520 test")
    store.save_message(session_id=sess.id, agent_id="autoreiv", message=ChatMessage(role=Role.TOOL, content="x" * 20000, name="c520_inventory_dump", tool_call_id="c1"))
    first = run_telemetry_friction_audit(store, data_dir, lookback_hours=24)
    assert first["recommendations_count"] == 1
    rec_id = first["recommendations"][0]["id"] if isinstance(first["recommendations"][0], dict) else first["recommendations"][0].id
    c = _client(store, data_dir)
    res = c.post(f"/api/observability/friction/recommendations/{rec_id}/escalate", json={"developer_session_id": "dev-520"})
    assert res.status_code == 200, res.text
    assert store.get_proposal(rec_id).status == ProposalStatus.APPROVED
    listed = {r["id"]: r for r in c.get("/api/observability/friction/recommendations").json()}
    assert listed[rec_id]["status"] == "escalated"
    assert listed[rec_id]["developer_session_id"] == "dev-520"
    ledger = json.loads((data_dir / "skills" / "_friction_recommendations.json").read_text(encoding="utf-8"))
    assert next(r for r in ledger if r["id"] == rec_id)["status"] == "escalated"
    assert c.get("/api/observability/friction/recommendations", params={"status": "escalated"}).json()[0]["id"] == rec_id
    again = run_telemetry_friction_audit(store, data_dir, lookback_hours=24)
    assert again["recommendations_count"] == 0


def test_escalate_refuses_a_runbook_patch(store, data_dir):
    patch = ToolSkillResolver(data_dir=data_dir).synthesize_recommendation(_incident("wiki_note_search"))
    _stage(store, patch)
    res = _client(store, data_dir).post(f"/api/observability/friction/recommendations/{patch.id}/escalate", json={"developer_session_id": "d"})
    assert res.status_code == 409


# ---------------------------------------------------------------- distill (REQ-520-001, 002)

class _Gateway:
    def __init__(self, payload):
        self.default_model_id = "m"
        resp = AsyncMock()
        resp.text = json.dumps(payload)
        self.complete = AsyncMock(return_value=resp)


def _distill_env(tmp_path, store):
    from src.application.skills.distillation_service import SkillDistillationService

    data = tmp_path / "dd"
    (data / "packs" / "autoreiv").mkdir(parents=True)
    (data / "packs" / "autoreiv" / "pack.json").write_text(json.dumps({"schema_version": "1.1", "id": "autoreiv", "name": "AutoReiv", "skills": []}), encoding="utf-8")
    sess = store.create_session(agent_id="autoreiv", title="t")
    store.save_message(session_id=sess.id, agent_id="autoreiv", message=ChatMessage(role=Role.USER, content="weather in Boston?"))
    mid = store.save_message(session_id=sess.id, agent_id="autoreiv", message=ChatMessage(role=Role.ASSISTANT, content="I have no weather tool."))
    return SkillDistillationService, data, sess.id, mid


@pytest.mark.asyncio
@pytest.mark.parametrize("model_key", ["tool_escalation", OLD])
async def test_distill_needs_tool_result_uses_tool_escalation(tmp_path, store, model_key):
    Svc, data, sid, mid = _distill_env(tmp_path, store)
    payload = {"needs_tool": True, "suggested_tool_name": "get_city_weather", "plain_summary": {"observed_slip": "a", "remedy": "b"},
               model_key: {"target_agent_id": "autoreiv", "seed_intent": "Current weather for a city", "starter_objectives": ["o1"]}}
    svc = Svc(store=store, gateway=_Gateway(payload), data_dir=data)
    result = await svc.distill_turn(session_id=sid, message_id=mid)
    assert result["needs_tool"] is True
    assert result["tool_escalation"]["seed_intent"] == "Current weather for a city"
    assert result["tool_escalation"]["suggested_tool_name"] == "get_city_weather"
    assert OLD not in result
    saved = [m for m in store.get_messages(sid) if m.role == Role.SKILL_PROPOSAL]
    assert saved and OLD not in saved[-1].content and '"tool_escalation"' in saved[-1].content
    prompt = svc.gateway.complete.call_args[0][0].messages[0].content
    assert '"tool_escalation"' in prompt and OLD not in prompt


class _FailingGateway:
    default_model_id = "m"

    async def complete(self, req):
        raise TimeoutError()


class _EmptyGateway:
    """A reasoning model that spends max_tokens thinking and returns no content (Jarvis, 2026-09-26)."""

    default_model_id = "m"

    async def complete(self, req):
        resp = AsyncMock()
        resp.text = ""
        return resp


WEATHER = "AutoReiv has no weather tool; it needs a tool that returns the current weather for a city."


@pytest.mark.asyncio
@pytest.mark.parametrize("gateway", [None, _FailingGateway(), _EmptyGateway()], ids=["no_gateway", "timeout", "empty_reply"])
async def test_fallback_distill_still_sees_a_missing_tool_in_the_guidance(tmp_path, store, gateway):
    """REQ-520-015: when the model gives nothing, guidance that names a missing tool still yields a tool escalation."""
    Svc, data, sid, mid = _distill_env(tmp_path, store)
    svc = Svc(store=store, gateway=gateway, data_dir=data)
    result = await svc.distill_turn(session_id=sid, message_id=mid, guidance=WEATHER)
    assert result["needs_tool"] is True
    esc = result["tool_escalation"]
    assert esc["target_agent_id"] == "autoreiv"
    assert esc["seed_intent"] == WEATHER
    assert esc["suggested_tool_name"] == "get_weather"
    assert esc["deliverable_type"] == "tool"
    assert result["runbook_markdown"] is None
    saved = [m for m in store.get_messages(sid) if m.role == Role.SKILL_PROPOSAL]
    assert json.loads(saved[-1].content)["needs_tool"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("guidance", ["Always cite the wiki page you used.", "Use the tool with limit 10 next time.", ""])
async def test_fallback_distill_keeps_a_runbook_when_no_tool_is_missing(tmp_path, store, guidance):
    Svc, data, sid, mid = _distill_env(tmp_path, store)
    result = await Svc(store=store, gateway=None, data_dir=data).distill_turn(session_id=sid, message_id=mid, guidance=guidance)
    assert result["needs_tool"] is False
    assert result["tool_escalation"] is None
    assert result["runbook_markdown"]


# ---------------------------------------------------------------- migration (REQ-520-005)

def test_startup_migration_rewrites_old_names_once(tmp_path, store, data_dir):
    from src.application.observability.tool_escalation_migration import migrate_tool_escalation_names

    sess = store.create_session(agent_id="autoreiv", title="old")
    old_prop = {"status": "ok", "needs_tool": True, OLD: {"seed_intent": "weather", "suggested_tool_name": "get_w"}}
    store.save_message(session_id=sess.id, agent_id="autoreiv", message=ChatMessage(role=Role.SKILL_PROPOSAL, content=json.dumps(old_prop), name="distill_skill"))
    store.save_message(session_id=sess.id, agent_id="autoreiv", message=ChatMessage(role=Role.SKILL_PROPOSAL, content="{not json " + OLD, name="distill_skill"))
    store.save_message(session_id=sess.id, agent_id="autoreiv", message=ChatMessage(role=Role.ASSISTANT, content="talking about " + OLD))
    store.create_proposal(Proposal(id="rec_old1", kind=ProposalKind.SKILL, status=ProposalStatus.DRAFT, requested_by_job_id="telemetry-friction-auditor",
                                   payload_json=json.dumps({"id": "rec_old1", "remedy_kind": OLD, "summary": "s"})))
    ledger = data_dir / "skills" / "_friction_recommendations.json"
    ledger.write_text(json.dumps([{"id": "rec_old1", "remedy_kind": OLD}, {"id": "rec_new", "remedy_kind": "runbook_patch"}]), encoding="utf-8")

    counts = migrate_tool_escalation_names(store, data_dir)
    assert counts == {"messages": 1, "proposals": 1, "ledger": 1}
    msgs = store.get_messages(sess.id)
    first = json.loads(msgs[0].content)
    assert OLD not in first and first["tool_escalation"]["suggested_tool_name"] == "get_w"
    assert msgs[1].content.startswith("{not json")  # malformed row untouched
    assert msgs[2].content == "talking about " + OLD  # only skill_proposal rows
    assert json.loads(store.get_proposal("rec_old1").payload_json)["remedy_kind"] == "tool_escalation"
    assert [r["remedy_kind"] for r in json.loads(ledger.read_text(encoding="utf-8"))] == ["tool_escalation", "runbook_patch"]
    assert migrate_tool_escalation_names(store, data_dir) == {"messages": 0, "proposals": 0, "ledger": 0}


def test_app_startup_runs_the_migration():
    src = (ROOT / "src" / "web" / "app.py").read_text(encoding="utf-8")
    assert "migrate_tool_escalation_names(" in src


# ---------------------------------------------------------------- sweep (REQ-520-012, 014)

ALLOW = {
    "src/domain/observability/models.py",
    "src/application/observability/tool_escalation_migration.py",
    "src/web/static/modules/studios/tool_escalation.js",
}


def test_old_name_only_in_the_allowlist():
    hits = []
    for p in (ROOT / "src").rglob("*"):
        if p.suffix not in {".py", ".js", ".html"} or not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text(encoding="utf-8", errors="ignore")
        if (OLD in text or "data-factory-escalation" in text) and rel not in ALLOW:
            hits.append(rel)
    assert hits == []


def test_no_factory_in_operator_strings():
    for rel in ("src/web/static/modules/studios/observability.js", "src/web/static/modules/studios/chat/render.js",
                "src/web/static/modules/studios/chat/teach_modal.js", "src/domain/observability/tool_skill_resolver.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        code = re.sub(r"//.*$|#.*$", "", text, flags=re.M)
        assert "Factory" not in code, rel


def test_adr_and_changelog_name_card_520():
    adr = (ROOT / "docs" / "adr" / "0060-retire-the-agent-training-factory.md").read_text(encoding="utf-8")
    assert "`tool_escalation` (CARD-520" in adr
    log = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "CARD-520" in log.split("## [", 2)[1]
