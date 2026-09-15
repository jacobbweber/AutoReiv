"""CARD-325: Education Learning OS — Environment framing + Analysis→Retention handoff.

Verifies:
- [REQ-EDU-ENV-001]: Environment framing participates in the course path with durable Wiki/ledger anchors.
- [REQ-EDU-ENV-002]: Analysis→Retention handoff is kill/resume safe (no lost schedule / course step).
- [REQ-EDU-ENV-003]: Uses existing Retention next_due / Routine→Job primitives — no parallel scheduler.
- [REQ-EDU-ENV-004]: Proof: failing test -> green; API endpoints; kill/resume safety.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from src.application.education.analysis import (
    build_analysis_scorecard,
    execute_analysis_retention_handoff,
)
from src.application.education.course import (
    ORDERED_COURSE_STEPS,
    complete_course_step,
    get_course,
    start_or_resume_course,
)
from src.application.education.environment import (
    build_environment_framing,
    get_active_delivery_profile,
    select_delivery_profile,
)
from src.application.education.retention_routine import run_education_retention
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.frontmatter import FrontmatterParser
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.web.app import app


def _assert_memory_db_path(db: Path) -> None:
    path_s = str(db).replace("\\", "/").lower()
    assert "memory" in path_s, f"ledger must live under memory.db path, got {db}"
    assert "storage.db" not in path_s, f"must never invent storage.db path, got {db}"


def test_req_edu_env_001_environment_framing_participates_in_course(tmp_path: Path):
    """[REQ-EDU-ENV-001] Environment framing generates durable Wiki note, profile selection, and ledger anchors."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    topic = "Distributed Tracing"

    # Verify framing helper
    select_delivery_profile(repo, "calm_focus")
    active = get_active_delivery_profile(repo)
    assert active["id"] == "calm_focus"

    framing = build_environment_framing(topic=topic, profile_id=active["id"])
    assert framing["topic"] == topic
    assert framing["profile"]["id"] == "calm_focus"
    assert "constraints" in framing and len(framing["constraints"]) >= 2
    assert "framing_markdown" in framing and len(framing["framing_markdown"]) > 0

    # Fast forward course to environment step (index 7)
    course = start_or_resume_course(repo, topic_id=topic, steps=ORDERED_COURSE_STEPS)
    # 0. priming -> dual_coding
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    # 1. dual_coding -> retrieval
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    # 2. retrieval -> elaboration
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    # 3. elaboration -> construction
    complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        learner_explanation="Distributed tracing propagates span contexts across RPC boundaries.",
    )
    # 4. construction -> application
    complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        lab_submission="Span context injection with deterministic trace IDs across boundary calls.",
    )
    # 5. application -> analysis
    complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        lab_submission="End-to-end trace collection under injected latency exercising invariant guarantees.",
    )
    # 6. analysis -> environment
    c_analysis = complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
    )
    assert c_analysis["course"]["current_step"] == "environment"

    # 7. Complete environment step
    c_env = complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
    )
    assert c_env["success"] is True
    assert c_env["completed_step"] == "environment"
    assert c_env["course"]["current_step"] == "amplifiers"

    # Verify Wiki note
    wiki_path = c_env.get("wiki_path") or c_env["artifact"]["path"]
    full_path = wiki_root / wiki_path
    assert full_path.exists()
    content = full_path.read_text(encoding="utf-8")
    meta, body = FrontmatterParser.parse(content)
    assert meta.template in ("education-priming", "education-score", "education-lab")
    assert "environment" in meta.tags

    # Verify ledger anchors
    assert len(c_env["item_ids"]) >= 1
    mid = c_env["item_ids"][0]
    mastery = repo.get_education_mastery(mid)
    assert mastery is not None
    assert mastery["topic"] == topic

    # Verify semantic fact
    facts = repo.list_semantic_facts()
    env_facts = [f for f in facts if f["attribute"] == "course_step_environment"]
    assert len(env_facts) >= 1
    assert topic in env_facts[0]["value"]


