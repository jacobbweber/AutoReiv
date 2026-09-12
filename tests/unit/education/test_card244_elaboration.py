"""CARD-244: Education Elaboration — explain-it-back binary external grade + write-back."""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.education.elaboration import (
    ELABORATION_CATEGORY,
    ELABORATION_ENTITY,
    extract_elaboration_items_from_note,
    grade_and_record_elaboration,
    grade_elaboration_binary,
    elaboration_from_mastery_row,
    write_elaboration_memory_fact,
    write_elaboration_wiki_outcome,
)
from src.application.education.retention_routine import run_education_retention
from src.domain.routines.models import Routine, ScheduleType
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def _repo(tmp_path: Path) -> AgentMemoryRepository:
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    return repo


def test_grade_elaboration_binary_uses_required_concepts_rubric():
    assert (
        grade_elaboration_binary(
            "A standing Job is a durable outcome-shaped job that survives sessions.",
            required_concepts=["standing Job", "durable", "outcome"],
        )
        is True
    )
    assert (
        grade_elaboration_binary(
            "Jobs are cool and chat toasts remind me later.",
            required_concepts=["standing Job", "durable", "outcome"],
        )
        is False
    )


def test_grade_elaboration_binary_uses_reference_token_containment():
    ref = "Routine to standing Job resurfaces due reviews from the mastery ledger"
    assert grade_elaboration_binary(
        "The mastery ledger drives Routine to standing Job resurfaces for due reviews.",
        reference=ref,
    )
    assert not grade_elaboration_binary("I do not remember anything.", reference=ref)
    # Soft equality path
    assert grade_elaboration_binary(ref, reference=ref)


def test_elaboration_grader_module_has_no_llm_self_score():
    import src.application.education.elaboration as elab

    src = inspect.getsource(elab)
    low = src.lower()
    assert "complete(" not in src
    assert "openai" not in low
    assert "ollama" not in low
    assert "chat.completions" not in low
    assert "self_score" not in low
    # Docstrings may say "never LLM self-score"; ban callable LLM paths only.
    assert "gateway.complete" not in low
    assert "llm_gateway" not in low


def test_extract_elaboration_items_from_wiki_section():
    body = """---
title: Elaboration Jobs
---

# Dual Coding: Standing Jobs

## Outline
- Jobs

## Elaboration
- Prompt: Explain standing Jobs in your own words.
  Reference: A standing Job is a durable outcome-shaped job that survives sessions.
  Concepts: standing Job, durable, outcome
- Prompt: What path resurfaces a miss?
  Reference: Routine to standing Job
  Concepts: Routine, standing Job
"""
    items = extract_elaboration_items_from_note(
        body,
        wiki_path="00_Inbox/elaboration-jobs.md",
        topic="Standing Jobs",
    )
    assert len(items) >= 2
    assert items[0]["kind"] == "elaboration"
    assert items[0]["item_id"].startswith("elab_")
    assert "standing job" in " ".join(items[0]["required_concepts"])
    assert items[0]["expected_answer"]


def test_miss_updates_mastery_ledger_and_next_due(tmp_path):
    repo = _repo(tmp_path)
    now = datetime(2026, 9, 11, 20, 0, 0, tzinfo=timezone.utc)
    item = {
        "item_id": "elab_miss_1",
        "topic": "Jobs",
        "wiki_path": "notes/jobs.md",
        "prompt": "Explain standing Jobs in your own words.",
        "expected_answer": "A standing Job is durable and outcome-shaped.",
        "required_concepts": ["standing Job", "durable", "outcome"],
    }
    result = grade_and_record_elaboration(
        repo=repo,
        item=item,
        given="I forgot — maybe a toast?",
        wiki_store=None,
        now=now,
        write_wiki=False,
        write_memory=True,
    )
    assert result["correct"] is False
    assert result["grade"] == "miss"
    assert result["grader"] == "binary_external_elaboration"
    row = repo.get_education_mastery("elab_miss_1")
    assert row is not None
    assert row["grade"] == "miss"
    assert row["miss_count"] >= 1
    due = datetime.fromisoformat(row["next_due"].replace("Z", "+00:00"))
    assert due == now + timedelta(days=1)
    assert result["memory_fact_id"]
    facts = [
        f
        for f in repo.list_facts_for_entity(ELABORATION_ENTITY)
        if f.get("attribute") == "elaboration_outcome"
    ]
    assert any("elab_miss_1" in (f.get("value") or "") and "miss" in (f.get("value") or "") for f in facts)
    assert all(f.get("category") == ELABORATION_CATEGORY for f in facts)


def test_pass_updates_ledger_pass(tmp_path):
    repo = _repo(tmp_path)
    now = datetime(2026, 9, 11, 20, 0, 0, tzinfo=timezone.utc)
    item = {
        "item_id": "elab_pass_1",
        "topic": "Jobs",
        "wiki_path": "notes/jobs.md",
        "prompt": "Explain standing Jobs.",
        "expected_answer": "durable outcome standing Job",
        "required_concepts": ["standing Job", "durable", "outcome"],
    }
    result = grade_and_record_elaboration(
        repo=repo,
        item=item,
        given="A standing Job is a durable outcome-shaped unit of work.",
        wiki_store=None,
        now=now,
        write_wiki=False,
        write_memory=True,
    )
    assert result["correct"] is True
    assert result["grade"] == "pass"
    row = repo.get_education_mastery("elab_pass_1")
    assert row["pass_count"] >= 1


