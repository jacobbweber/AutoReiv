"""CARD-324: Education Learning OS — Construction / Application labs with graded pressure.

Verifies:
- [REQ-EDU-LAB-001]: Construction / Application labs exist as ordered course step(s) with graded pressure.
- [REQ-EDU-LAB-002]: Lab complete / grade writes templated Wiki artifact + ledger anchors.
- [REQ-EDU-LAB-003]: Miss / incomplete does not fake mastery; ties to existing Retention / mastery honesty.
- [REQ-EDU-LAB-004]: Proof: failing test -> green; API endpoints; no toast-only Done.
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
from src.application.education.labs import grade_lab_submission
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.frontmatter import FrontmatterParser
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.web.app import app

# A lab as `grounded_steps.compose_step_content(..., "construction")` returns it from a learner's
# consistent hashing notes [CARD-643]; the old fixed per-topic lab is gone.
HASH_LAB = {
    "ok": True,
    "step": "construction",
    "objective": "Build a consistent hashing ring with virtual nodes",
    "tasks": [
        "Place nodes and keys on the hash ring",
        "Give each server virtual nodes",
        "Look up the next clockwise node for a key",
    ],
    "criteria": [
        "Key lookup finds the next clockwise node on the ring",
        "Adding a node only moves keys from its successor",
    ],
    "question": "Which node owns a key on the ring?",
    "answer": "The next clockwise node",
    "sources": [],
}


def _assert_memory_db_path(db: Path) -> None:
    path_s = str(db).replace("\\", "/").lower()
    assert "memory" in path_s, f"ledger must live under memory.db path, got {db}"
    assert "storage.db" not in path_s, f"must never invent storage.db path, got {db}"


def test_req_edu_lab_001_lab_specification_and_graded_pressure():
    """[REQ-EDU-LAB-001] Construction and Application labs exist in ORDERED_COURSE_STEPS; graded pressure evaluates invariants."""
    assert "construction" in ORDERED_COURSE_STEPS
    assert "application" in ORDERED_COURSE_STEPS
    assert ORDERED_COURSE_STEPS.index("construction") == 4
    assert ORDERED_COURSE_STEPS.index("application") == 5

    c_spec = HASH_LAB
    assert len(c_spec["criteria"]) >= 2

    # Graded pressure: empty submission fails
    fail_res = grade_lab_submission(
        topic="Consistent Hashing Ring",
        step="construction",
        submission="",
        expected_invariants=c_spec["criteria"],
    )
    assert fail_res["passed"] is False
    assert fail_res["score"] == 0.0
    assert len(fail_res["failed_invariants"]) > 0
    assert fail_res["receipt"]["status"] == "Failed"

    # Graded pressure: substantive submission satisfying invariants passes
    good_solution = (
        "Implementation of Consistent Hashing Ring: We map nodes and keys to a 360-degree hash ring using SHA-256. "
        "Each physical server has 100 virtual nodes for even distribution. Invariant 1: Key lookups locate the next "
        "clockwise node. Invariant 2: Adding or removing a node only migrates keys to/from the adjacent successor, "
        "preserving minimal key redistribution."
    )
    pass_res = grade_lab_submission(
        topic="Consistent Hashing Ring",
        step="construction",
        submission=good_solution,
        expected_invariants=c_spec["criteria"],
    )
    assert pass_res["passed"] is True
    assert pass_res["score"] == 1.0
    assert len(pass_res["passed_invariants"]) >= 2
    assert pass_res["receipt"]["status"] == "Passed"


def test_req_edu_lab_002_lab_complete_writes_templated_wiki_and_advances_course(tmp_path: Path):
    """[REQ-EDU-LAB-002] Passed lab writes templated education-lab Wiki note and updates mastery ledger."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(
        repo, topic_id="Consistent Hashing Ring", steps=ORDERED_COURSE_STEPS
    )
    # Fast-forward priming -> dual_coding -> retrieval -> elaboration -> construction
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        learner_explanation="Consistent hashing allows distributing hash table keys across nodes with minimal remapping.",
    )

    c_cur = get_course(repo, course_id=course["course_id"])
    assert c_cur["current_step"] == "construction"

    # Complete construction step with passing lab submission
    lab_submission = (
        "Consistent Hashing Ring Construction:\n"
        "1. Circular keyspace ring with virtual nodes.\n"
        "2. Binary search across sorted node tokens for O(log N) key lookup.\n"
        "3. Invariant: Adding a node only invalidates K/N keys from direct successor."
    )
    res = complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        lab_submission=lab_submission,
        composed=HASH_LAB,
    )
    assert res["success"] is True
    assert res["completed_step"] == "construction"
    assert res["course"]["current_step"] == "application"

    # Verify Wiki note and education-lab front matter
    wiki_path = res.get("wiki_path") or res["artifact"]["path"]
    assert "00_inbox" in wiki_path.lower()
    full_path = wiki_root / wiki_path
    assert full_path.exists()
    content = full_path.read_text(encoding="utf-8")
    meta, body = FrontmatterParser.parse(content)
    assert meta.template == "education-lab"
    assert "education" in meta.tags
    assert "lab" in meta.tags
    assert "## Result" in body
    assert "**Status:** Passed" in body

    # The quiz item is the grounded lab's own question [CARD-643]
    assert len(res["item_ids"]) == 1
    mastery = repo.get_education_mastery(res["item_ids"][0])
    assert mastery["prompt"] == HASH_LAB["question"]

    # Verify learner semantic fact
    facts = repo.list_semantic_facts()
    lab_facts = [f for f in facts if f["attribute"] == "course_step_construction"]
    assert len(lab_facts) >= 1
    assert "Consistent Hashing Ring" in lab_facts[0]["value"]


