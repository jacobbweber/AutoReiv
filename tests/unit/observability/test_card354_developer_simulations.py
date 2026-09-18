"""
5 Comprehensive Tests for CARD-354:
Three live simulations using the developer agent against active agentic-test project,
validating telemetry capture, friction diagnosis, runbook optimization, and lifecycle safety.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.routines.telemetry_friction_auditor import run_telemetry_friction_audit
from src.application.skills.project_file_tools import ProjectFileTools
from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.domain.observability.friction_analyzer import TelemetryFrictionAnalyzer
from src.domain.observability.models import FrictionSignatureType
from src.domain.observability.tool_skill_resolver import ToolSkillResolver
from src.domain.orchestration.models import ProposalKind, ProposalStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.observability import router as observability_router

AGENTIC_TEST_PATH = Path("D:/Projects/Exprimentation/agentic-test").resolve()


@pytest.fixture
def sim_environment(tmp_path: Path):
    """
    Sets up an isolated AutoReiv user-data environment mirroring live AppData,
    seeded with developer pack and targeting the active agentic-test project.
    """
    user_data = tmp_path / "user_data"
    user_data.mkdir()

    # 1. Database
    db_dir = user_data / "database"
    db_dir.mkdir()
    store = SQLiteStateStore(db_path=db_dir / "autoreiv.db")
    store.initialize_db()

    # 2. Developer pack in user data
    dev_dir = user_data / "packs" / "developer"
    skills_dir = dev_dir / "skills"
    build_dir = skills_dir / "build"
    plan_dir = skills_dir / "plan"
    test_dir = skills_dir / "test"
    build_dir.mkdir(parents=True)
    plan_dir.mkdir(parents=True)
    test_dir.mkdir(parents=True)

    (dev_dir / "pack.json").write_text(
        json.dumps(
            {
                "id": "developer",
                "name": "Developer",
                "skills": [
                    {
                        "id": "plan",
                        "name": "Plan",
                        "tools": ["list_project_dir", "read_project_file", "read_card", "write_card"],
                    },
                    {
                        "id": "build",
                        "name": "Build",
                        "tools": ["read_project_file", "write_project_file", "git_status"],
                    },
                    {
                        "id": "test",
                        "name": "Test",
                        "tools": ["cli_exec", "execute_code"],
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (build_dir / "SKILL.md").write_text(
        "---\nname: Build\ndescription: Implement code changes\n---\n# Build\n\n## Order\n1. Read card\n2. Write code\n\n## Pitfalls\n\n- Do not invent scope beyond card.\n",
        encoding="utf-8",
    )
    (plan_dir / "SKILL.md").write_text(
        "---\nname: Plan\ndescription: Explore codebase\n---\n# Plan\n\n## Pitfalls\n\n- Do not plan without spec.\n",
        encoding="utf-8",
    )
    (test_dir / "SKILL.md").write_text(
        "---\nname: Test\ndescription: Run automated tests\n---\n# Test\n\n## Pitfalls\n\n- Do not ignore failing tests.\n",
        encoding="utf-8",
    )

    # 3. Platform wiki skill
    wiki_dir = user_data / "skills" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "SKILL.md").write_text(
        "---\nname: wiki\ndescription: Wiki notes\ntools:\n  - wiki_note_search\n  - wiki_note_read\n---\n# Wiki\n\n## Pitfalls\n\n- Do not use absolute paths.\n",
        encoding="utf-8",
    )

    # 4. Project tools targeting agentic-test
    project_tools = ProjectFileTools(default_project_root=str(AGENTIC_TEST_PATH))

    return {
        "user_data": user_data,
        "store": store,
        "project_tools": project_tools,
        "project_root": AGENTIC_TEST_PATH,
    }


def test_1_simulation_redundant_verification(sim_environment):
    """
    Test 1: Simulation 1 — Developer Agent Redundant Verification Loop in agentic-test.
    Developer writes a configuration change via write_project_file, then immediately
    performs read_project_file on the same target. Validates detection & runbook patch synthesis.
    """
    store = sim_environment["store"]
    user_data = sim_environment["user_data"]
    sess = store.create_session(agent_id="developer", title="Sim 1: Redundant Verification")
    session_id = sess.id

    store.save_message(
        session_id=session_id,
        agent_id="developer",
        message=ChatMessage(
            role=Role.USER,
            content="Update SentinelPulse configuration constants in src/sentinel/models.py",
        ),
    )

    mutation_call = ToolCall(
        id="call_write_1",
        name="write_project_file",
        arguments={"path": "src/sentinel/models.py", "content": "# SentinelPulse Models\nTIMEOUT_MS = 500\n"},
    )
    store.save_message(
        session_id=session_id,
        agent_id="developer",
        message=ChatMessage(role=Role.ASSISTANT, content="Writing config", tool_calls=[mutation_call]),
    )
    store.save_message(
        session_id=session_id,
        agent_id="developer",
        message=ChatMessage(
            role=Role.TOOL,
            name="write_project_file",
            content=json.dumps({"success": True, "path": "src/sentinel/models.py", "bytes": 45}),
            tool_call_id="call_write_1",
        ),
    )

    read_call = ToolCall(
        id="call_read_1",
        name="read_project_file",
        arguments={"path": "src/sentinel/models.py"},
    )
    store.save_message(
        session_id=session_id,
        agent_id="developer",
        message=ChatMessage(role=Role.ASSISTANT, content="Verifying write", tool_calls=[read_call]),
    )
    store.save_message(
        session_id=session_id,
        agent_id="developer",
        message=ChatMessage(
            role=Role.TOOL,
            name="read_project_file",
            content=json.dumps({"success": True, "path": "src/sentinel/models.py", "content": "TIMEOUT_MS = 500"}),
            tool_call_id="call_read_1",
        ),
    )

    analyzer = TelemetryFrictionAnalyzer(store=store)
    messages = list(store.get_messages(session_id=session_id))
    incidents = analyzer.analyze_messages(session_id=session_id, agent_id="developer", messages=messages)

    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.signature == FrictionSignatureType.REDUNDANT_VERIFICATION
    assert inc.agent_id == "developer"
    assert inc.tool_name == "read_project_file"
    assert "immediately after successful mutation" in inc.evidence

    resolver = ToolSkillResolver(data_dir=user_data)
    rec = resolver.synthesize_recommendation(inc)
    assert rec.remedy_kind == "runbook_patch"
    assert "packs/developer/skills" in (rec.skill_path or "")
    assert "Do not invoke read_project_file immediately after a successful mutation" in rec.proposed_patch


def test_2_simulation_payload_bloat_inspection(sim_environment):
    """
    Test 2: Simulation 2 — Developer Agent Database Inspection & Payload Bloat in agentic-test.
    Developer reads sentinel.db (16 KB > 8,192 bytes limit).
    Validates detection, byte attribution, and Factory Studio escalation.
    """
    store = sim_environment["store"]
    user_data = sim_environment["user_data"]
    project_tools = sim_environment["project_tools"]
    sess = store.create_session(agent_id="developer", title="Sim 2: Payload Bloat")
    session_id = sess.id

    store.save_message(
        session_id=session_id,
        agent_id="developer",
        message=ChatMessage(
            role=Role.USER,
            content="Inspect sentinel.db in agentic-test to verify schema tables and size",
        ),
    )

    real_db = AGENTIC_TEST_PATH / "sentinel.db"
    if real_db.is_file():
        file_res = project_tools.read_project_file("sentinel.db")
        content_payload = json.dumps(file_res)
    else:
        content_payload = "A" * 16384

    call_read = ToolCall(id="call_read_db", name="read_project_file", arguments={"path": "sentinel.db"})
    store.save_message(
        session_id=session_id,
        agent_id="developer",
        message=ChatMessage(role=Role.ASSISTANT, content="Reading database file", tool_calls=[call_read]),
    )
    store.save_message(
        session_id=session_id,
        agent_id="developer",
        message=ChatMessage(
            role=Role.TOOL,
            name="read_project_file",
            content=content_payload,
            tool_call_id="call_read_db",
        ),
    )

    analyzer = TelemetryFrictionAnalyzer(store=store)
    messages = list(store.get_messages(session_id=session_id))
    incidents = analyzer.analyze_messages(session_id=session_id, agent_id="developer", messages=messages)

    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.signature == FrictionSignatureType.PAYLOAD_BLOAT
    assert inc.agent_id == "developer"
    assert inc.tool_name == "read_project_file"
    assert inc.payload_bytes is not None and inc.payload_bytes > 8192
    assert inc.severity == "high"

    resolver = ToolSkillResolver(data_dir=user_data)
    rec = resolver.synthesize_recommendation(inc)
    assert rec.remedy_kind == "factory_escalation"
    assert "Factory Studio" in rec.proposed_patch
    assert "unbounded payload" in rec.summary.lower()


def test_3_simulation_search_thrashing(sim_environment):
    """
    Test 3: Simulation 3 — Developer Agent Search Thrashing.
    Developer executes 3 consecutive searches without reading returned content.
    Validates detection and anti-search-loop patch synthesis.
    """
    store = sim_environment["store"]
    user_data = sim_environment["user_data"]
    sess = store.create_session(agent_id="developer", title="Sim 3: Search Thrashing")
    session_id = sess.id

    store.save_message(
        session_id=session_id,
        agent_id="developer",
        message=ChatMessage(
            role=Role.USER,
            content="Find documentation regarding Sentinel alert deduplication",
        ),
    )

    call1 = ToolCall(id="c1", name="wiki_note_search", arguments={"query": "sentinel alerts"})
    call2 = ToolCall(id="c2", name="wiki_note_search", arguments={"query": "sentinel deduplication"})
    call3 = ToolCall(id="c3", name="wiki_note_search", arguments={"query": "alerts"})

    store.save_message(
        session_id=session_id,
        agent_id="developer",
        message=ChatMessage(role=Role.ASSISTANT, content="Searching documentation", tool_calls=[call1, call2, call3]),
    )
    for c in (call1, call2, call3):
        store.save_message(
            session_id=session_id,
            agent_id="developer",
            message=ChatMessage(
                role=Role.TOOL,
                name="wiki_note_search",
                content=json.dumps({"results": []}),
                tool_call_id=c.id,
            ),
        )

    analyzer = TelemetryFrictionAnalyzer(store=store)
    messages = list(store.get_messages(session_id=session_id))
    incidents = analyzer.analyze_messages(session_id=session_id, agent_id="developer", messages=messages)

    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.signature == FrictionSignatureType.SEARCH_THRASHING
    assert inc.tool_name == "wiki_note_search"
    assert "3 consecutive search" in inc.evidence

    resolver = ToolSkillResolver(data_dir=user_data)
    rec = resolver.synthesize_recommendation(inc)
    assert rec.remedy_kind == "runbook_patch"
    assert "skills/wiki/SKILL.md" in (rec.skill_path or "").replace("\\", "/")
    assert "Do not execute consecutive search calls with slight keyword variations" in rec.proposed_patch


def test_4_autonomous_routine_staging_and_rest_api(sim_environment):
    """
    Test 4: Autonomous Routine End-to-End Execution & REST API Staging.
    Runs run_telemetry_friction_audit across all 3 simulation sessions,
    verifying SQLite proposal staging and GET /api/observability/friction/recommendations.
    """
    store = sim_environment["store"]
    user_data = sim_environment["user_data"]

    test_1_simulation_redundant_verification(sim_environment)
    test_2_simulation_payload_bloat_inspection(sim_environment)
    test_3_simulation_search_thrashing(sim_environment)

    result = run_telemetry_friction_audit(store=store, data_dir=user_data, lookback_hours=24)
    assert result["success"] is True
    assert result["incidents_count"] == 3
    assert result["recommendations_count"] == 3
    assert result["auto_applied_count"] == 0

    proposals = store.list_proposals(kind=ProposalKind.SKILL)
    assert len(proposals) == 3
    for p in proposals:
        assert p.status == ProposalStatus.DRAFT

    app = FastAPI()
    app.state.store = store
    app.state.data_dir = str(user_data)
    app.include_router(observability_router)

    client = TestClient(app)
    res = client.get("/api/observability/friction/recommendations")
    assert res.status_code == 200
    recs = res.json()
    assert len(recs) == 3

    signatures = {r["friction_type"] for r in recs}
    assert "redundant_verification" in signatures
    assert "payload_bloat" in signatures
    assert "search_thrashing" in signatures


def test_5_safe_apply_dismiss_and_deduplication_lifecycle(sim_environment):
    """
    Test 5: Safe Runbook Application, Dismissal, and Idempotent Routine Deduplication.
    Verifies that 1-click apply writes only to user-data SKILL.md under ## Pitfalls,
    dismiss marks proposal as dismissed, and re-running audit creates no duplicate inbox clutter.
    """
    store = sim_environment["store"]
    user_data = sim_environment["user_data"]

    test_1_simulation_redundant_verification(sim_environment)
    test_2_simulation_payload_bloat_inspection(sim_environment)
    test_3_simulation_search_thrashing(sim_environment)

    run_telemetry_friction_audit(store=store, data_dir=user_data, lookback_hours=24)

    app = FastAPI()
    app.state.store = store
    app.state.data_dir = str(user_data)
    app.include_router(observability_router)
    client = TestClient(app)

    res = client.get("/api/observability/friction/recommendations")
    recs = res.json()
    redundant_rec = next(r for r in recs if r["friction_type"] == "redundant_verification")
    thrash_rec = next(r for r in recs if r["friction_type"] == "search_thrashing")

    apply_res = client.post(f"/api/observability/friction/recommendations/{redundant_rec['id']}/apply")
    assert apply_res.status_code == 200
    assert apply_res.json()["applied"] is True

    skill_file = user_data / redundant_rec["skill_path"]
    assert skill_file.is_file()
    skill_content = skill_file.read_text(encoding="utf-8")
    assert "Do not invoke read_project_file immediately after a successful mutation" in skill_content
    assert "## Pitfalls" in skill_content

    assert not Path("platform-packs/developer/skills/build/SKILL.md").read_text(encoding="utf-8").count(
        "Do not invoke read_project_file"
    )

    dismiss_res = client.post(f"/api/observability/friction/recommendations/{thrash_rec['id']}/dismiss")
    assert dismiss_res.status_code == 200
    assert dismiss_res.json()["dismissed"] is True

    recs_updated = client.get("/api/observability/friction/recommendations").json()
    red_status = next(r["status"] for r in recs_updated if r["id"] == redundant_rec["id"])
    thrash_status = next(r["status"] for r in recs_updated if r["id"] == thrash_rec["id"])
    assert red_status == "applied"
    assert thrash_status == "dismissed"

    audit_rerun = run_telemetry_friction_audit(store=store, data_dir=user_data, lookback_hours=24)
    assert audit_rerun["recommendations_count"] == 0