def test_req_edu_env_002_analysis_retention_handoff_kill_resume_safe(tmp_path: Path):
    """[REQ-EDU-ENV-002] Analysis->Retention handoff persists all next_due dates and course step safely across kill/reopen."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    topic = "Circuit Breaker Pattern"
    course = start_or_resume_course(repo, topic_id=topic, steps=ORDERED_COURSE_STEPS)

    # Seed some mastery items for topic
    repo.upsert_education_mastery(
        item_id="cb_item_1",
        topic=topic,
        prompt="What triggers the open state?",
        expected_answer="Error threshold reached",
        grade="pass",
    )
    repo.upsert_education_mastery(
        item_id="cb_item_2",
        topic=topic,
        prompt="What state attempts limited requests?",
        expected_answer="Half-open",
        grade="miss",
    )

    # Fast-forward to analysis
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        learner_explanation="Circuit breakers trip when error rates exceed thresholds to protect downstream services.",
    )
    complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        lab_submission="State machine with closed, open, and half-open transitions preserving invariant guarantees.",
    )
    complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        lab_submission="End-to-end Circuit Breaker Pattern workload execution verifying invariant guarantees hold under failure pressure.",
    )

    # Scorecard verification before handoff
    card = build_analysis_scorecard(repo, topic)
    assert card["topic"] == topic
    assert card["total_items"] >= 2

    # Now complete Analysis step -> triggers handoff to retention
    c_analysis = complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
    )
    assert c_analysis["success"] is True
    assert c_analysis["completed_step"] == "analysis"

    # Simulate Process Kill: destroy repo instance and open fresh
    del repo
    repo2 = AgentMemoryRepository(db_path=db)

    # Reopen verification
    reopened_course = get_course(repo2, course_id=course["course_id"])
    assert reopened_course is not None
    assert reopened_course["current_step"] == "environment"
    assert reopened_course["status"] == "active"

    # Verify all mastery items for topic have durable next_due timestamps
    items = repo2.list_education_mastery(topic=topic)
    assert len(items) >= 2
    for it in items:
        assert it.get("next_due") is not None
        # Check ISO format
        datetime.fromisoformat(it["next_due"].replace("Z", "+00:00"))

    # Verify handoff semantic fact
    facts = repo2.list_semantic_facts()
    handoff_facts = [f for f in facts if f["attribute"] == "course_handoff_retention"]
    assert len(handoff_facts) >= 1
    assert topic in handoff_facts[0]["value"]


def test_req_edu_env_003_uses_existing_retention_primitives(tmp_path: Path):
    """[REQ-EDU-ENV-003] Retention handoff relies strictly on education_mastery.next_due and routine minting."""
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    topic = "Lease Coordination"
    now = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)

    # Create mastery item without next_due
    repo.upsert_education_mastery(
        item_id="lease_item_1",
        topic=topic,
        prompt="What is a split-brain guard?",
        expected_answer="Time-bounded lease duration",
        grade="miss",
    )

    # Execute handoff
    handoff_res = execute_analysis_retention_handoff(repo, topic=topic, now=now)
    assert handoff_res["success"] is True
    assert handoff_res["scheduled_count"] >= 1
    assert "lease_item_1" in handoff_res["scheduled_item_ids"]

    # Mastery item must have stage 0 next_due (+1 day)
    updated = repo.get_education_mastery("lease_item_1")
    assert updated is not None
    assert updated["next_due"] == "2026-09-16T12:00:00Z"

    # Routine query on next day recognizes it as due
    future = now + timedelta(days=2)
    due_items = repo.list_due_education_mastery(as_of=future)
    assert any(d["item_id"] == "lease_item_1" for d in due_items)

    # Retention routine execution confirms items surfaced without second scheduler
    ret_res = run_education_retention(memory_repo=repo, now=future)
    assert ret_res["due_count"] >= 1


def test_req_edu_env_004_endpoints_and_validation(tmp_path: Path):
    """[REQ-EDU-ENV-004] Preview and complete REST endpoints for environment framing and analysis handoff."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)
    assert tools is not None

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    topic = "Leader Election Protocol"
    course = start_or_resume_course(repo, topic_id=topic, steps=ORDERED_COURSE_STEPS)

    app.state.memory_repo = repo
    app.state.wiki_path = str(wiki_root)
    client = TestClient(app)

    # 1. Environment Preview endpoint
    res_prev = client.post(
        "/api/education/course/environment/preview",
        json={"topic": topic, "profile_id": "pomodoro"},
    )
    assert res_prev.status_code == 200
    pdata = res_prev.json()
    assert pdata["success"] is True
    assert pdata["topic"] == topic
    assert pdata["profile"]["id"] == "pomodoro"
    assert "constraints" in pdata

    # 2. Analysis Handoff endpoint
    res_handoff = client.post(
        "/api/education/course/analysis/handoff",
        json={"course_id": course["course_id"], "topic": topic},
    )
    assert res_handoff.status_code == 200
    hdata = res_handoff.json()
    assert hdata["success"] is True
    assert "scheduled_item_ids" in hdata
