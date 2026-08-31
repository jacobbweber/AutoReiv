"""CARD-123: save a Goal phase list as a workflow and instantiate it."""

import json
import os
import tempfile

import pytest

from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.workflow_service import (
    chapters_from_job,
    instantiate_workflow,
    save_job_as_workflow,
)
from src.domain.orchestration.models import HandoffPacket, PhaseSpec
from src.domain.orchestration.workflow import WorkflowChapterKind
from src.infrastructure.memory.repositories.workflows import WorkflowStore
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.fixture
def orch(temp_db_path):
    store = SQLiteStateStore(db_path=temp_db_path)
    return JobPhaseOrchestrator(store)


@pytest.fixture
def agents_root(tmp_path):
    root = tmp_path / "agents"
    root.mkdir()
    return root


def _goal_job(orch, goal="Onboard Jane Doe jane@example.com"):
    packet = HandoffPacket(
        goal=goal,
        facts=["email: jane@example.com", "name: Jane Doe"],
        constraints=[],
        done_when="Account exists",
        budget={"max_turns": 10},
    )
    job = orch.create_job_with_phases(
        goal=goal,
        session_id="sess_jane",
        agent_id="assistant",
        phase_specs=[
            PhaseSpec(name="Create account", success_rule="Account exists", assigned_agent_id="assistant"),
            PhaseSpec(name="Assign laptop", success_rule="Laptop assigned", assigned_agent_id="assistant"),
            PhaseSpec(
                name="Grant apps",
                success_rule="Apps granted",
                assigned_agent_id="okta-admin",
            ),
        ],
    )
    phases = orch._store.list_phases_for_job(job.id)
    phases[0].input_packet_json = packet.model_dump_json()
    orch._store.update_phase(phases[0])
    return job, orch._store.list_phases_for_job(job.id)


def test_empty_store_lists_nothing(agents_root):
    store = WorkflowStore(agents_root)
    assert store.list_for_agent("assistant") == []


def test_save_goal_phase_list_persists_chapters_not_instance_facts(orch, agents_root):
    job, phases = _goal_job(orch)
    store = WorkflowStore(agents_root)
    workflow = save_job_as_workflow(store, job, phases, "new-employee-onboarding")

    assert workflow.owner_agent_id == "assistant"
    assert workflow.name == "new-employee-onboarding"
    assert [c.name for c in workflow.chapters] == ["Create account", "Assign laptop", "Grant apps"]
    assert [c.success_rule for c in workflow.chapters] == [
        "Account exists",
        "Laptop assigned",
        "Apps granted",
    ]
    assert workflow.chapters[0].kind == WorkflowChapterKind.SKILL
    assert workflow.chapters[2].kind == WorkflowChapterKind.HANDOFF
    assert workflow.chapters[2].handoff_target_agent_id == "okta-admin"

    dumped = json.dumps(workflow.model_dump(mode="json"))
    assert "jane@example.com" not in dumped.lower()
    assert "Jane Doe" not in dumped
    assert "input_packet_json" not in dumped
    assert "sess_jane" not in dumped

    on_disk = store.get("assistant", workflow.id)
    assert on_disk is not None
    disk_text = (agents_root / "assistant" / "workflows" / f"{workflow.id}.json").read_text(encoding="utf-8")
    assert "jane@example.com" not in disk_text.lower()
    assert "Create account" in disk_text


def test_instantiate_creates_job_with_those_phases(orch, agents_root):
    job, phases = _goal_job(orch)
    store = WorkflowStore(agents_root)
    workflow = save_job_as_workflow(store, job, phases, "new-employee-onboarding")

    new_job = instantiate_workflow(
        store,
        orch,
        owner_agent_id="assistant",
        workflow_id=workflow.id,
        goal="Onboard Bob Smith bob@example.com",
        session_id="sess_bob",
    )
    new_phases = orch._store.list_phases_for_job(new_job.id)
    assert new_job.template_id == workflow.id
    assert new_job.goal == "Onboard Bob Smith bob@example.com"
    assert new_job.session_id == "sess_bob"
    assert [p.name for p in new_phases] == ["Create account", "Assign laptop", "Grant apps"]
    assert [p.assigned_agent_id for p in new_phases] == ["assistant", "assistant", "okta-admin"]
    assert [p.success_rule for p in new_phases] == ["Account exists", "Laptop assigned", "Apps granted"]
    # New instance facts live on the job/packets, not on the recipe.
    recipe = store.get("assistant", workflow.id)
    recipe_text = json.dumps(recipe.model_dump(mode="json"))
    assert "bob@example.com" not in recipe_text.lower()
    assert "Jane Doe" not in recipe_text


def test_chapters_from_job_ignore_packet_blobs(orch):
    job, phases = _goal_job(orch)
    chapters = chapters_from_job(job, phases)
    blob = json.dumps([c.model_dump() for c in chapters])
    assert "jane@example.com" not in blob
    assert "facts" not in blob
