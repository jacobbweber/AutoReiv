"""
JobPhaseOrchestrator [REQ-ORCH-034 / CARD-220].
Owns Job/Phase records and linear transitions. Does not call the LLM.
Kernel wiring is CARD-097 / CARD-099.
Standing catalog resolve: intent → matched subset → Research/Handoff/Execute.
"""

import logging
import uuid
from pathlib import Path
from typing import Any, List, Mapping, Optional, Sequence, Union

from src.application.capabilities.resolver import CapabilityCatalogResolver, ResolveResult
from src.application.orchestration.crash_resume import (
    verifier_status_from_facts,
)
from src.application.orchestration.job_recovery import (
    _PHASE_RUN_TOKENS as _PHASE_RUN_TOKENS,
)
from src.application.orchestration.job_recovery import (
    JobRecoveryMixin,
)
from src.application.orchestration.job_recovery import (
    _ticks_coding as _ticks_coding,
)
from src.application.orchestration.job_recovery import (
    resolve_specialist_agent_for_capabilities as resolve_specialist_agent_for_capabilities,
)
from src.application.orchestration.kill_resume import (
    WAITING_FOR_ANSWER_REASON,
)
from src.application.orchestration.outcome_intake import (
    OutcomeIntakeError,
    assert_intake_ready_for_phase1,
    derive_success_rule,
    is_testable_success_rule,
    is_vibes_only_success_rule,
    matched_ids_authority,
)
from src.application.orchestration.research_before_plan import (
    assess_catalog_match,
    run_standing_research,
)
from src.domain.kernel.models import DEFAULT_AGENT_MAX_TURNS
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


