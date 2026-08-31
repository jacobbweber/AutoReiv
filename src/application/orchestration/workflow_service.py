"""
Workflow recipes [CARD-123].
Save a Goal-planned Job's chapter list (not instance facts). Instantiate as a new Job + Phase rows.
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from src.domain.orchestration.models import Job, Phase, PhaseSpec, utc_now
from src.domain.orchestration.workflow import (
    Workflow,
    WorkflowChapter,
    WorkflowChapterKind,
)
from src.infrastructure.memory.repositories.workflows import WorkflowStore, new_workflow_id


def chapters_from_job(job: Job, phases: Sequence[Phase]) -> List[WorkflowChapter]:
    """
    Persist the chapter list: who, skill vs handoff, done-when.
    Do not copy input_packet_json / chat transcript / person-specific facts.
    """
    owner = (job.agent_id or "").strip()
    ordered = sorted(phases, key=lambda p: p.index)
    chapters: List[WorkflowChapter] = []
    for phase in ordered:
        assigned = (phase.assigned_agent_id or owner).strip() or owner
        is_handoff = bool(assigned) and bool(owner) and assigned != owner
        chapters.append(
            WorkflowChapter(
                name=phase.name or f"Phase {phase.index + 1}",
                kind=WorkflowChapterKind.HANDOFF if is_handoff else WorkflowChapterKind.SKILL,
                assigned_agent_id=assigned,
                skill_id=None,
                handoff_target_agent_id=assigned if is_handoff else None,
                success_rule=phase.success_rule or "",
            )
        )
    return chapters


def phase_specs_from_workflow(workflow: Workflow, fallback_agent_id: str) -> List[PhaseSpec]:
    """Map saved chapters to linear PhaseSpecs. No graph edges. No instance facts."""
    specs: List[PhaseSpec] = []
    owner = (workflow.owner_agent_id or fallback_agent_id).strip()
    for chapter in workflow.chapters:
        assigned = (chapter.assigned_agent_id or owner).strip() or owner
        if chapter.kind == WorkflowChapterKind.HANDOFF and chapter.handoff_target_agent_id:
            assigned = chapter.handoff_target_agent_id.strip() or assigned
        specs.append(
            PhaseSpec(
                name=chapter.name,
                success_rule=chapter.success_rule or "",
                assigned_agent_id=assigned,
            )
        )
    if not specs:
        specs.append(PhaseSpec(name="Chat", success_rule="", assigned_agent_id=owner))
    return specs


def save_job_as_workflow(
    store: WorkflowStore,
    job: Job,
    phases: Sequence[Phase],
    name: str,
    *,
    owner_agent_id: Optional[str] = None,
) -> Workflow:
    owner = (owner_agent_id or job.agent_id or "").strip()
    if not owner:
        raise ValueError("Workflow requires an owner agent.")
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("Workflow name is required.")
    chapters = chapters_from_job(job, phases)
    if not chapters:
        raise ValueError("Cannot save a workflow with no chapters.")
    now = utc_now()
    workflow = Workflow(
        id=new_workflow_id(),
        name=cleaned,
        owner_agent_id=owner,
        chapters=chapters,
        created_at=now,
        updated_at=now,
    )
    return store.save(workflow)


def instantiate_workflow(
    store: WorkflowStore,
    orchestrator: Any,
    *,
    owner_agent_id: str,
    workflow_id: str,
    goal: str,
    session_id: str,
) -> Job:
    workflow = store.get(owner_agent_id, workflow_id)
    if workflow is None:
        raise KeyError(f"Workflow '{workflow_id}' not found for agent '{owner_agent_id}'.")
    specs = phase_specs_from_workflow(workflow, owner_agent_id)
    return orchestrator.create_job_with_phases(
        goal=goal,
        session_id=session_id,
        agent_id=owner_agent_id,
        phase_specs=specs,
        template_id=workflow.id,
    )
