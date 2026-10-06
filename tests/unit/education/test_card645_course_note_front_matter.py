"""CARD-645: course step notes keep their metadata in front matter, with a document type per step.

The old notes wrote "tags: / kind: / step: / topic: / created:" lines (dual coding) or a
"> **Topic:** ... **Generated:**" block (elaboration, labs, analysis, environment) at the top of the
body, and every note was typed `priming_schema`.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.application.education.course import complete_course_step, start_or_resume_course
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.frontmatter import FrontmatterParser
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

NOW = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)
TOPIC = "Raft log replication"
BODY_META = re.compile(
    r"^(tags|kind|step|topic|created):|^>\s*\*\*(Topic|Pedagogy Phase|Generated|Created|Status|Delivery Profile|Timer):\*\*",
    re.MULTILINE,
)

DUAL = {
    "ok": True,
    "prose": "The leader appends entries and followers accept AppendEntries only when the previous log index and term match.",
    "mermaid": "flowchart LR\n  L[Leader] --> F[Follower]",
    "steps": ["Leader appends the entry", "Followers check prevLogIndex and prevLogTerm"],
    "question": "When does a follower accept AppendEntries?",
    "answer": "When its log matches the previous log index and term",
    "sources": [{"path": "00_Inbox/raft-notes.md", "title": "Raft notes"}],
}


@pytest.fixture()
def env(tmp_path: Path):
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    repo = AgentMemoryRepository(db_path=tmp_path / "assistant_memory.db")
    repo.initialize_schema()
    return wiki_root, WikiTools(wiki_root=wiki_root), repo


def _complete(repo, tools, step: str, **kw):
    course = start_or_resume_course(repo, topic_id=f"{TOPIC} {step}", steps=[step, "retention"])
    return complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools, now=NOW, **kw)


def _note(wiki_root: Path, result: dict):
    path = result.get("wiki_path")
    assert path, result
    meta, body = FrontmatterParser.parse((wiki_root / path).read_text(encoding="utf-8"))
    return meta, body


def test_dual_coding_note_metadata_is_front_matter_only(env):
    wiki_root, tools, repo = env
    meta, body = _note(wiki_root, _complete(repo, tools, "dual_coding", dual_coding=DUAL))
    assert not BODY_META.search(body), body[:400]
    assert meta.document_type == "course_dual_coding"
    extra = meta.model_extra or {}
    assert extra.get("kind") == "education_course_step"
    assert extra.get("step") == "dual_coding"
    assert "dual_coding" in meta.tags


@pytest.mark.parametrize(
    "step,kw",
    [
        ("analysis", {}),
        ("construction", {"lab_submission": "My Raft lab: leader appends, followers check prevLogIndex and prevLogTerm, conflicting entries are truncated."}),
    ],
)
def test_other_course_step_notes_have_their_own_document_type(env, step, kw):
    wiki_root, tools, repo = env
    result = _complete(repo, tools, step, **kw)
    if not result.get("wiki_path"):
        pytest.skip(f"{step} wrote no note")
    meta, body = _note(wiki_root, result)
    assert not BODY_META.search(body), body[:400]
    assert meta.document_type == f"course_{step}"
    extra = meta.model_extra or {}
    assert extra.get("kind") == "education_course_step"
    assert extra.get("step") == step


def test_no_course_step_note_is_typed_priming_schema_except_priming(env):
    wiki_root, tools, repo = env
    _complete(repo, tools, "dual_coding", dual_coding=DUAL)
    _complete(repo, tools, "analysis")
    typed = {}
    for p in (wiki_root / "00_Inbox").glob("*.md"):
        meta, _ = FrontmatterParser.parse(p.read_text(encoding="utf-8"))
        typed[meta.title] = meta.document_type
    course_notes = {t: d for t, d in typed.items() if t.startswith("Course ")}
    assert course_notes, typed
    assert "priming_schema" not in course_notes.values(), course_notes
