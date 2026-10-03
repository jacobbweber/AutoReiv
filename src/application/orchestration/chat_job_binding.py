"""
Bind chat turns to persisted Job/Phase records
[REQ-ORCH-035, REQ-ORCH-039, REQ-ORCH-040, REQ-ORCH-041].
"""

import re
from typing import Any, List, Optional, Sequence

from src.application.orchestration.kill_resume import job_waiting_for_answer
from src.application.orchestration.session_activity import is_job_step_session, parent_session_id
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


def job_waiting_for_answer_on_session(store: Any, session_id: str) -> Optional[Job]:
    """CARD-613: the chat's open job when its step is waiting for Jacob's answer, else None."""
    job = latest_open_job_for_session(store, session_id)
    return job if job is not None and job_waiting_for_answer(store, job) else None


WAITING_FOR_ANSWER_NOTE = "The job is waiting for your answer. Reply here and the step continues."

_PARK_NOTE = re.compile(r"Job (\S+) is waiting for operator approval during (.+?)\. Approve or reject above to continue execution\.")


def park_note(job_id: str, phase_name: str) -> str:
    """CARD-343: the chat line saved when a job step parks on an approval card."""
    return f"Job {job_id} is waiting for operator approval during {phase_name}. Approve or reject above to continue execution."


def settle_park_note(store: Any, approval_session_id: str, decision: str) -> bool:
    """CARD-617: once a job step's card is decided (in the chat or through the API), its park note says so.

    The note used to keep saying "Approve or reject above" after an API decision left the job stopped.
    """
    if not is_job_step_session(approval_session_id):
        return False
    verb = "approved" if str(decision or "").strip().lower() in {"approved", "approve"} else "rejected"
    origin = parent_session_id(approval_session_id)
    for message in reversed((store.get_messages(session_id=origin) or [])[-30:]):
        role = str(getattr(getattr(message, "role", ""), "value", getattr(message, "role", ""))).lower()
        content = str(getattr(message, "content", "") or "")
        if role != "assistant" or not _PARK_NOTE.search(content) or not getattr(message, "id", None):
            continue
        settled = _PARK_NOTE.sub(lambda m: f"Job {m.group(1)} paused for approval during {m.group(2)}; the card was {verb}.", content)
        return bool(store.update_message(message.id, settled))
    return False


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
    return "verify_status: skipped_no_checker"


def phase_assignment_prompt(job: Job, phase: Phase, phase_count: int, prior: Sequence[str]) -> str:
    """Legacy prompt helper.

    Standing Chat/Routines should prefer `format_phase_working_set_prompt` /
    `build_phase_working_set` [CARD-229]. Prior lines are distilled to durable
    notes (tool dumps stripped) so accidental callers stay aligned with M12.
    """
    from src.application.orchestration.working_set_context import (
        distill_durable_note,
        strip_tool_dumps,
    )

    notes: list[str] = []
    for i, line in enumerate(prior or []):
        raw = str(line or "").strip()
        if not raw:
            continue
        cleaned = strip_tool_dumps(raw)
        if cleaned.startswith("Phase ") and len(cleaned) <= 480:
            notes.append(cleaned)
        else:
            notes.append(
                distill_durable_note(
                    phase_name=f"prior_{i}",
                    phase_index=max(0, phase.index - 1),
                    raw_output=cleaned,
                )
            )
    prior_block = "\n".join(notes) if notes else "None (first phase)"
    return (
        f"You are executing phase {phase.index + 1}/{phase_count} of the goal: '{job.goal}'.\n"
        f"PHASE: {phase.name}\n"
        f"SUCCESS RULE: {phase.success_rule or phase.name}\n"
        f"PRIOR PHASE DURABLE NOTES:\n{prior_block}"
    )
