"""CARD-651: the growth portfolio note repeated its metadata in a "> **Topic:** / **Generated:**" body
block, listed the same capability lines for every topic ("Verified definitions and mental models for
X", "Grounded with dual coding ...") and wrote an already-passed quiz item about its own level. Now the
metadata lives in front matter, the body holds only the learner's real numbers and items, and no quiz
item is written."""

from __future__ import annotations

from pathlib import Path

from src.application.education.depth import create_growth_portfolio_note
from src.application.skills.wiki_tools import WikiTools
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.domain.wiki.frontmatter import FrontmatterParser
from src.domain.wiki.store import WikiStore

TOPIC = "Raft log replication"
TEMPLATE_LINES = (
    "Verified definitions and mental models",
    "Grounded with dual coding, retrieval practice",
    "Ledger items tracked under single-brain",
    "Continue through active course pipeline",
    "Pedagogy Phase",
)


def _env(tmp_path: Path):
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    repo = AgentMemoryRepository(db_path=tmp_path / "assistant_memory.db")
    repo.initialize_schema()
    repo.upsert_education_mastery(
        item_id="raft_q1", topic=TOPIC, prompt="What must match before a follower appends entries?",
        expected_answer="The previous index and term", grade="pass",
    )
    repo.upsert_education_mastery(
        item_id="raft_q2", topic=TOPIC, prompt="When does the leader advance the commit index?",
        expected_answer="After a majority stored the entry", grade="miss",
    )
    return WikiTools(wiki_root=wiki_root), repo, wiki_root


def test_portfolio_note_has_front_matter_metadata_and_no_template_lines(tmp_path: Path):
    tools, repo, wiki_root = _env(tmp_path)
    res = create_growth_portfolio_note(tools, repo, topic=TOPIC)
    assert res["success"] is True
    meta, body = FrontmatterParser.parse((wiki_root / res["path"]).read_text(encoding="utf-8"))
    extra = meta.model_extra or {}
    assert meta.document_type == "growth_portfolio"
    assert extra.get("kind") == "education_growth_portfolio"
    assert extra.get("course_topic") == TOPIC
    assert extra.get("mastery_level") is not None and extra.get("academic_rank")
    for line in TEMPLATE_LINES:
        assert line not in body, line
    assert "> **Topic:**" not in body and "**Generated:**" not in body
    # The body shows the learner's real items and numbers.
    assert "What must match before a follower appends entries?" in body
    assert "When does the leader advance the commit index?" in body
    assert "1 of 2" in body or "50.0%" in body


def test_portfolio_writes_no_quiz_item_about_itself(tmp_path: Path):
    tools, repo, _ = _env(tmp_path)
    before = {r["item_id"] for r in repo.list_education_mastery(limit=100)}
    create_growth_portfolio_note(tools, repo, topic=TOPIC)
    rows = repo.list_education_mastery(limit=100)
    assert {r["item_id"] for r in rows} == before
    assert not any("growth portfolio depth level" in str(r.get("prompt")) for r in rows)
    # The depth is still recorded as a learner fact.
    assert [f for f in repo.list_semantic_facts() if f["attribute"] == "course_growth_portfolio"]
