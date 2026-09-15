"""CARD-323: Education Learning OS — Elaboration course step.

Verifies:
- [REQ-EDU-ELAB-001]: Elaboration is an ordered education_course step (explain-in-own-words).
- [REQ-EDU-ELAB-002]: Step complete writes Wiki artifact (templated) + ledger anchors.
- [REQ-EDU-ELAB-003]: Advances current_step / course status honestly (restart-safe).
- [REQ-EDU-ELAB-004]: Proof: failing test -> green; API endpoints; no toast-only Done.
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
from src.application.education.elaboration import (
    build_elaboration_preview,
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


def test_req_edu_elab_001_ordered_course_step():
    """[REQ-EDU-ELAB-001] Elaboration is step 4 in ORDERED_COURSE_STEPS; preview generates Socratic probes."""
    assert isinstance(ORDERED_COURSE_STEPS, (list, tuple))
    assert "elaboration" in ORDERED_COURSE_STEPS
    assert ORDERED_COURSE_STEPS[0] == "priming"
    assert ORDERED_COURSE_STEPS[1] == "dual_coding"
    assert ORDERED_COURSE_STEPS[2] == "retrieval"
    assert ORDERED_COURSE_STEPS[3] == "elaboration"

    preview = build_elaboration_preview(topic="Two-Phase Commit Protocol")
    assert preview["topic"] == "Two-Phase Commit Protocol"
    assert "prompt" in preview and len(preview["prompt"]) > 0
    assert "probing_questions" in preview and len(preview["probing_questions"]) >= 2
    assert preview["template"] == "education-elaboration"


def test_req_edu_elab_002_complete_writes_wiki_and_ledger_anchors(tmp_path: Path):
    """[REQ-EDU-ELAB-002] Completing elaboration writes a templated Wiki note and anchors in memory.db."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(
        repo, topic_id="Two-Phase Commit Protocol", steps=ORDERED_COURSE_STEPS
    )
    # 1. priming -> dual_coding
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    # 2. dual_coding -> retrieval
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    # 3. retrieval -> elaboration
    c3 = complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    assert c3["course"]["current_step"] == "elaboration"

    # 4. complete elaboration with learner explanation
    explanation = "In 2PC, a coordinator sends Prepare to all participants; if all agree, it commits, otherwise aborts."
    elab_done = complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        learner_explanation=explanation,
    )
    assert elab_done["success"] is True
    assert elab_done["completed_step"] == "elaboration"

    # Verify Wiki note and front matter
    wiki_path = elab_done.get("wiki_path") or elab_done["artifact"]["path"]
    assert "00_inbox" in wiki_path.lower()
    full_path = wiki_root / wiki_path
    assert full_path.exists()
    content = full_path.read_text(encoding="utf-8")
    meta, body = FrontmatterParser.parse(content)
    assert meta.template == "education-elaboration"
    assert "education" in meta.tags
    assert "elaboration" in meta.tags
    assert explanation in content

    # Verify memory.db ledger anchors
    assert len(elab_done["item_ids"]) >= 1
    item_id = elab_done["item_ids"][0]
    mastery_item = repo.get_education_mastery(item_id)
    assert mastery_item is not None
    assert mastery_item["topic"] == "Two-Phase Commit Protocol"
    assert mastery_item["grade"] == "unseen"

    # Verify learner semantic fact
    facts = repo.list_semantic_facts()
    elab_facts = [f for f in facts if f["attribute"] == "course_step_elaboration"]
    assert len(elab_facts) >= 1
    assert "Two-Phase Commit Protocol" in elab_facts[0]["value"]


def test_req_edu_elab_003_advances_course_step_honestly(tmp_path: Path):
    """[REQ-EDU-ELAB-003] Completing elaboration advances current_step to construction."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(
        repo, topic_id="Paxos Consensus", steps=ORDERED_COURSE_STEPS
    )
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)

    res = complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        learner_explanation="Paxos reaches consensus through prepare/promise and accept/accepted phases.",
    )
    assert res["success"] is True
    assert res["course"]["current_step"] == "construction"
    assert res["course"]["status"] == "active"


def test_req_edu_elab_004_restart_safe_and_api(tmp_path: Path):
    """[REQ-EDU-ELAB-004] Reopen memory.db preserves state; REST API preview and complete work."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(
        repo, topic_id="Vector Clocks", steps=ORDERED_COURSE_STEPS
    )
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)

    done = complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        learner_explanation="Vector clocks determine causal ordering between distributed events.",
    )
    assert done["success"] is True

    # Reopen test
    repo2 = AgentMemoryRepository(db_path=db)
    persisted = get_course(repo2, course_id=course["course_id"])
    assert persisted is not None
    assert persisted["current_step"] == "construction"

    # API endpoints
    app.state.memory_repo = repo2
    app.state.wiki_path = str(wiki_root)
    client = TestClient(app)
    # Preview endpoint
    res_preview = client.post(
        "/api/education/course/elaboration/preview",
        json={"topic": "Vector Clocks"},
    )
    assert res_preview.status_code == 200
    pdata = res_preview.json()
    assert pdata["success"] is True
    assert pdata["topic"] == "Vector Clocks"
    assert "prompt" in pdata
    assert "probing_questions" in pdata

    # Complete endpoint
    res_complete = client.post(
        "/api/education/course/elaboration/complete",
        json={
            "course_id": course["course_id"],
            "topic": "Vector Clocks",
            "learner_explanation": "Vector clocks track partial orders of events in distributed systems.",
        },
    )
    assert res_complete.status_code == 200
    cdata = res_complete.json()
    assert cdata["success"] is True
