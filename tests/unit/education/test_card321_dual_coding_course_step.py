"""CARD-321: Education Learning OS — Dual Coding as real course step.

Verifies:
- [REQ-EDU-DUAL-001]: Dual Coding is an ordered education_course step (not jump-only chrome).
- [REQ-EDU-DUAL-002]: Player / diagram path is usable for the Dual Coding step.
- [REQ-EDU-DUAL-003]: Step complete writes Wiki artifact + ledger anchors in agent memory.db.
- [REQ-EDU-DUAL-004]: Stays inside CARD-320 course pipeline (advances current_step / status honestly).
- [REQ-EDU-DUAL-005]: Proof: restart-safe, failing test -> green, no toast-only Done.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.application.education.course import (
    ORDERED_COURSE_STEPS,
    complete_course_step,
    get_course,
    start_or_resume_course,
)
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.web.app import app


def _assert_memory_db_path(db: Path) -> None:
    path_s = str(db).replace("\\", "/").lower()
    assert "memory" in path_s, f"ledger must live under memory.db path, got {db}"
    assert "storage.db" not in path_s, f"must never invent storage.db path, got {db}"


def test_req_edu_dual_001_ordered_course_step():
    """[REQ-EDU-DUAL-001] Dual Coding is an ordered step in ORDERED_COURSE_STEPS, situated between priming and retrieval."""
    assert isinstance(ORDERED_COURSE_STEPS, (list, tuple))
    assert "dual_coding" in ORDERED_COURSE_STEPS
    assert ORDERED_COURSE_STEPS[0] == "priming"
    assert ORDERED_COURSE_STEPS[1] == "dual_coding"
    assert ORDERED_COURSE_STEPS[2] == "retrieval"


def test_req_edu_dual_002_player_diagram_preview_contract():
    """[REQ-EDU-DUAL-002] Player / diagram path provides usable prose and Mermaid structure for topic."""
    from src.application.education.course import build_dual_coding_preview

    preview = build_dual_coding_preview(topic="Distributed Consensus")
    assert preview["topic"] == "Distributed Consensus"
    assert "prose" in preview and len(preview["prose"]) > 0
    assert "mermaid" in preview and "flowchart" in preview["mermaid"]
    assert "step_through" in preview and isinstance(preview["step_through"], list)


def test_req_edu_dual_003_complete_writes_wiki_and_ledger_anchors(tmp_path: Path):
    """[REQ-EDU-DUAL-003] Completing dual_coding writes a Wiki artifact with Mermaid and anchors in memory.db."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    # Start course with ORDERED_COURSE_STEPS (which has dual_coding after priming)
    course = start_or_resume_course(
        repo, topic_id="Raft Log Replication", steps=ORDERED_COURSE_STEPS
    )
    assert course["current_step"] == "priming"

    # Complete priming -> advances to dual_coding
    priming_done = complete_course_step(
        repo, course_id=course["course_id"], wiki_tools_or_store=tools
    )
    assert priming_done["success"] is True
    assert priming_done["course"]["current_step"] == "dual_coding"

    # Complete dual_coding step
    dual_done = complete_course_step(
        repo, course_id=course["course_id"], wiki_tools_or_store=tools
    )
    assert dual_done["success"] is True
    assert dual_done["completed_step"] == "dual_coding"

    # Verify Wiki artifact
    wiki_path = dual_done.get("wiki_path") or dual_done["artifact"]["path"]
    assert "00_Inbox" in wiki_path or "00_inbox" in wiki_path.lower()
    full_path = wiki_root / wiki_path
    assert full_path.exists()
    content = full_path.read_text(encoding="utf-8")
    assert "```mermaid" in content
    assert "flowchart" in content
    assert "dual_coding" in content

    # Verify memory.db ledger anchors
    assert len(dual_done["item_ids"]) >= 1
    item_id = dual_done["item_ids"][0]
    mastery_item = repo.get_education_mastery(item_id)
    assert mastery_item is not None
    assert mastery_item["topic"] == "Raft Log Replication"
    assert "dual_coding" in mastery_item["item_id"]

    # Verify learner semantic fact
    facts = repo.list_semantic_facts()
    dual_facts = [f for f in facts if "dual_coding" in (f.get("attribute") or "")]
    assert len(dual_facts) >= 1


def test_req_edu_dual_004_advances_current_step_honestly(tmp_path: Path):
    """[REQ-EDU-DUAL-004] Completing dual_coding honestly advances current_step to retrieval inside course pipeline."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(
        repo, topic_id="Vector Clocks", steps=ORDERED_COURSE_STEPS
    )
    # Fast forward to dual_coding
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    current = get_course(repo, course_id=course["course_id"])
    assert current["current_step"] == "dual_coding"
    assert current["status"] == "active"

    # Complete dual_coding
    res = complete_course_step(
        repo, course_id=course["course_id"], wiki_tools_or_store=tools
    )
    assert res["course"]["current_step"] == "retrieval"
    assert res["course"]["status"] == "active"


def test_req_edu_dual_005_restart_safe_and_api(tmp_path: Path):
    """[REQ-EDU-DUAL-005] Course at dual_coding step is restart-safe and accessible via API."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    c0 = start_or_resume_course(
        repo, topic_id="Paxos Lease", steps=ORDERED_COURSE_STEPS
    )
    complete_course_step(repo, course_id=c0["course_id"], wiki_tools_or_store=tools)

    # Reopen DB to verify restart-safety
    repo2 = AgentMemoryRepository(db_path=db)
    repo2.initialize_schema()
    c_reopened = get_course(repo2, course_id=c0["course_id"])
    assert c_reopened["current_step"] == "dual_coding"

    # Test preview endpoint via FastAPI TestClient
    client = TestClient(app)
    resp = client.post(
        "/api/education/course/dual-coding/preview",
        json={"topic": "Paxos Lease", "agent_id": "assistant"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["topic"] == "Paxos Lease"
    assert "mermaid" in data
    assert "prose" in data