class JobPhaseOrchestrator(JobRecoveryMixin):
    """
    Create job -> run phase -> on DONE next or finish.
    PARKED / FAILED / waiting_approval do not auto-advance.
    """

    def __init__(
        self,
        store: SQLiteStateStore,
        capability_resolver: Optional[CapabilityCatalogResolver] = None,
        data_dir: Optional[Union[str, Path]] = None,
        skill_catalog: Optional[Any] = None,
    ) -> None:
        self._store = store
        self._capability_resolver = capability_resolver
        self._data_dir = data_dir
        self._skill_catalog = skill_catalog
        # job_id -> matched capability ids locked at formulate time [REQ-CATJOB-002]
        self._matched_ids: dict[str, list[str]] = {}
        # phase_id -> last bound skill id (progressive; one body at a time) [CARD-228]
        self._bound_skills: dict[str, str] = {}

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
        budget_max_phases: int = 256,  # CARD-592 (was 16)
        budget_max_handoffs: int = 64,  # CARD-592 (was 4)
        budget_max_ollama_slots: int = 1,
        max_turns: int = DEFAULT_AGENT_MAX_TURNS,
    ) -> Job:
        """Default chat shape: one Job, one Phase, both queued [REQ-ORCH-035 shape only]."""
        return self.create_job_with_phases(
            goal=goal,
            session_id=session_id,
            agent_id=agent_id,
            phase_specs=[
                PhaseSpec(
                    name=name,
                    success_rule=success_rule,
                    assigned_agent_id=agent_id,
                    verify_checker=verify_checker,
                    max_turns=max_turns,
                )
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
        budget_max_phases: int = 256,  # CARD-592 (was 16)
        budget_max_handoffs: int = 64,  # CARD-592 (was 4)
        budget_max_ollama_slots: int = 1,
        success_rule: str = "",
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
            success_rule=success_rule or "",
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
        if int(getattr(phase, "index", 0) or 0) == 0:
            template = getattr(job, "template_id", None) or ""
            matched = self.matched_capability_ids_for_job(job.id)
            rule = getattr(job, "success_rule", "") or ""
            standing_intake = (
                template == "catalog_resolve_rhe"
                or str(template).startswith("catalog_")
                or bool(rule.strip())
                or bool(matched)
            )
            if standing_intake:
                cp = self.get_latest_checkpoint(job.id)
                is_research = str(getattr(phase, "name", "") or "").lower().startswith(
                    "research"
                )
                research_gap_ok = (
                    is_research
                    and cp is not None
                    and bool(getattr(cp, "research_inserted", False))
                    and bool(rule.strip())
                )
                if research_gap_ok:
                    if is_vibes_only_success_rule(rule) or not is_testable_success_rule(
                        rule
                    ):
                        raise OutcomeIntakeError(
                            f"fail-closed: success_rule not testable before research: {rule!r}"
                        )
                else:
                    assert_intake_ready_for_phase1(
                        success_rule=rule,
                        matched_capability_ids=matched,
                    )
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
        _PHASE_RUN_TOKENS[updated.id] = uuid.uuid4().hex
        logger.info("Started phase %s on job %s", updated.id, job.id)
        return updated

    def complete_phase(
        self,
        phase_id: str,
        output_packet: HandoffPacket,
        *,
        advance: bool = True,
    ) -> Optional[Phase]:
        """
        Mark phase DONE. If advance and a later queued phase exists, set it current.
        Else mark the job done when advance exhausts the plan.
        Does not auto-advance PARKED/FAILED phases.
        advance=False completes without moving to the next phase [REQ-CATJOB-003].
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
            return self._next_queued_phase(phase.job_id, phase.index) if advance else None

        phase.status = PhaseStatus.DONE
        phase.react_state = ReactState.DONE
        phase.output_packet_json = output_packet.model_dump_json()
        self._store.update_phase(phase)
        memory_fact_ids = self._persist_phase_memory(phase, list(output_packet.facts or []))
        self._commit_checkpoint(
            phase,
            verifier_status=verifier_status_from_facts(list(output_packet.facts or [])),
            hitl_park_state=False,
            memory_fact_ids=memory_fact_ids,
        )

        if not advance:
            self._store.update_job_status(
                phase.job_id, JobStatus.RUNNING.value, current_phase_id=phase.id
            )
            logger.info(
                "Phase %s done on job %s without advance (standing gate)",
                phase.id,
                phase.job_id,
            )
            return None

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
        self._commit_checkpoint(phase, verifier_status="failed", hitl_park_state=False, last_fail_reason=error)
        job = self._store.update_job_status(phase.job_id, JobStatus.FAILED.value, current_phase_id=phase.id)
        logger.warning("Phase %s failed on job %s: %s", phase.id, job.id, error)
        return job

    def park_phase(self, phase_id: str, *, verifier_status: str = "none") -> Job:
        """HITL park: phase waiting_approval, react_state PARKED. Does not auto-advance."""
        phase = self._store.get_phase(phase_id)
        if phase.status in _TERMINAL_PHASE:
            raise InvalidPhaseTransitionError(f"Cannot park phase {phase_id}: status is {phase.status.value}.")
        phase.status = PhaseStatus.WAITING_APPROVAL
        phase.react_state = ReactState.PARKED
        self._store.update_phase(phase)
        self._commit_checkpoint(
            phase,
            verifier_status=verifier_status or "none",
            hitl_park_state=True,
        )
        job = self._store.update_job_status(
            phase.job_id,
            JobStatus.WAITING_APPROVAL.value,
            current_phase_id=phase.id,
        )
        logger.info("Parked phase %s on job %s", phase.id, job.id)
        return job

    def wait_for_answer(self, phase_id: str) -> Job:
        """CARD-613: the step asked Jacob a question: phase back to queued (not done), job open; his reply resumes it."""
        phase = self._store.get_phase(phase_id)
        if phase.status in _TERMINAL_PHASE:
            raise InvalidPhaseTransitionError(f"Cannot wait on phase {phase_id}: status is {phase.status.value}.")
        phase.status = PhaseStatus.QUEUED
        phase.react_state = None
        phase = self._store.update_phase(phase)
        self._commit_checkpoint(phase, verifier_status="none", last_fail_reason=WAITING_FOR_ANSWER_REASON)
        job = self._store.update_job_status(phase.job_id, JobStatus.RUNNING.value, current_phase_id=phase.id)
        logger.info("Phase %s on job %s waits for the operator's answer", phase.id, job.id)
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

    def _resolve_skill_catalog(self) -> Any:
        if self._skill_catalog is not None:
            return self._skill_catalog
        if self._data_dir is None:
            return None
        from src.application.skills.user_catalog import UserSkillCatalog

        self._skill_catalog = UserSkillCatalog(skills_dir=Path(self._data_dir) / "skills")
        return self._skill_catalog

    def matched_skill_ids_for_job(self, job_id: str) -> list[str]:
        """Matched capability IDs that are skills (progressive bind candidates)."""
        out: list[str] = []
        for cid in self.matched_capability_ids_for_job(job_id):
            s = str(cid)
            if s.startswith("skill."):
                out.append(s)
                continue
            if self._capability_resolver is not None:
                get = getattr(self._capability_resolver, "_store", None)
                getter = getattr(get, "get_entry", None) if get is not None else None
                if callable(getter):
                    entry = getter(s)
                    kind = getattr(entry, "kind", None) if entry is not None else None
                    raw = kind.value if hasattr(kind, "value") else str(kind or "")
                    if raw == "skill":
                        out.append(s)
        return out

    def bind_skill_for_phase(self, phase_id: str, skill_id: str) -> dict[str, Any]:
        """Load one SKILL.md body when a phase binds/selects that skill [REQ-PSKILL-002]."""
        from src.application.capabilities.progressive_skills import load_one_skill_body

        phase = self._store.get_phase(phase_id)
        catalog = self._resolve_skill_catalog()
        loaded = load_one_skill_body(catalog, skill_id)
        payload = {
            "phase_id": phase_id,
            "job_id": phase.job_id,
            "skill_id": skill_id,
            "runbook_id": loaded.get("runbook_id"),
            "title": loaded.get("title"),
            "body_loaded": bool(loaded.get("body_loaded")),
            "success": bool(loaded.get("success")),
            "error": loaded.get("error"),
        }
        save_ev = getattr(self._store, "save_standing_journey_event", None)
        if callable(save_ev):
            save_ev(job_id=phase.job_id, kind="skill_bound", payload=payload)
        self._bound_skills[phase_id] = skill_id
        return {
            "success": bool(loaded.get("success")),
            "event": "skill_bound",
            "phase_id": phase_id,
            "job_id": phase.job_id,
            "skill_id": skill_id,
            "runbook_id": loaded.get("runbook_id"),
            "title": loaded.get("title"),
            "body": loaded.get("body") if loaded.get("success") else None,
            "body_loaded": bool(loaded.get("body_loaded")),
            "tools": loaded.get("tools") or [],
            "error": loaded.get("error"),
            "path": loaded.get("path"),
        }

    def bind_matched_skill_on_phase_start(self, phase_id: str) -> list[dict[str, Any]]:
        """Bind exactly one matched skill body for this phase — never dump-all [REQ-PSKILL-005]."""
        phase = self._store.get_phase(phase_id)
        skill_ids = self.matched_skill_ids_for_job(phase.job_id)
        if not skill_ids:
            return []
        start = phase.index % len(skill_ids)
        ordered = skill_ids[start:] + skill_ids[:start]
        last: dict[str, Any] | None = None
        for sid in ordered:
            bound = self.bind_skill_for_phase(phase_id, sid)
            last = bound
            if bound.get("success"):
                return [bound]
        return [last] if last is not None else []

    def supervisor_pick_specialist(
        self,
        phase_id: str,
        *,
        specialty: str,
        entry_meta: Optional[Mapping[str, Mapping[str, Any]]] = None,
        session_id: Optional[str] = None,
        requested_agent_id: Optional[str] = None,
        on_no_match: str = "park",
        intent: Optional[str] = None,
        verify_checker: Optional[str] = None,
    ) -> dict[str, Any]:
        """Pick specialist from matched catalog agent/skill IDs only [CARD-234]."""
        from src.application.orchestration.supervisor_specialist_pick import (
            supervisor_specialist_handoff,
        )

        return supervisor_specialist_handoff(
            self,
            phase_id=phase_id,
            specialty=specialty,
            entry_meta=entry_meta,
            session_id=session_id,
            requested_agent_id=requested_agent_id,
            on_no_match=on_no_match,
            intent=intent,
            verify_checker=verify_checker,
        )

    def matched_capability_ids_for_job(self, job_id: str) -> list[str]:
        """Return locked matched capability IDs (checkpoint first; no re-resolve)."""
        if job_id in self._matched_ids:
            return list(self._matched_ids[job_id])
        cp = self.get_latest_checkpoint(job_id)
        if cp is not None and cp.matched_capability_ids:
            ids = list(cp.matched_capability_ids)
            self._matched_ids[job_id] = ids
            return ids
        return []

    def create_job_from_catalog_resolve(
        self,
        intent: str,
        session_id: str,
        agent_id: str,
        *,
        role: Optional[str] = None,
        matched_capability_ids: Optional[Sequence[str]] = None,
        verify_checker: Optional[str] = "pytest",
        success_rule: Optional[str] = None,
    ) -> Job:
        """
        Standing C runtime [REQ-CATJOB-001 / CARD-231]: intent → matched subset →
        Research(optional)/Formulate/Execute.
        """
        ids: list[str]
        resolve_facts: list[str] = []
        matched_entry_keywords: dict[str, list[str]] = {}
        if matched_capability_ids is not None:
            ids = [str(x) for x in matched_capability_ids]
            resolve_facts.append(
                f"capability_resolve: reused_checkpoint_ids={len(ids)} (no cold re-resolve)"
            )
        else:
            if self._capability_resolver is None:
                raise RuntimeError(
                    "JobPhaseOrchestrator requires capability_resolver for catalog formulate"
                )
            result: ResolveResult = self._capability_resolver.resolve(
                intent, role=role, trusted_only=True
            )
            ids = [e.id for e in result.matched]
            resolve_facts.extend(list(result.facts))
            for e in result.matched:
                matched_entry_keywords[e.id] = list(getattr(e, "keywords", None) or [])

        ids = matched_ids_authority(ids, preferred_agent_id=agent_id)
        job_success_rule = derive_success_rule(intent, explicit=success_rule)

        if ids and not matched_entry_keywords and self._capability_resolver is not None:
            store = getattr(self._capability_resolver, "_store", None)
            getter = getattr(store, "get_entry", None) if store is not None else None
            if callable(getter):
                for cid in ids:
                    try:
                        entry = getter(cid)
                    except Exception:
                        entry = None
                    if entry is not None:
                        matched_entry_keywords[cid] = list(
                            getattr(entry, "keywords", None) or []
                        )

        assessment = assess_catalog_match(
            ids,
            job_success_rule,
            matched_entry_keywords=matched_entry_keywords or None,
        )

        id_note = ", ".join(ids) if ids else "(none)"
        goal = (intent or "").strip() or "catalog job"
        phase_specs: list[PhaseSpec] = []
        if assessment.research_inserted:
            phase_specs.append(
                PhaseSpec(
                    name="Research",
                    success_rule=(
                        f"Research catalog gaps before plan formulate "
                        f"(reason={assessment.reason}); matched={id_note}"
                    ),
                    assigned_agent_id=agent_id,
                    verify_checker=None,
                )
            )
        phase_specs.append(
            PhaseSpec(
                name="Formulate",
                success_rule=f"Write the plan (plan only) for: {goal}",
                assigned_agent_id=agent_id,
                verify_checker=None,
            )
        )
        execute_agent_id = resolve_specialist_agent_for_capabilities(
            ids, agent_id, store=self._store
        )
        phase_specs.append(
            PhaseSpec(
                name="Execute",
                success_rule=job_success_rule,
                assigned_agent_id=execute_agent_id,
                verify_checker=verify_checker,
            )
        )
        job = self.create_job_with_phases(
            goal=goal,
            session_id=session_id,
            agent_id=agent_id,
            phase_specs=phase_specs,
            template_id="catalog_resolve_rhe",
            success_rule=job_success_rule,
        )
        self._matched_ids[job.id] = list(ids)
        phases = self._store.list_phases_for_job(job.id)
        first = phases[0]
        self._commit_checkpoint(
            first,
            verifier_status="none",
            hitl_park_state=False,
            matched_capability_ids=ids,
            research_inserted=assessment.research_inserted,
            research_reason=assessment.reason,
        )
        ev = getattr(self._store, "save_standing_journey_event", None)
        if callable(ev):
            try:
                ev(
                    job_id=job.id,
                    kind="research" if assessment.research_inserted else "research_skipped",
                    payload={
                        "research_inserted": assessment.research_inserted,
                        "reason": assessment.reason,
                        "match_count": assessment.match_count,
                        "missing_families": list(assessment.missing_families),
                        "matched_capability_ids": list(ids),
                    },
                )
            except Exception:
                pass
        if assessment.research_inserted:
            try:
                run_standing_research(
                    self,
                    job_id=job.id,
                    intent=goal,
                    success_rule=job_success_rule,
                    matched_capability_ids=ids,
                    assessment=assessment,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("standing research side-effects failed: %s", exc)
        logger.info(
            "Catalog-resolve job %s matched=%s research_inserted=%s reason=%s facts=%s",
            job.id,
            ids,
            assessment.research_inserted,
            assessment.reason,
            resolve_facts,
        )
        return job

    def _next_queued_phase(self, job_id: str, after_index: int) -> Optional[Phase]:
        for phase in self._store.list_phases_for_job(job_id):
            if phase.index > after_index and phase.status == PhaseStatus.QUEUED:
                return phase
        return None
