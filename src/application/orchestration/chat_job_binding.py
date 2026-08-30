"""
Bind chat turns to persisted Job/Phase records
[REQ-ORCH-035, REQ-ORCH-039, REQ-ORCH-040, REQ-ORCH-041].
"""

from typing import Any, List, Optional, Sequence

from src.domain.orchestration.models import (
    FOLLOWUP_JOB_TEMPLATE_ID,
    HandoffPacket,
    Job,
    JobStatus,
    Phase,
    PhaseSpec,
)
from src.domain.planning.models import ExecutionPlan

_OPEN_JOB = {JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.WAITING_APPROVAL}


def phase_specs_from_plan(
    plan: ExecutionPlan,
    *,
    verify_checker: Optional[str] = None,
) -> List[PhaseSpec]:
    """Map ExecutionPlan DTO steps to linear PhaseSpecs. No graph edges."""
    specs: List[PhaseSpec] = []
    for step in plan.steps:
        specs.append(
            PhaseSpec(
                name=step.title or f"Phase {len(specs) + 1}",
                success_rule=step.description or step.title or "",
                assigned_agent_id=plan.agent_id,
                verify_checker=verify_checker,
            )
        )
    if not specs:
        specs.append(
            PhaseSpec(
                name="Chat",
                success_rule=plan.goal,
                assigned_agent_id=plan.agent_id,
                verify_checker=verify_checker,
            )
        )
    return specs


def persist_plan_as_job(
    orchestrator: Any,
    plan: ExecutionPlan,
    *,
    verify_checker: Optional[str] = None,
) -> Job:
    """Persist planner output as Job+Phases. This is the Goal-mode store [REQ-ORCH-040]."""
    return orchestrator.create_job_with_phases(
        goal=plan.goal,
        session_id=plan.session_id,
        agent_id=plan.agent_id,
        phase_specs=phase_specs_from_plan(plan, verify_checker=verify_checker),
    )


def latest_open_job_for_session(store: Any, session_id: str) -> Optional[Job]:
    lister = getattr(store, "list_jobs_for_session", None)
    if not callable(lister):
        return None
    jobs: Sequence[Job] = lister(session_id) or []
    for job in jobs:
        if getattr(job, "template_id", None) == FOLLOWUP_JOB_TEMPLATE_ID:
            # Draft/approved follow-ups stay queued until an explicit start.
            # HITL approve must not auto-pick them via resume [REQ-ORCH-043].
            continue
        status = job.status if isinstance(job.status, JobStatus) else JobStatus(str(job.status))
        if status in _OPEN_JOB:
            return job
    return None


def latest_job_for_session(store: Any, session_id: str) -> Optional[Job]:
    lister = getattr(store, "list_jobs_for_session", None)
    if not callable(lister):
        return None
    jobs: Sequence[Job] = lister(session_id) or []
    return jobs[0] if jobs else None


def output_packet_for_phase(
    phase: Phase,
    content: str,
    extra_facts: Optional[List[str]] = None,
) -> HandoffPacket:
    facts = list(extra_facts or [])
    trimmed = (content or "").strip()
    if trimmed:
        facts.append(trimmed[:2000])
    return HandoffPacket(
        goal=phase.success_rule or phase.name or "",
        facts=facts,
        constraints=[],
        done_when=phase.success_rule or "",
        budget={},
    )


def verify_skip_fact() -> str:
    return "verify_checker: skipped (none configured)"


def phase_assignment_prompt(job: Job, phase: Phase, phase_count: int, prior: Sequence[str]) -> str:
    prior_block = "\n".join(prior) if prior else "None (first phase)"
    return (
        f"You are executing phase {phase.index + 1}/{phase_count} of the goal: '{job.goal}'.\n"
        f"PHASE: {phase.name}\n"
        f"SUCCESS RULE: {phase.success_rule or phase.name}\n"
        f"PRIOR PHASE OUTPUTS:\n{prior_block}"
    )
