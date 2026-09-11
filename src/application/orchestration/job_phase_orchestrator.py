"""
JobPhaseOrchestrator [REQ-ORCH-034].
Owns Job/Phase records and linear transitions. Does not call the LLM.
Kernel wiring is CARD-097 / CARD-099.
"""

import logging
import uuid
from typing import Any, List, Mapping, Optional, Sequence, Union

from src.application.orchestration.crash_resume import (
    CrashResumeResult,
    verifier_status_from_facts,
)
from src.domain.orchestration.errors import InvalidPhaseTransitionError
from src.domain.orchestration.models import (
    HandoffPacket,
    Job,
    JobPhaseCheckpoint,
    JobStatus,
    Phase,
    PhaseSpec,
    PhaseStatus,
    ReactState,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)

_TERMINAL_PHASE = {PhaseStatus.DONE, PhaseStatus.FAILED, PhaseStatus.CANCELLED}
_TERMINAL_JOB = {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED}
_STARTABLE_PHASE = {PhaseStatus.QUEUED, PhaseStatus.WAITING_APPROVAL}


def _new_job_id() -> str:
    return f"job_{uuid.uuid4().hex[:12]}"


def _new_phase_id() -> str:
    return f"phase_{uuid.uuid4().hex[:12]}"


def _as_phase_spec(item: Union[PhaseSpec, Mapping[str, Any]]) -> PhaseSpec:
    if isinstance(item, PhaseSpec):
        return item
    return PhaseSpec.model_validate(item)


def _default_packet(
    goal: str,
    success_rule: str,
    max_turns: int,
    max_handoffs: int,
    max_ollama_slots: int,
) -> HandoffPacket:
    return HandoffPacket(
        goal=goal,
        facts=[],
        constraints=[],
        done_when=success_rule,
        budget={
            "max_turns": max_turns,
            "max_handoffs": max_handoffs,
            "max_ollama_slots": max_ollama_slots,
        },
    )