def test_miss_can_schedule_routine_to_job_resurface(tmp_path):
    """Reuse CARD-242 retention path after elaboration miss [REQ-EDU-ELAB-002]."""
    repo = _repo(tmp_path)
    now = datetime(2026, 9, 11, 20, 0, 0, tzinfo=timezone.utc)
    item = {
        "item_id": "elab_resurf_1",
        "topic": "Priming",
        "wiki_path": "00_Inbox/priming.md",
        "prompt": "Explain Priming.",
        "expected_answer": "schema first before details",
        "required_concepts": ["schema", "priming"],
    }
    grade_and_record_elaboration(
        repo=repo,
        item=item,
        given="nope",
        wiki_store=None,
        now=now,
        write_wiki=False,
        write_memory=True,
    )
    # Force due now
    past = (now - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with repo.get_connection() as conn:
        conn.execute(
            "UPDATE education_mastery SET next_due = ?, pending_job_id = NULL WHERE item_id = ?",
            (past, "elab_resurf_1"),
        )

    class FakeOrch:
        def __init__(self):
            self.jobs = []

        def create_job_from_catalog_resolve(self, **kwargs):
            jid = f"job_{len(self.jobs)+1:04d}"
            self.jobs.append({"id": jid, **kwargs})
            return {"id": jid}

    orch = FakeOrch()
    routine = Routine(
        id="education-retrieval-retention",
        name="Education Retrieval + Retention",
        description="test",
        agent_id="assistant",
        prompt="resurface",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
        enabled=True,
    )
    result = run_education_retention(
        memory_repo=repo,
        orch=orch,
        routine=routine,
        agent_id="assistant",
        now=now,
    )
    assert result["status"] == "ok"
    assert result["minted_job_ids"]
    row = repo.get_education_mastery("elab_resurf_1")
    assert row["pending_job_id"] in result["minted_job_ids"]


class _FakeWiki:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.notes: dict[str, str] = {}

    def seed(self, rel: str, body: str):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        self.notes[rel] = body

    def append_note(self, relative_path: str, content: str, heading=None):
        from src.domain.wiki.store import WikiStore

        store = WikiStore(root_dir=self.root)
        return store.append_note(relative_path, content, heading=heading)

    def read_text(self, relative_path: str) -> str:
        return (self.root / relative_path).read_text(encoding="utf-8")


def test_wiki_and_memory_writeback_on_elaboration(tmp_path):
    repo = _repo(tmp_path)
    wiki_root = tmp_path / "wiki"
    wiki = _FakeWiki(wiki_root)
    rel = "00_Inbox/card244_elaboration.md"
    wiki.seed(
        rel,
        "---\ntitle: Elaboration\n---\n\n# Elaboration\n\n## Elaboration\n"
        "- Prompt: Explain standing Jobs.\n"
        "  Reference: durable outcome standing Job\n"
        "  Concepts: standing Job, durable, outcome\n",
    )
    items = extract_elaboration_items_from_note(
        wiki.read_text(rel), wiki_path=rel, topic="Jobs"
    )
    assert items
    item = items[0]
    now = datetime(2026, 9, 11, 21, 0, 0, tzinfo=timezone.utc)
    result = grade_and_record_elaboration(
        repo=repo,
        item=item,
        given="wrong answer without required ideas",
        wiki_store=wiki,
        now=now,
        write_wiki=True,
        write_memory=True,
    )
    assert result["correct"] is False
    assert result["wiki_writeback"].get("success") is True
    body = wiki.read_text(rel)
    assert "Elaboration outcomes" in body
    assert item["item_id"] in body
    assert "grade=miss" in body
    facts = list(repo.list_facts_for_entity(ELABORATION_ENTITY) or [])
    assert any("elaboration_outcome" == f.get("attribute") for f in facts)


def test_elaboration_from_mastery_row_shapes_explain_prompt():
    row = {
        "item_id": "edu_x",
        "topic": "Jobs",
        "wiki_path": "a.md",
        "prompt": "What mints resurface?",
        "expected_answer": "Routine to standing Job",
        "grade": "miss",
        "miss_count": 2,
    }
    elab = elaboration_from_mastery_row(row)
    assert elab["kind"] == "elaboration"
    assert "explain" in elab["prompt"].lower()
    assert elab["item_id"] == "edu_x"


def test_write_elaboration_memory_fact_direct(tmp_path):
    repo = _repo(tmp_path)
    item = {"item_id": "elab_direct", "topic": "T", "prompt": "P"}
    fid = write_elaboration_memory_fact(repo, item=item, correct=True, given="good")
    assert fid
    facts = repo.list_facts_for_entity(ELABORATION_ENTITY)
    assert any(fid == f.get("id") for f in facts)