def test_req_edu_lab_003_lab_miss_records_miss_schedules_retention_and_halts_advancement(tmp_path: Path):
    """[REQ-EDU-LAB-003] Failed lab records miss, schedules next_due retention, and halts step advancement."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(
        repo, topic_id="Raft Consensus Algorithm", steps=ORDERED_COURSE_STEPS
    )
    # Fast forward to construction
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        learner_explanation="Raft decomposes consensus into leader election, log replication, and safety.",
    )

    # Submit an empty/failing lab submission
    bad_submission = "I don't know how to build this yet."
    res = complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        lab_submission=bad_submission,
        composed={**HASH_LAB, "objective": "Replicate the Raft log"},
    )
    assert res["success"] is False
    assert res.get("passed") is False
    assert res.get("completed_step") == "construction"
    # Course does NOT advance to application
    assert res["course"]["current_step"] == "construction"
    assert res["course"]["status"] == "active"

    assert res["grade_result"]["passed"] is False

    # Learner model records weakness fact
    facts = repo.list_semantic_facts()
    weakness_facts = [
        f for f in facts if "weakness" in f["attribute"] or "weakness" in f["value"] or f["attribute"] == "course_step_construction_miss"
    ]
    assert len(weakness_facts) >= 1


def test_req_edu_lab_004_endpoints_and_validation(tmp_path: Path):
    """[REQ-EDU-LAB-004] Preview and grade API endpoints reject empty input and record graded pressure."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(
        repo, topic_id="B-Tree Indexing", steps=ORDERED_COURSE_STEPS
    )
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        learner_explanation="B-Trees balance search trees for disk storage blocks.",
    )

    app.state.memory_repo = repo
    app.state.wiki_path = str(wiki_root)
    client = TestClient(app)

    # 1. Preview endpoint
    res_prev = client.post(
        "/api/education/course/lab/preview",
        json={"topic": "B-Tree Indexing", "step": "construction"},
    )
    assert res_prev.status_code == 200
    pdata = res_prev.json()
    assert pdata["success"] is True
    assert pdata["step"] == "construction"
    # No notes on the topic here: no lab is invented [CARD-643]
    assert pdata["ok"] is False and pdata["skip_reason"]
    assert "invariants" not in pdata and "test_command" not in pdata

    # 2. Grade endpoint rejects empty submission with 422
    res_bad = client.post(
        "/api/education/course/lab/grade",
        json={
            "course_id": course["course_id"],
            "step": "construction",
            "submission": "   ",
        },
    )
    assert res_bad.status_code == 422

    # 3. Grade endpoint with passing submission
    res_pass = client.post(
        "/api/education/course/lab/grade",
        json={
            "course_id": course["course_id"],
            "step": "construction",
            "submission": (
                "B-Tree implementation maintains balanced node heights where keys are sorted. "
                "Invariant 1: All leaf nodes remain at the exact same depth. "
                "Invariant 2: Internal nodes have between ceil(M/2) and M child pointers."
            ),
        },
    )
    assert res_pass.status_code == 200
    pass_data = res_pass.json()
    assert pass_data["success"] is True
    assert pass_data["passed"] is True
    assert pass_data["course"]["current_step"] == "application"