class JobPhaseOrchestrator:
    """
    Create job -> run phase -> on DONE next or finish.
    PARKED / FAILED / waiting_approval do not auto-advance.
    """

    def __init__(self, store: SQLiteStateStore) -> None:
        self._store = store

    def create_single_phase_job(
        self,
        goal: str,
        session_id: str,
        agent_id: str,
        *,
        name: str = "Chat",
        success_rule: str = "",
        verify_checker: Optional[str] = None,
        template_id: Optional[str] = None,
        budget_max_phases: int = 16,
        budget_max_handoffs: int = 4,
        budget_max_ollama_slots: int = 1,
        max_turns: int = 10,
    ) -> Job:
        """Default chat shape: one Job, one Phase, both queued [REQ-ORCH-035 shape only]."""
        return self.create_job_with_phases(
            goal=goal,
            session_id=session_id,
            agent_id=agent_id,
            phase_specs=[
                PhaseSpec(name=name, success_rule=success_rule, assigned_agent_id=agent_id, verify_checker=verify_checker, max_turns=max_turns)
            ],
            template_id=template_id,
            budget_max_phases=budget_max_phases,
            budget_max_handoffs=budget_max_handoffs,
            budget_max_ollama_slots=budget_max_ollama_slots,
        )

    def create_job_with_phases(
        self,
        goal: str,
        session_id: str,
        agent_id: str,
        phase_specs: Sequence[Union[PhaseSpec, Mapping[str, Any]]],
        *,
        template_id: Optional[str] = None,
        budget_max_phases: int = 16,
        budget_max_handoffs: int = 4,
        budget_max_ollama_slots: int = 1,
    ) -> Job:
        specs = [_as_phase_spec(item) for item in phase_specs]
        if not specs:
            raise InvalidPhaseTransitionError("create_job_with_phases requires at least one phase spec.")

        job_id = _new_job_id()
        phases: List[Phase] = []
        for index, spec in enumerate(specs):
            assigned = spec.assigned_agent_id or agent_id
            packet = _default_packet(
                goal=goal,
                success_rule=spec.success_rule,
                max_turns=spec.max_turns,
                max_handoffs=budget_max_handoffs,
                max_ollama_slots=budget_max_ollama_slots,
            )
            phases.append(
                Phase(
                    id=_new_phase_id(),
                    job_id=job_id,
                    name=spec.name,
                    index=index,
                    assigned_agent_id=assigned,
                    status=PhaseStatus.QUEUED,
                    success_rule=spec.success_rule,
                    verify_checker=spec.verify_checker,
                    input_packet_json=packet.model_dump_json(),
                    output_packet_json=None,
                    parent_phase_id=spec.parent_phase_id,
                    max_turns=spec.max_turns,
                    react_state=None,
                )
            )

        job = Job(
            id=job_id,
            goal=goal,
            status=JobStatus.QUEUED,
            budget_max_phases=max(int(budget_max_phases), len(phases)),
            budget_max_handoffs=budget_max_handoffs,
            budget_max_ollama_slots=budget_max_ollama_slots,
            current_phase_id=phases[0].id,
            template_id=template_id,
            session_id=session_id,
            agent_id=agent_id,
        )
        persisted = self._store.create_job(job, phases)
        logger.info(
            "Created job %s with %s phase(s) current=%s",
            persisted.id,
            len(phases),
            persisted.current_phase_id,
        )
        return persisted

    def start_phase(self, phase_id: str) -> Phase:
        """queued (or parked waiting_approval) -> running. Job becomes running."""
        phase = self._store.get_phase(phase_id)
        job = self._store.get_job(phase.job_id)
        if job.status == JobStatus.CANCELLED:
            raise InvalidPhaseTransitionError(f"Cannot start phase {phase_id}: job {job.id} is cancelled.")
        if phase.status in _TERMINAL_PHASE:
            raise InvalidPhaseTransitionError(f"Cannot start phase {phase_id}: status is {phase.status.value}.")
        if phase.status not in _STARTABLE_PHASE:
            raise InvalidPhaseTransitionError(f"Cannot start phase {phase_id}: status is {phase.status.value}.")

        phase.status = PhaseStatus.RUNNING
        phase.react_state = ReactState.THINKING
        updated = self._store.update_phase(phase)
        self._store.update_job_status(job.id, JobStatus.RUNNING.value, current_phase_id=updated.id)
        logger.info("Started phase %s on job %s", updated.id, job.id)
        return updated

    def complete_phase(self, phase_id: str, output_packet: HandoffPacket) -> Optional[Phase]:
        """
        Mark phase DONE. If a later queued phase exists, set it current and return it.
        Else mark the job done. Does not auto-advance PARKED/FAILED phases.
        """
        phase = self._store.get_phase(phase_id)
        if phase.status in {PhaseStatus.FAILED, PhaseStatus.CANCELLED, PhaseStatus.WAITING_APPROVAL}:
            raise InvalidPhaseTransitionError(
                f"Cannot complete phase {phase_id}: status is {phase.status.value}; "
                "PARKED/FAILED/waiting_approval do not auto-advance."
            )
        if phase.status == PhaseStatus.QUEUED:
            raise InvalidPhaseTransitionError(f"Cannot complete phase {phase_id}: still queued.")
        if phase.status == PhaseStatus.DONE:
            return self._next_queued_phase(phase.job_id, phase.index)

        phase.status = PhaseStatus.DONE
        phase.react_state = ReactState.DONE
        phase.output_packet_json = output_packet.model_dump_json()
        self._store.update_phase(phase)
        self._commit_checkpoint(
            phase,
            verifier_status=verifier_status_from_facts(list(output_packet.facts or [])),
            hitl_park_state=False,
        )

        nxt = self._next_queued_phase(phase.job_id, phase.index)
        if nxt is None:
            self._store.update_job_status(phase.job_id, JobStatus.DONE.value, current_phase_id=phase.id)
            logger.info("Job %s done after phase %s", phase.job_id, phase.id)
            return None

        self._store.update_job_status(phase.job_id, JobStatus.RUNNING.value, current_phase_id=nxt.id)
        logger.info("Job %s advanced to phase %s (index %s)", phase.job_id, nxt.id, nxt.index)
        return nxt

    def fail_phase(self, phase_id: str, error: str) -> Job:
        """Phase FAILED, job failed. Does not start the next phase."""
        phase = self._store.get_phase(phase_id)
        packet = HandoffPacket(
            goal=phase.success_rule or "",
            facts=[error],
            constraints=[],
            done_when=phase.success_rule or "",
            budget={},
        )
        phase.status = PhaseStatus.FAILED
        phase.react_state = ReactState.FAILED
        phase.output_packet_json = packet.model_dump_json()
        self._store.update_phase(phase)
        self._commit_checkpoint(phase, verifier_status="failed", hitl_park_state=False)
        job = self._store.update_job_status(phase.job_id, JobStatus.FAILED.value, current_phase_id=phase.id)
        logger.warning("Phase %s failed on job %s: %s", phase.id, job.id, error)
        return job

    def park_phase(self, phase_id: str) -> Job:
        """HITL park: phase waiting_approval, react_state PARKED. Does not auto-advance."""
        phase = self._store.get_phase(phase_id)
        if phase.status in _TERMINAL_PHASE:
            raise InvalidPhaseTransitionError(f"Cannot park phase {phase_id}: status is {phase.status.value}.")
        phase.status = PhaseStatus.WAITING_APPROVAL
        phase.react_state = ReactState.PARKED
        self._store.update_phase(phase)
        self._commit_checkpoint(phase, verifier_status="none", hitl_park_state=True)
        job = self._store.update_job_status(
            phase.job_id,
            JobStatus.WAITING_APPROVAL.value,
            current_phase_id=phase.id,
        )
        logger.info("Parked phase %s on job %s", phase.id, job.id)
        return job

    def cancel_job(self, job_id: str) -> Job:
        """Cancel the job and every non-terminal phase. Does not start remaining work."""
        job = self._store.get_job(job_id)
        if job.status in _TERMINAL_JOB and job.status != JobStatus.CANCELLED:
            raise InvalidPhaseTransitionError(f"Cannot cancel job {job_id}: status is {job.status.value}.")
        for phase in self._store.list_phases_for_job(job_id):
            if phase.status in _TERMINAL_PHASE:
                continue
            phase.status = PhaseStatus.CANCELLED
            self._store.update_phase(phase)
        updated = self._store.update_job_status(job_id, JobStatus.CANCELLED.value, current_phase_id=job.current_phase_id)
        logger.info("Cancelled job %s", job_id)
        return updated


    def replan_job(
        self,
        job_id: str,
        phase_specs: Sequence[Union[PhaseSpec, Mapping[str, Any]]],
    ) -> Job:
        """
        Replace non-DONE remaining phases with a new linear plan [REQ-JOBGRAPH-001a].
        DONE phases are kept. QUEUED/RUNNING/WAITING_APPROVAL phases are cancelled.
        """
        job = self._store.get_job(job_id)
        if job.status in _TERMINAL_JOB:
            raise InvalidPhaseTransitionError(
                f"Cannot replan job {job_id}: status is {job.status.value}."
            )
        specs = [_as_phase_spec(item) for item in phase_specs]
        if not specs:
            raise InvalidPhaseTransitionError("replan_job requires at least one phase spec.")

        existing = self._store.list_phases_for_job(job_id)
        done_phases = [p for p in existing if p.status == PhaseStatus.DONE]
        # Indices are unique per job; cancelled rows retain theirs, so append after max.
        max_index = max((p.index for p in existing), default=-1)

        for phase in existing:
            if phase.status == PhaseStatus.DONE or phase.status in _TERMINAL_PHASE:
                continue
            phase.status = PhaseStatus.CANCELLED
            phase.react_state = None
            self._store.update_phase(phase)

        new_ids: List[str] = []
        for offset, spec in enumerate(specs):
            assigned = spec.assigned_agent_id or job.agent_id
            packet = _default_packet(
                goal=job.goal,
                success_rule=spec.success_rule,
                max_turns=spec.max_turns,
                max_handoffs=job.budget_max_handoffs,
                max_ollama_slots=job.budget_max_ollama_slots,
            )
            phase = Phase(
                id=_new_phase_id(),
                job_id=job_id,
                name=spec.name,
                index=max_index + 1 + offset,
                assigned_agent_id=assigned,
                status=PhaseStatus.QUEUED,
                success_rule=spec.success_rule,
                verify_checker=spec.verify_checker,
                input_packet_json=packet.model_dump_json(),
                output_packet_json=None,
                parent_phase_id=spec.parent_phase_id,
                max_turns=spec.max_turns,
                react_state=None,
            )
            created = self._store.create_phase(phase)
            new_ids.append(created.id)

        refreshed = self._store.get_job(job_id)
        refreshed.budget_max_phases = max(
            int(refreshed.budget_max_phases),
            len(self._store.list_phases_for_job(job_id)),
        )
        refreshed.current_phase_id = new_ids[0]
        refreshed.status = JobStatus.RUNNING if done_phases else JobStatus.QUEUED
        updated = self._store.update_job(refreshed)
        logger.info(
            "Replanned job %s with %s new phase(s); current=%s",
            job_id,
            len(new_ids),
            updated.current_phase_id,
        )
        return updated

    def _commit_checkpoint(
        self,
        phase: Phase,
        *,
        verifier_status: str,
        hitl_park_state: bool = False,
    ) -> JobPhaseCheckpoint:
        """Durable on-disk checkpoint after a phase commit [REQ-RESUME-001]."""
        saver = getattr(self._store, "save_job_phase_checkpoint", None)
        if not callable(saver):
            raise RuntimeError("Store does not support job_phase_checkpoints")
        cp = saver(
            job_id=phase.job_id,
            phase_id=phase.id,
            phase_index=int(phase.index),
            verifier_status=verifier_status,
            hitl_park_state=hitl_park_state,
        )
        logger.info(
            "Checkpoint job=%s phase_index=%s verifier=%s park=%s",
            phase.job_id,
            phase.index,
            verifier_status,
            hitl_park_state,
        )
        return cp

    def get_latest_checkpoint(self, job_id: str) -> JobPhaseCheckpoint | None:
        getter = getattr(self._store, "get_latest_job_phase_checkpoint", None)
        if not callable(getter):
            return None
        return getter(job_id)

    def resume_after_crash(self, job_id: str) -> CrashResumeResult:
        """
        LangGraph-style continue from last durable checkpoint [REQ-RESUME-002].

        - Missing/corrupt checkpoint => needs_replan (replan-from-zero only then).
        - Interrupted RUNNING phase is re-queued so the same job_id can advance.
        """
        try:
            job = self._store.get_job(job_id)
        except Exception as exc:  # noqa: BLE001 - fail closed to replan
            return CrashResumeResult(
                ok=False,
                needs_replan=True,
                resumed_from_checkpoint=False,
                reason=f"job missing: {exc}",
            )

        checkpoint = self.get_latest_checkpoint(job_id)
        if checkpoint is None or checkpoint.corrupt:
            return CrashResumeResult(
                job=job,
                checkpoint=checkpoint,
                ok=False,
                needs_replan=True,
                resumed_from_checkpoint=False,
                reason="checkpoint corrupt or missing",
            )

        phases = self._store.list_phases_for_job(job_id)
        interrupted = next((p for p in phases if p.status == PhaseStatus.RUNNING), None)
        parked = next((p for p in phases if p.status == PhaseStatus.WAITING_APPROVAL), None)

        # Only crash/HITL recovery surfaces resumed_from_checkpoint.
        # Ordinary queued advance after a prior commit is not a crash resume.
        if interrupted is None and parked is None:
            queued = next((p for p in phases if p.status == PhaseStatus.QUEUED), None)
            return CrashResumeResult(
                job=job,
                checkpoint=checkpoint,
                continue_phase=queued,
                ok=True,
                needs_replan=False,
                resumed_from_checkpoint=False,
                reason="open job with durable checkpoint; no interrupt to recover",
            )

        continue_phase: Phase | None = None
        if interrupted is not None:
            # Mid-phase kill: reset to queued so start_phase can re-enter.
            interrupted.status = PhaseStatus.QUEUED
            interrupted.react_state = None
            continue_phase = self._store.update_phase(interrupted)
        else:
            continue_phase = parked

        if job.status not in _TERMINAL_JOB and continue_phase is not None:
            job = self._store.update_job_status(
                job.id,
                JobStatus.WAITING_APPROVAL.value
                if continue_phase.status == PhaseStatus.WAITING_APPROVAL
                else JobStatus.RUNNING.value,
                current_phase_id=continue_phase.id,
            )
        else:
            job = self._store.get_job(job_id)

        logger.info(
            "Resumed job %s from checkpoint phase_index=%s continue=%s",
            job_id,
            checkpoint.phase_index,
            continue_phase.id if continue_phase else None,
        )
        return CrashResumeResult(
            job=job,
            checkpoint=checkpoint,
            continue_phase=continue_phase,
            ok=True,
            needs_replan=False,
            resumed_from_checkpoint=True,
            reason="continued from durable checkpoint after interrupt",
        )

    def _next_queued_phase(self, job_id: str, after_index: int) -> Optional[Phase]:
        for phase in self._store.list_phases_for_job(job_id):
            if phase.index > after_index and phase.status == PhaseStatus.QUEUED:
                return phase
        return None
