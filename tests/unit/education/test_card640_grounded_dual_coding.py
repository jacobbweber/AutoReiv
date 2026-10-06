"""CARD-640: the dual coding course step is built from the learner's wiki notes on the topic via one
model call, or writes nothing. The old fixed template (same paragraph, same four boxes, same quiz
item for every topic) is gone."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.application.education.course import (
    ORDERED_COURSE_STEPS,
    complete_course_step,
    jump_to_course_step,
    start_or_resume_course,
)
from src.application.education.dual_coding import compose_dual_coding, find_dual_coding_sources
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

TOPIC = "Raft log replication"
USER_NOTE = """---
title: Raft log replication
tags: [distributed-systems, raft]
---
# Raft log replication

The leader accepts client commands and appends them to its own log. It sends AppendEntries
messages to every follower. A follower appends the entries only if its log matches the leader's
previous index and term. Once a majority of followers have stored an entry, the leader advances
the commit index and applies the entry to its state machine. Followers learn the commit index
from the next AppendEntries heartbeat.
"""

GROUNDED = {
    "prose": "In Raft the leader appends each client command to its log, replicates it to followers with AppendEntries, and commits it once a majority has stored it.",
    "mermaid": "flowchart TD\n  A[Client command] --> B[Leader appends to log]\n  B --> C[AppendEntries to followers]\n  C --> D[Majority stored]\n  D --> E[Leader advances commit index]",
    "steps": ["Leader appends the command", "AppendEntries goes to every follower", "A majority stores it and the leader commits"],
    "question": "When does the Raft leader advance the commit index?",
    "answer": "When a majority of followers have stored the entry",
}

OLD_TEMPLATE = {
    "prose": f"Dual Coding for {TOPIC} pairs verbal concept definitions with visual relational models. The prose code establishes domain concepts and causal flow, while the visual code renders hierarchical and sequential interactions.",
    "mermaid": f"flowchart TD\n    A[{TOPIC}] --> B[Key Concepts & Invariants]\n    B --> C[Concrete Implementation Flow]\n    C --> D[Verified Mastery & Application]",
    "steps": ["Deconstruct core definitions and invariants in prose", "Trace relational structure", "Synthesize verbal and visual codes"],
    "question": f"What are the two representations used in Dual Coding for {TOPIC}?",
    "answer": "verbal prose and visual diagrams",
}


class FakeGateway:
    default_model_id = "fake-model"

    def __init__(self, reply=None, error: Exception | None = None):
        self.reply, self.error, self.requests = reply, error, []

    async def complete(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        text = self.reply if isinstance(self.reply, str) else "```json\n" + json.dumps(self.reply) + "\n```"
        return SimpleNamespace(text=text)


@pytest.fixture
def env(tmp_path: Path):
    repo = AgentMemoryRepository(db_path=tmp_path / "tutor_memory.db")
    repo.initialize_schema()
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    return repo, WikiTools(wiki_root=wiki_root), wiki_root


def _add_note(wiki_root: Path, rel: str, text: str) -> None:
    p = wiki_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _course_on_dual_coding(repo) -> str:
    course = start_or_resume_course(repo, topic_id=TOPIC, steps=ORDERED_COURSE_STEPS)
    jump_to_course_step(repo, course_id=course["course_id"], step="dual_coding")
    return course["course_id"]


def _md_files(wiki_root: Path) -> set:
    return {str(p.relative_to(wiki_root)) for p in wiki_root.rglob("*.md")}


def _assert_nothing_written(repo, wiki_root: Path, before: set, done: dict) -> None:
    assert _md_files(wiki_root) == before
    assert done["item_ids"] == [] and not done["wiki_path"]
    assert [r for r in repo.list_education_mastery(limit=500) if "dual_coding" in r["item_id"]] == []
    assert [f for f in repo.list_semantic_facts() if "dual_coding" in (f.get("attribute") or "")] == []
    assert done["course"]["current_step"] == "retrieval"


def test_template_function_is_gone():
    import src.application.education.course as course_mod

    assert not hasattr(course_mod, "build_dual_coding_preview")
    src = Path(course_mod.__file__).read_text(encoding="utf-8")
    assert "Key Concepts & Invariants" not in src
    assert "verbal prose and visual diagrams" not in src


def test_no_notes_on_the_topic_skips_and_writes_nothing(env):
    repo, tools, wiki_root = env
    cid = _course_on_dual_coding(repo)
    gw = FakeGateway(GROUNDED)
    composed = asyncio.run(compose_dual_coding(gw, tools, TOPIC))
    assert composed["ok"] is False and composed["skip_reason"] == "no_wiki_notes"
    assert gw.requests == []  # no model call without source notes
    before = _md_files(wiki_root)
    done = complete_course_step(repo, course_id=cid, wiki_tools_or_store=tools, dual_coding=composed)
    assert done["skip_reason"] == "no_wiki_notes"
    _assert_nothing_written(repo, wiki_root, before, done)


def test_step_without_composed_content_writes_nothing(env):
    repo, tools, wiki_root = env
    cid = _course_on_dual_coding(repo)
    before = _md_files(wiki_root)
    done = complete_course_step(repo, course_id=cid, wiki_tools_or_store=tools)
    assert done["skip_reason"] == "not_composed"
    _assert_nothing_written(repo, wiki_root, before, done)


def test_course_written_notes_are_not_sources(env):
    _repo, tools, wiki_root = env
    _add_note(wiki_root, "00_Inbox/course_environment_raft.md", f"---\ntitle: 'Course Environment: {TOPIC}'\ntags: [education, course, environment]\n---\n# Course Environment: {TOPIC}\nRaft log replication framing.\n")
    _add_note(wiki_root, "00_Inbox/priming_raft.md", f"---\ntitle: 'Priming: {TOPIC}'\ntags: [education, priming]\n---\n# Priming: {TOPIC}\nRaft log replication outline.\n")
    assert find_dual_coding_sources(tools, TOPIC) == []


def test_grounded_reply_is_written_with_source_links(env):
    repo, tools, wiki_root = env
    _add_note(wiki_root, "Distributed/raft-log-replication.md", USER_NOTE)
    sources = find_dual_coding_sources(tools, TOPIC)
    assert [s["path"] for s in sources] == ["Distributed/raft-log-replication.md"]
    gw = FakeGateway(GROUNDED)
    composed = asyncio.run(compose_dual_coding(gw, tools, TOPIC))
    assert composed["ok"] is True, composed
    assert len(gw.requests) == 1
    prompt = " ".join(str(m.content) for m in gw.requests[0].messages)
    assert "AppendEntries" in prompt  # the note text is the source handed to the model

    cid = _course_on_dual_coding(repo)
    done = complete_course_step(repo, course_id=cid, wiki_tools_or_store=tools, dual_coding=composed)
    assert done["skip_reason"] is None
    assert done["course"]["current_step"] == "retrieval"
    note = (wiki_root / done["wiki_path"]).read_text(encoding="utf-8")
    assert "```mermaid" in note and "AppendEntries to followers" in note
    assert "[[Distributed/raft-log-replication]]" in note
    assert "Key Concepts & Invariants" not in note
    item = repo.get_education_mastery(done["item_ids"][0])
    assert item["prompt"] == GROUNDED["question"]
    assert item["expected_answer"] == GROUNDED["answer"]


def test_old_template_reply_is_refused(env):
    _repo, tools, wiki_root = env
    _add_note(wiki_root, "Distributed/raft-log-replication.md", USER_NOTE)
    composed = asyncio.run(compose_dual_coding(FakeGateway(OLD_TEMPLATE), tools, TOPIC))
    assert composed["ok"] is False and composed["skip_reason"] == "model_output_invalid"


def test_unparseable_reply_is_refused(env):
    _repo, tools, wiki_root = env
    _add_note(wiki_root, "Distributed/raft-log-replication.md", USER_NOTE)
    composed = asyncio.run(compose_dual_coding(FakeGateway("I cannot help with that."), tools, TOPIC))
    assert composed["ok"] is False and composed["skip_reason"] == "model_output_invalid"


@pytest.mark.parametrize("gateway", [None, FakeGateway(error=RuntimeError("spark down"))])
def test_no_model_or_model_error_is_a_skip(env, gateway):
    _repo, tools, wiki_root = env
    _add_note(wiki_root, "Distributed/raft-log-replication.md", USER_NOTE)
    composed = asyncio.run(compose_dual_coding(gateway, tools, TOPIC))
    assert composed["ok"] is False and composed["skip_reason"] == "model_unavailable"


def test_preview_api_never_returns_the_template():
    from fastapi.testclient import TestClient

    from src.web.app import app

    res = TestClient(app).post("/api/education/course/dual-coding/preview", json={"topic": "Zyzzogeton quorum leases"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False and body["skip_reason"] in ("no_wiki_notes", "model_unavailable")
    assert "Key Concepts" not in json.dumps(body)
