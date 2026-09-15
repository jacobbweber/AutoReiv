"""CARD-327: Education Learning OS — Adaptive depth + mastery chrome + Studio usability.

Verifies:
- [REQ-EDU-DEPTH-001]: Durable depth/level model in agent memory.db (Explorer->Foundational->Practitioner->Expert->Master).
- [REQ-EDU-DEPTH-002]: Wiki growth portfolio notes per topic/domain (education-portfolio template in 00_Inbox/).
- [REQ-EDU-DEPTH-003]: Chrome snapshot contains depth model bound to real ledger (not toast theatre).
- [REQ-EDU-DEPTH-004]: REST API endpoints (GET /api/education/course/depth, POST /api/education/course/portfolio/create).
- [REQ-EDU-DEPTH-005]: Reopen/restart safety for depth semantic facts.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.application.education.course import (
    ORDERED_COURSE_STEPS,
    course_chrome_snapshot,
    start_or_resume_course,
)
from src.application.education.depth import (
    DEPTH_LADDER,
    calculate_topic_depth,
    create_growth_portfolio_note,
    get_topic_depth,
    record_topic_depth,
)
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.frontmatter import FrontmatterParser
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.web.app import app


def _assert_memory_db_path(db: Path) -> None:
    path_s = str(db).replace("\\", "/").lower()
    assert "memory" in path_s, f"ledger must live under memory.db path, got {db}"
    assert "storage.db" not in path_s, f"must never invent storage.db path, got {db}"


def test_req_edu_depth_001_depth_ladder_calculation_and_progression(tmp_path: Path):
    """[REQ-EDU-DEPTH-001] Depth ladder computes accurate levels (0..4) and milestones from ledger items."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    topic = "Vector Clocks"

    assert len(DEPTH_LADDER) == 5
    assert [d["academic_rank"] for d in DEPTH_LADDER] == [
        "Kindergarten",
        "Elementary",
        "High School",
        "Undergraduate",
        "Masters",
    ]

    # Level 0: Explorer (no items or 0 passed)
    d0 = calculate_topic_depth(repo, topic=topic)
    assert d0["level"] == 0
    assert d0["name"] == "explorer"
    assert d0["academic_rank"] == "Kindergarten"
    assert d0["total_items"] == 0
    assert d0["pass_rate"] == 0.0
    assert d0["next_milestone"] != ""

    # Seed 3 items with pass grade -> Level 1: Foundational (Elementary)
    for i in range(3):
        repo.upsert_education_mastery(
            item_id=f"vc_item_{i}",
            topic=topic,
            prompt=f"Vector clock prompt {i}",
            expected_answer=f"Answer {i}",
            grade="pass",
        )
    d1 = calculate_topic_depth(repo, topic=topic)
    assert d1["level"] == 1
    assert d1["name"] == "foundational"
    assert d1["academic_rank"] == "Elementary"
    assert d1["total_items"] == 3
    assert d1["pass_rate"] == 100.0

    # Seed 3 more items (total 6) -> Level 2: Practitioner (High School)
    for i in range(3, 6):
        repo.upsert_education_mastery(
            item_id=f"vc_item_{i}",
            topic=topic,
            prompt=f"Vector clock prompt {i}",
            expected_answer=f"Answer {i}",
            grade="pass",
        )
    d2 = calculate_topic_depth(repo, topic=topic)
    assert d2["level"] == 2
    assert d2["name"] == "practitioner"
    assert d2["academic_rank"] == "High School"
    assert d2["total_items"] == 6

    # Test record_topic_depth anchors fact in memory.db
    rec = record_topic_depth(repo, topic=topic)
    assert rec["level"] == 2
    facts = repo.list_semantic_facts()
    depth_facts = [f for f in facts if f["attribute"] == "topic_mastery_depth"]
    assert len(depth_facts) >= 1
    assert topic in depth_facts[0]["value"]


