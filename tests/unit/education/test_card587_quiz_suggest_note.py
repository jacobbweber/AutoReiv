"""CARD-587: quiz extraction on a plain note suggests questions (or takes the agent's) and saves them in a separate
quiz note; the source note is never edited."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.education.quiz_engine import quiz_note_path_for, suggest_quiz_items_from_note
from src.application.skills.education_tools import EducationTools
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

PLAIN = """---
title: Kubernetes basics
---
# Kubernetes basics

Kubernetes runs containers across a cluster of machines.

## Terms
- **Pod**: the smallest deployable unit, one or more containers sharing a network namespace
- **Node** - a worker machine that runs Pods under the kubelet
- etcd: the key-value store that holds all cluster state
- See also: https://kubernetes.io/docs
"""

PROSE = """# Why containers

Containers package an app with its dependencies so it runs the same everywhere. Teams adopted them to ship faster.
"""

WITH_QUIZ = """# Networking

## Quiz
- Q: Which protocol resolves names to IP addresses?
  A: DNS
"""


@pytest.fixture
def env(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "01_Notes" / "k8s").mkdir(parents=True)
    repo = AgentMemoryRepository(db_path=tmp_path / "tutor_memory.db")
    repo.initialize_schema()
    tools = EducationTools(repository=repo, wiki_root=wiki, default_agent_id="tutor")
    return tools, wiki


def _write(wiki: Path, rel: str, text: str) -> Path:
    p = wiki / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_suggestions_ask_for_the_term_so_the_exact_grader_works():
    items = suggest_quiz_items_from_note(PLAIN)
    assert [i["answer"] for i in items] == ["Pod", "Node", "etcd"]
    assert items[0]["prompt"].startswith("Which term matches this description: the smallest deployable unit")
    assert suggest_quiz_items_from_note(PROSE) == []


def test_quiz_note_path_sits_next_to_the_source():
    assert quiz_note_path_for("01_Notes/k8s/basics.md") == "01_Notes/k8s/basics-quiz.md"
    assert quiz_note_path_for("notes") == "notes-quiz.md"


def test_plain_note_gets_a_separate_quiz_note_and_is_not_edited(env):
    tools, wiki = env
    src = _write(wiki, "01_Notes/k8s/basics.md", PLAIN)
    before = src.read_bytes()
    res = tools.education_quiz_extract("01_Notes/k8s/basics.md")
    assert res["success"] and res["suggested"] and res["source_edited"] is False
    assert res["quiz_note_path"] == "01_Notes/k8s/basics-quiz.md"
    assert res["count"] == 3 and res["durable"] and len(res["persisted"]) == 3
    assert all(it["wiki_path"] == "01_Notes/k8s/basics-quiz.md" for it in res["items"])
    assert src.read_bytes() == before
    quiz = (wiki / "01_Notes/k8s/basics-quiz.md").read_text(encoding="utf-8")
    assert "- **Expected Binary Answer:** Pod" in quiz and "[[01_Notes/k8s/basics.md]]" in quiz


def test_prose_note_asks_the_agent_for_questions_and_writes_nothing(env):
    tools, wiki = env
    src = _write(wiki, "01_Notes/why.md", PROSE)
    before = src.read_bytes()
    res = tools.education_quiz_extract("01_Notes/why.md")
    assert res["success"] and res["needs_questions"] and res["count"] == 0
    assert "questions=" in res["hint"]
    assert not (wiki / "01_Notes/why-quiz.md").exists()
    assert src.read_bytes() == before


def test_agent_questions_are_saved_merged_and_graded_from_the_quiz_note(env):
    tools, wiki = env
    src = _write(wiki, "01_Notes/why.md", PROSE)
    before = src.read_bytes()
    first = tools.education_quiz_extract(
        "01_Notes/why.md", questions=[{"prompt": "What do containers package with the app?", "answer": "dependencies"}]
    )
    assert first["success"] and first["count"] == 1 and first["suggested"] is False
    again = tools.education_quiz_extract(
        "01_Notes/why.md",
        questions=[
            {"prompt": "What do containers package with the app?", "answer": "dependencies"},
            {"question": "Why did teams adopt containers?", "expected_answer": "to ship faster"},
        ],
    )
    assert again["count"] == 2  # merged, no duplicate
    assert src.read_bytes() == before
    item = next(i for i in again["items"] if i["expected_answer"] == "dependencies")
    graded = tools.education_quiz_grade(item_id=item["item_id"], answer="Dependencies")
    assert graded["success"] is True and graded["correct"] is True


def test_quiz_path_cannot_be_the_source_note(env):
    tools, wiki = env
    _write(wiki, "01_Notes/why.md", PROSE)
    res = tools.education_quiz_extract("01_Notes/why.md", questions=[{"prompt": "p?", "answer": "a"}], quiz_path="01_Notes/why.md")
    assert res["success"] is False and "separate" in res["error"]


def test_a_note_with_its_own_quiz_section_works_as_before(env):
    tools, wiki = env
    _write(wiki, "01_Notes/net.md", WITH_QUIZ)
    res = tools.education_quiz_extract("01_Notes/net.md")
    assert res["count"] == 1 and res["quiz_note_path"] is None
    assert not (wiki / "01_Notes/net-quiz.md").exists()
