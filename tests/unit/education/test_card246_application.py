"""CARD-246: Education Application - Exercise Job + binary external verify."""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.education.application import (
    APPLICATION_CATEGORY,
    APPLICATION_ENTITY,
    APPLICATION_KIND,
    apply_application_fail_path,
    build_exercise_job_intent,
    extract_application_items_from_note,
    grade_and_record_application,
    grade_application_binary,
    mint_exercise_job,
    write_application_memory_fact,
    write_application_wiki_outcome,
)
from src.application.orchestration.bounded_auto_replan import MAX_REPLAN_ATTEMPTS
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def _repo(tmp_path: Path) -> AgentMemoryRepository:
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    return repo


def test_grade_application_binary_uses_required_concepts():
    assert (
        grade_application_binary(
            "I minted a standing Job, then HITL park after bounded replan exhausted.",
            required_concepts=["standing Job", "HITL park", "bounded replan"],
        )
        is True
    )
    assert (
        grade_application_binary(
            "I just used a chat toast reminder.",
            required_concepts=["standing Job", "HITL park", "bounded replan"],
        )
        is False
    )


def test_grade_application_binary_uses_reference_soft_match():
    ref = "Fail triggers bounded replan then HITL park; pass advances mastery ledger"
    assert grade_application_binary(
        "On fail we do bounded replan then HITL park; on pass mastery ledger advances.",
        reference=ref,
    )
    assert not grade_application_binary("I do not remember.", reference=ref)
    assert grade_application_binary(ref, reference=ref)


def test_application_grader_module_has_no_llm_self_score():
    import src.application.education.application as app

    src = inspect.getsource(app)
    low = src.lower()
    assert "complete(" not in src
    assert "openai" not in low
    assert "ollama" not in low
    assert "chat.completions" not in low
    assert "self_score" not in low
    assert "gateway.complete" not in low
    assert "llm_gateway" not in low


def test_extract_application_items_from_wiki_section():
    body = """---
title: Application Jobs
---

# Construction: Standing Jobs

## Outline
- Jobs

## Application
- Task: Apply standing Jobs to resurface a quiz miss end-to-end.
  Expected: Mint a standing Job from retention and park HITL when verify fails after replans.
  Concepts: standing Job, HITL park, bounded replan, mastery
- Exercise: What happens on pass?
  Reference: Pass advances the mastery ledger
  Concepts: pass, mastery ledger
"""
    items = extract_application_items_from_note(
        body,
        wiki_path="00_Inbox/application-jobs.md",
        topic="Standing Jobs",
    )
    assert len(items) >= 2
    assert items[0]["kind"] == APPLICATION_KIND
    assert items[0]["item_id"].startswith("app_")
    assert "standing job" in " ".join(items[0]["required_concepts"])
    assert items[0]["expected_answer"]


def test_pass_advances_mastery_ledger(tmp_path):
    repo = _repo(tmp_path)
    now = datetime(2026, 9, 11, 21, 0, 0, tzinfo=timezone.utc)
    item = {
        "item_id": "app_pass_1",
        "topic": "Jobs",
        "wiki_path": "notes/jobs.md",
        "prompt": "Apply standing Jobs to resurface a miss.",
        "expected_answer": "standing Job HITL park mastery",
        "required_concepts": ["standing Job", "HITL park", "mastery"],
    }
    result = grade_and_record_application(
        repo=repo,
        item=item,
        given="I used a standing Job, HITL park on fail, and mastery advanced on pass.",
        wiki_store=None,
        now=now,
        write_wiki=False,
        write_memory=True,
        mint_on_fail=False,
    )
    assert result["correct"] is True
    assert result["grade"] == "pass"
    assert result["action"] == "advance_mastery"
    assert result["grader"] == "binary_external_application"
    row = repo.get_education_mastery("app_pass_1")
    assert row["pass_count"] >= 1
    assert row["grade"] == "pass"


def test_fail_updates_ledger_and_can_mint_exercise_job(tmp_path):
    repo = _repo(tmp_path)
    now = datetime(2026, 9, 11, 21, 0, 0, tzinfo=timezone.utc)
    item = {
        "item_id": "app_fail_1",
        "topic": "Jobs",
        "wiki_path": "notes/jobs.md",
        "prompt": "Apply standing Jobs.",
        "expected_answer": "standing Job HITL park",
        "required_concepts": ["standing Job", "HITL park", "bounded replan"],
    }

    class FakeOrch:
        def __init__(self):
            self.jobs = []

        def create_job_from_catalog_resolve(self, **kwargs):
            jid = f"job_app_{len(self.jobs)+1:04d}"
            self.jobs.append({"id": jid, **kwargs})
            return {"id": jid}

    orch = FakeOrch()
    result = grade_and_record_application(
        repo=repo,
        item=item,
        given="toast reminder only",
        wiki_store=None,
        orch=orch,
        now=now,
        write_wiki=False,
        write_memory=True,
        mint_on_fail=True,
    )
    assert result["correct"] is False
    assert result["grade"] == "miss"
    assert result["action"] == "resurface_job"
    assert result["fail_path"]["job_id"] in result["fail_path"]["job_id"]
    row = repo.get_education_mastery("app_fail_1")
    assert row["miss_count"] >= 1
    assert row["pending_job_id"]
    assert orch.jobs
    assert "Application" in orch.jobs[0]["intent"] or "Exercise" in orch.jobs[0]["intent"]