def test_req_edu_depth_002_wiki_growth_portfolio_note(tmp_path: Path):
    """[REQ-EDU-DEPTH-002] Generates durable growth portfolio note in 00_Inbox/ using education-portfolio template."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    topic = "CRDT State Sync"

    # Seed some mastery items
    for i in range(4):
        repo.upsert_education_mastery(
            item_id=f"crdt_item_{i}",
            topic=topic,
            prompt=f"CRDT question {i}",
            expected_answer=f"CRDT answer {i}",
            grade="pass",
        )

    res = create_growth_portfolio_note(tools, repo, topic=topic)
    assert res["success"] is True
    wiki_path = res["path"]
    assert wiki_path.replace("\\", "/").startswith("00_Inbox/")

    # Verify content and template
    full_path = wiki_root / wiki_path
    assert full_path.exists()
    content = full_path.read_text(encoding="utf-8")
    meta, body = FrontmatterParser.parse(content)
    assert meta.template == "education-portfolio"
    assert "portfolio" in meta.tags
    assert "growth" in meta.tags
    assert "CRDT State Sync" in body
    assert "Mastery Level" in body

    # Verify semantic fact anchored
    facts = repo.list_semantic_facts()
    portfolio_facts = [f for f in facts if f["attribute"] == "course_growth_portfolio"]
    assert len(portfolio_facts) >= 1
    assert topic in portfolio_facts[0]["value"]


def test_req_edu_depth_003_chrome_snapshot_includes_depth(tmp_path: Path):
    """[REQ-EDU-DEPTH-003] Chrome snapshot contains depth model bound to real ledger (not toast theatre)."""
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    topic = "Consistent Hashing"
    course = start_or_resume_course(repo, topic_id=topic, steps=ORDERED_COURSE_STEPS)

    repo.upsert_education_mastery(
        item_id="ch_item_1",
        topic=topic,
        prompt="What is virtual node replication?",
        expected_answer="Distributes hash space evenly",
        grade="pass",
    )

    chrome = course_chrome_snapshot(repo, topic_id=topic, course_id=course["course_id"])
    assert "depth" in chrome
    depth = chrome["depth"]
    assert depth["topic"] == topic
    assert "level" in depth
    assert "name" in depth
    assert "academic_rank" in depth
    assert "progress_percent" in depth
    assert "next_milestone" in depth


def test_req_edu_depth_004_rest_endpoints(tmp_path: Path):
    """[REQ-EDU-DEPTH-004] Endpoints for GET /api/education/course/depth and POST /api/education/course/portfolio/create."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    topic = "Gossip Protocol"
    course = start_or_resume_course(repo, topic_id=topic, steps=ORDERED_COURSE_STEPS)

    app.state.memory_repo = repo
    app.state.wiki_path = str(wiki_root)
    client = TestClient(app)

    # 1. GET depth
    res_get = client.get(f"/api/education/course/depth?topic={topic}")
    assert res_get.status_code == 200
    gdata = res_get.json()
    assert gdata["success"] is True
    assert gdata["depth"]["topic"] == topic
    assert "level" in gdata["depth"]
    assert "academic_rank" in gdata["depth"]

    # 2. POST create portfolio note
    res_post = client.post(
        "/api/education/course/portfolio/create",
        json={"topic": topic, "course_id": course["course_id"]},
    )
    assert res_post.status_code == 200
    pdata = res_post.json()
    assert pdata["success"] is True
    assert "path" in pdata
    assert pdata["path"].replace("\\", "/").startswith("00_Inbox/")
    assert (wiki_root / pdata["path"]).exists()


def test_req_edu_depth_005_reopen_kill_resume_safety(tmp_path: Path):
    """[REQ-EDU-DEPTH-005] Process kill / reopen preserves depth semantic facts and ledger anchors."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    topic = "Paxos Protocol"
    for i in range(5):
        repo.upsert_education_mastery(
            item_id=f"paxos_{i}",
            topic=topic,
            prompt=f"Paxos prompt {i}",
            expected_answer=f"Paxos answer {i}",
            grade="pass",
        )

    rec = record_topic_depth(repo, topic=topic)
    assert rec["level"] == 1

    # Simulate Process Kill: destroy repo and open repo2
    del repo
    repo2 = AgentMemoryRepository(db_path=db)

    # Reopen verification
    d = get_topic_depth(repo2, topic=topic)
    assert d["level"] == 1
    assert d["academic_rank"] == "Elementary"
    assert d["total_items"] == 5
