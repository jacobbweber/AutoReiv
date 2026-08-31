"""
JobPhaseOrchestrator [REQ-ORCH-034].
Owns Job/Phase records and linear transitions. Does not call the LLM.
Kernel wiring is CARD-097 / CARD-099.
"""

import logging
import uuid
from typing import Any, List, Mapping, Optional, Sequence, Union

from src.domain.orchestration.errors import InvalidPhaseTransitionError
from src.domain.orchestration.models import (
    HandoffPacket,
    Job,
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

    def _next_queued_phase(self, job_id: str, after_index: int) -> Optional[Phase]:
        for phase in self._store.list_phases_for_job(job_id):
            if phase.index > after_index and phase.status == PhaseStatus.QUEUED:
                return phase
        return None
