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
    CrashResumeResult,
    verifier_status_from_facts,
)
from src.application.orchestration.job_phase_memory import persist_phase_memory_for_job
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
        # CARD-230 fail-closed intake gate before phase 1 [REQ-INTAKE-004].
        # Applies to standing catalog / outcome-intake jobs only so legacy bare
        # Job/Phase unit fixtures (215-229) keep exercising the state machine.
        # CARD-231: Research phase with research_inserted may start when matched
        # IDs are empty (gap fill into memory.db); still requires testable rule.
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
        self._commit_checkpoint(phase, verifier_status="failed", hitl_park_state=False)
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
        matched_capability_ids: Optional[Sequence[str]] = None,
        memory_fact_ids: Optional[Sequence[str]] = None,
        research_inserted: Optional[bool] = None,
        research_reason: Optional[str] = None,
        replan_count: Optional[int] = None,
        last_fail_reason: Optional[str] = None,
    ) -> JobPhaseCheckpoint:
        """Durable on-disk checkpoint after a phase commit [REQ-RESUME-001 / REQ-CATJOB-002 / CARD-226 / CARD-231 / CARD-232]."""
        saver = getattr(self._store, "save_job_phase_checkpoint", None)
        if not callable(saver):
            raise RuntimeError("Store does not support job_phase_checkpoints")
        ids: Optional[list[str]]
        if matched_capability_ids is not None:
            ids = [str(x) for x in matched_capability_ids]
            self._matched_ids[phase.job_id] = list(ids)
        else:
            ids = self._matched_ids.get(phase.job_id)
            if ids is None:
                prior = self.get_latest_checkpoint(phase.job_id)
                ids = list(prior.matched_capability_ids) if prior else []
                if ids:
                    self._matched_ids[phase.job_id] = list(ids)
        prior_cp = self.get_latest_checkpoint(phase.job_id)
        prior_mem = list(prior_cp.memory_fact_ids) if prior_cp else []
        if memory_fact_ids is not None:
            # Accumulate across phases so resume sees full job memory refs [REQ-JPMEM-002].
            merged: list[str] = []
            for x in prior_mem + [str(i) for i in memory_fact_ids]:
                if x and x not in merged:
                    merged.append(x)
            mem_ids = merged
        else:
            mem_ids = prior_mem
        cp = saver(
            job_id=phase.job_id,
            phase_id=phase.id,
            phase_index=int(phase.index),
            verifier_status=verifier_status,
            hitl_park_state=hitl_park_state,
            matched_capability_ids=ids,
            memory_fact_ids=mem_ids,
            research_inserted=research_inserted,
            research_reason=research_reason,
            replan_count=replan_count,
            last_fail_reason=last_fail_reason,
        )
        logger.info(
            "Checkpoint job=%s phase_index=%s verifier=%s park=%s caps=%s mem=%s",
            phase.job_id,
            phase.index,
            verifier_status,
            hitl_park_state,
            len(ids or []),
            len(mem_ids or []),
        )
        return cp

    def _persist_phase_memory(self, phase: Phase, facts: list[str]) -> list[str]:
        """Write phase facts into <agent>_memory.db; return fact ids [REQ-JPMEM-002]."""
        try:
            job = self._store.get_job(phase.job_id)
            agent_id = getattr(job, "agent_id", None) or getattr(phase, "assigned_agent_id", None) or "assistant"
            return persist_phase_memory_for_job(
                agent_id=str(agent_id),
                job_id=phase.job_id,
                phase_index=int(phase.index),
                phase_name=str(phase.name or f"phase_{phase.index}"),
                facts=facts,
                data_dir=self._data_dir,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Phase memory persist skipped: %s", exc)
            return []



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
            "pack_id": loaded.get("pack_id"),
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
            "pack_id": loaded.get("pack_id"),
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
        # Round-robin start index; skip unloadable ids but still load at most ONE body.
        start = phase.index % len(skill_ids)
        ordered = skill_ids[start:] + skill_ids[:start]
        last: dict[str, Any] | None = None
        for sid in ordered:
            bound = self.bind_skill_for_phase(phase_id, sid)
            last = bound
            if bound.get("success"):
                return [bound]
        return [last] if last is not None else []


    def handle_mid_job_capability_gap(
        self,
        phase_id: str,
        *,
        spine: Any,
        matched_entry_keywords: Optional[Mapping[str, Sequence[str]]] = None,
        park: bool = True,
        kind: Optional[str] = None,
        name: Optional[str] = None,
        pack_id: Optional[str] = None,
        summary: str = "",
        content: str = "",
    ) -> dict[str, Any]:
        """Mid-job capability gap -> 218 candidate scaffold [CARD-233]."""
        from src.application.orchestration.mid_job_self_scaffold import (
            apply_mid_job_scaffold_on_gap,
            detect_mid_job_capability_gap,
        )

        phase = self._store.get_phase(phase_id)
        job = self._store.get_job(phase.job_id)
        matched = self.matched_capability_ids_for_job(phase.job_id)
        gap = detect_mid_job_capability_gap(
            matched,
            getattr(job, "success_rule", None) or getattr(phase, "success_rule", None),
            matched_entry_keywords=matched_entry_keywords,
            phase_name=getattr(phase, "name", None),
        )
        if not gap.is_gap:
            return {"ok": False, "action": "none", "reason": "no_gap", "trusted_write": False}
        return apply_mid_job_scaffold_on_gap(
            self,
            spine=spine,
            phase_id=phase_id,
            gap=gap,
            kind=kind,
            name=name,
            pack_id=pack_id,
            summary=summary,
            content=content,
            park=park,
        )

    def promote_mid_job_scaffold(
        self,
        *,
        spine: Any,
        job_id: str,
        record_id: str,
        intent: Optional[str] = None,
    ) -> dict[str, Any]:
        """HITL promote scaffold + catalog re-resolve matched IDs [CARD-233]."""
        from src.application.orchestration.mid_job_self_scaffold import (
            promote_scaffold_and_reresolve,
        )

        return promote_scaffold_and_reresolve(
            self,
            spine=spine,
            job_id=job_id,
            record_id=record_id,
            intent=intent,
        )

    def forge_approve_and_resume(
        self,
        *,
        spine: Any,
        record_id: str,
        intent: Optional[str] = None,
    ) -> dict[str, Any]:
        """Forge Approve resumes same parked job_id [CARD-251]."""
        from src.application.orchestration.mid_job_self_scaffold import (
            forge_approve_and_resume_job,
        )

        return forge_approve_and_resume_job(
            self,
            spine=spine,
            record_id=record_id,
            intent=intent,
        )



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
        """Pick specialist from matched catalog agent/pack IDs only [CARD-234]."""
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

        When matched_capability_ids is provided (resume path), reuse that subset and do not
        cold re-resolve [REQ-CATJOB-002].

        CARD-230: derive/persist testable job.success_rule; matched IDs are authority
        (agent_id is preference only) [REQ-INTAKE-002, REQ-INTAKE-003].

        CARD-231: thin/gap → insert Research before Formulate; sufficient → skip research.
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
                intent, role=role
            )
            ids = [e.id for e in result.matched]
            resolve_facts.extend(list(result.facts))
            for e in result.matched:
                matched_entry_keywords[e.id] = list(getattr(e, "keywords", None) or [])

        # Agent picker preference must not widen matched subset [REQ-INTAKE-003].
        ids = matched_ids_authority(ids, preferred_agent_id=agent_id)

        job_success_rule = derive_success_rule(intent, explicit=success_rule)

        # Fill keyword map from catalog store when reuse path omitted entry metadata.
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
                success_rule=f"Formulate plan using matched capabilities: {id_note}",
                assigned_agent_id=agent_id,
                verify_checker=None,
            )
        )
        phase_specs.append(
            PhaseSpec(
                name="Execute",
                success_rule=job_success_rule,
                assigned_agent_id=agent_id,
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
        # Bootstrap checkpoint so resume can reuse matched IDs before first phase commit.
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
        # Standing journey: record research decision even when skipped [REQ-RESEARCH-004].
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
        # Thin/gap: run research side-effects (memory.db + gap proposals) immediately
        # so phase-0 Research has facts before formulate [REQ-RESEARCH-003].
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
        - Matched capability IDs come from checkpoint (no cold re-resolve) [REQ-CATJOB-002].
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
        matched_ids = list(checkpoint.matched_capability_ids) if checkpoint else []
        if matched_ids:
            self._matched_ids[job_id] = list(matched_ids)
        if checkpoint is None or checkpoint.corrupt:
            return CrashResumeResult(
                job=job,
                checkpoint=checkpoint,
                ok=False,
                needs_replan=True,
                resumed_from_checkpoint=False,
                reason="checkpoint corrupt or missing",
                matched_capability_ids=matched_ids,
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
                matched_capability_ids=matched_ids,
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
        # Standing journey resume event for Observability replay [CARD-227]
        ev = getattr(self._store, "save_standing_journey_event", None)
        if callable(ev):
            try:
                ev(
                    job_id=job_id,
                    kind="resumed_from_checkpoint",
                    payload={
                        "phase_index": checkpoint.phase_index if checkpoint else None,
                        "phase_id": continue_phase.id if continue_phase else None,
                        "reason": "continued from durable checkpoint after interrupt",
                    },
                )
            except Exception:
                pass

        return CrashResumeResult(
            job=job,
            checkpoint=checkpoint,
            continue_phase=continue_phase,
            ok=True,
            needs_replan=False,
            resumed_from_checkpoint=True,
            reason="continued from durable checkpoint after interrupt",
            matched_capability_ids=matched_ids,
        )

    def _next_queued_phase(self, job_id: str, after_index: int) -> Optional[Phase]:
        for phase in self._store.list_phases_for_job(job_id):
            if phase.index > after_index and phase.status == PhaseStatus.QUEUED:
                return phase
        return None