def test_fail_with_phase_uses_bounded_replan_then_park():
    """Reuse CARD-232 apply_bounded_replan_on_failed [REQ-EDU-APP-002]."""

    class FakePhase:
        def __init__(self, pid, jid):
            self.id = pid
            self.job_id = jid
            self.status = type("S", (), {"value": "running"})()
            self.success_rule = "verify application exercise"
            self.verify_checker = "pytest"

    class FakeJob:
        def __init__(self, jid):
            self.id = jid
            self.agent_id = "assistant"
            self.success_rule = "verify application exercise"
            self.current_phase_id = "ph1"

    class FakeStore:
        def __init__(self):
            self.phase = FakePhase("ph1", "job1")
            self.job = FakeJob("job1")

        def get_phase(self, phase_id):
            return self.phase

        def get_job(self, job_id):
            return self.job

    class FakeOrch:
        def __init__(self):
            self._store = FakeStore()
            self.parked = []
            self.replanned = []
            self.checkpoints = []

        def get_latest_checkpoint(self, job_id):
            if self.checkpoints:
                return self.checkpoints[-1]
            return {"replan_count": 0}

        def matched_capability_ids_for_job(self, job_id):
            return ["skill.education-application"]

        def replan_job(self, job_id, specs):
            self.replanned.append((job_id, specs))
            self._store.job.current_phase_id = "ph_replan"
            self._store.phase = FakePhase("ph_replan", job_id)
            return self._store.job

        def park_phase(self, phase_id, *, verifier_status="failed"):
            self.parked.append((phase_id, verifier_status))
            return self._store.job

        def _commit_checkpoint(self, phase, **kwargs):
            self.checkpoints.append({"phase_id": phase.id, **kwargs})

        def emit_journey_event(self, *a, **k):
            return None

    orch = FakeOrch()
    # First fails -> replan
    out1 = apply_application_fail_path(
        orch=orch,
        phase_id="ph1",
        fail_facts=["binary verify failed"],
    )
    assert out1["action"] == "replan"
    assert out1["needs_replan"] is True
    assert orch.replanned

    # Exhaust replans -> park
    orch.checkpoints = [{"replan_count": MAX_REPLAN_ATTEMPTS}]
    orch._store.phase = FakePhase("ph1", "job1")
    out2 = apply_application_fail_path(
        orch=orch,
        phase_id="ph1",
        replan_count=MAX_REPLAN_ATTEMPTS,
        fail_facts=["binary verify failed again"],
    )
    assert out2["action"] == "park"
    assert out2["replan_exhausted"] is True
    assert orch.parked


def test_mint_exercise_job_prefers_standing_job(tmp_path):
    repo = _repo(tmp_path)
    item = {
        "item_id": "app_mint_1",
        "topic": "Application",
        "wiki_path": "00_Inbox/app.md",
        "prompt": "Apply bounded replan on fail.",
        "expected_answer": "bounded replan HITL park",
        "required_concepts": ["bounded replan", "HITL park"],
    }

    class FakeOrch:
        def create_job_from_catalog_resolve(self, **kwargs):
            return {"id": "job_exercise_1", **kwargs}

    result = mint_exercise_job(
        orch=FakeOrch(),
        memory_repo=repo,
        item=item,
        agent_id="assistant",
    )
    assert result["success"] is True
    assert result["job_id"] == "job_exercise_1"
    row = repo.get_education_mastery("app_mint_1")
    assert row["pending_job_id"] == "job_exercise_1"
    intent = build_exercise_job_intent(item)
    assert "Exercise Job" in intent
    assert "binary external" in intent.lower()


class _FakeWiki:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def seed(self, rel: str, body: str):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")

    def append_note(self, relative_path: str, content: str, heading=None):
        from src.domain.wiki.store import WikiStore

        store = WikiStore(root_dir=self.root)
        return store.append_note(relative_path, content, heading=heading)

    def read_text(self, relative_path: str) -> str:
        return (self.root / relative_path).read_text(encoding="utf-8")


def test_wiki_and_memory_writeback_on_application(tmp_path):
    repo = _repo(tmp_path)
    wiki_root = tmp_path / "wiki"
    wiki = _FakeWiki(wiki_root)
    rel = "00_Inbox/card246_application.md"
    wiki.seed(
        rel,
        "---\ntitle: Application\n---\n\n# Application\n\n## Application\n"
        "- Task: Apply standing Jobs on fail.\n"
        "  Expected: bounded replan then HITL park\n"
        "  Concepts: standing Job, bounded replan, HITL park\n",
    )
    items = extract_application_items_from_note(
        wiki.read_text(rel), wiki_path=rel, topic="Jobs"
    )
    assert items
    item = items[0]
    now = datetime(2026, 9, 11, 21, 30, 0, tzinfo=timezone.utc)
    result = grade_and_record_application(
        repo=repo,
        item=item,
        given="wrong fluff without required ideas",
        wiki_store=wiki,
        now=now,
        write_wiki=True,
        write_memory=True,
        mint_on_fail=False,
    )
    assert result["correct"] is False
    assert result["wiki_writeback"].get("success") is True
    body = wiki.read_text(rel)
    assert "Application outcomes" in body
    assert item["item_id"] in body
    assert "grade=miss" in body
    facts = list(repo.list_facts_for_entity(APPLICATION_ENTITY) or [])
    assert any(f.get("attribute") == "application_outcome" for f in facts)
    assert all(f.get("category") == APPLICATION_CATEGORY for f in facts)


def test_write_application_memory_fact_direct(tmp_path):
    repo = _repo(tmp_path)
    item = {"item_id": "app_direct", "topic": "T", "prompt": "P"}
    fid = write_application_memory_fact(
        repo, item=item, correct=True, given="good", fail_action="advance_mastery"
    )
    assert fid
    facts = repo.list_facts_for_entity(APPLICATION_ENTITY)
    assert any(fid == f.get("id") for f in facts)
