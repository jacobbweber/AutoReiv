"""Job/Phase checkpoint persistence, crash/kill recovery, and specialist agent resolution [CARD-715]."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Sequence, Union

from src.application.orchestration.crash_resume import CrashResumeResult
from src.application.orchestration.job_phase_memory import persist_phase_memory_for_job
from src.application.orchestration.kill_resume import (
    OPERATOR_KILL_REASON,
    is_operator_kill_reason,
    kill_checkpoint_payload,
)
from src.domain.agents.profiles import DEFAULT_PLATFORM_AGENT_ID, canonical_agent_id
from src.domain.orchestration.models import (
    JobPhaseCheckpoint,
    JobStatus,
    Phase,
    PhaseStatus,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)

# CARD-530 D3: which run owns a running phase (one serve process). start_phase mints a token; a cancelled
# worker may only re-queue the phase if it still holds the current token.
_PHASE_RUN_TOKENS: dict[str, str] = {}

_TERMINAL_JOB = {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED}


def _ticks_coding(agent_id: str, store: Optional[Any]) -> bool:
    if agent_id == "developer":
        return True
    getter = getattr(store, "get_agent_profile", None) if store is not None else None
    profile = getter(agent_id) if callable(getter) else None
    if profile is not None:
        return "coding" in (getattr(profile, "allowed_skill", None) or [])
    from src.infrastructure.content.store import get_store  # CARD-570: the winning agent file

    item = get_store().agents.load(agent_id)
    return bool(item and "coding" in item.skills)


def resolve_specialist_agent_for_capabilities(
    matched_ids: Sequence[str],
    default_agent_id: str,
    store: Optional[Any] = None,
) -> str:
    """
    Resolve specialist agent for execution phase when capabilities require specialist dispatch [CARD-336, CARD-339, CARD-341, CARD-383].
    Uses canonical_agent_id for single-source resolution rather than ad-hoc string comparisons.
    """
    canonical_default = canonical_agent_id(default_agent_id or DEFAULT_PLATFORM_AGENT_ID)
    if not matched_ids:
        return canonical_default

    for cid in matched_ids:
        s = str(cid or "").strip().lower()
        prefix = "agent." if s.startswith("agent.") else ""
        candidate = s[len(prefix) :] if prefix else ""
        if not candidate:
            continue
        resolved = canonical_agent_id(candidate)
        # CARD-544: a match on the chat's own agent (role bonus) is not a specialist pick; keep routing by family.
        if resolved != canonical_default:
            return resolved

    has_coding_tools = any(
        any(k in cid.lower() for k in ("repo_file_", "write_project_file", "project_dir", "git_", "coding"))
        for cid in matched_ids
    )
    if has_coding_tools:  # CARD-544 D1: code work goes to Developer unless the default agent ticks coding
        return canonical_default if _ticks_coding(canonical_default, store) else "developer"

    has_tutor_tools = any(
        any(k in cid.lower() for k in ("tutor", "education", "mastery", "quiz", "elaboration", "flashcard"))
        for cid in matched_ids
    )
    if has_tutor_tools:
        return DEFAULT_PLATFORM_AGENT_ID

    has_autoreiv_tools = any(
        any(
            k in cid.lower()
            for k in (
                "wiki_",
                "wiki_note",
                "weekly_note",
                "weekly_task",
                "work_item",
                "rollover",
                "system_info",
                "health",
                "sre",
                "diagnostics",
                "platform-health",
            )
        )
        for cid in matched_ids
    )
    if has_autoreiv_tools:
        return DEFAULT_PLATFORM_AGENT_ID

    for cid in matched_ids:
        s = str(cid or "").strip().lower()
        if "homelab" in s:
            return "homelab"

    return canonical_default


class JobRecoveryMixin:
    """Checkpoint persistence, phase memory persistence, and crash/kill recovery for JobPhaseOrchestrator."""

    _store: SQLiteStateStore
    _data_dir: Optional[Union[str, Path]]
    _matched_ids: dict[str, list[str]]

    def phase_run_token(self, phase_id: str) -> Optional[str]:
        """Token of the run that last started ``phase_id`` in this process [CARD-530 D3]."""
        return _PHASE_RUN_TOKENS.get(phase_id)

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
            raw_agent = (
                getattr(job, "agent_id", None)
                or getattr(phase, "assigned_agent_id", None)
                or DEFAULT_PLATFORM_AGENT_ID
            )
            agent_id = canonical_agent_id(str(raw_agent))
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

    def checkpoint_mid_llm_kill_phase(
        self, phase_id: str, run_token: Optional[str] = None, reason: str = OPERATOR_KILL_REASON
    ) -> dict:
        """Operator/worker kill mid-LLM: checkpoint + re-queue, never fail/cancel [CARD-259]."""
        phase = self._store.get_phase(phase_id)
        job = self._store.get_job(phase.job_id)
        current_token = _PHASE_RUN_TOKENS.get(phase_id)
        if run_token and current_token and current_token != run_token:
            logger.info("Skipped stale kill checkpoint job=%s phase=%s (newer run owns it)", phase.job_id, phase.id)
            return kill_checkpoint_payload(
                job_id=phase.job_id,
                phase_id=phase.id,
                phase_name=getattr(phase, "name", None),
                checkpointed=False,
                extra={"stale_run": True, "phase_status": phase.status.value},
            )
        if phase.status in {PhaseStatus.FAILED, PhaseStatus.CANCELLED, PhaseStatus.DONE}:
            return kill_checkpoint_payload(
                job_id=phase.job_id,
                phase_id=phase.id,
                phase_name=getattr(phase, "name", None),
                checkpointed=False,
                resumable=job.status not in _TERMINAL_JOB,
                extra={"already_terminal": True, "phase_status": phase.status.value},
            )
        if phase.status == PhaseStatus.WAITING_APPROVAL:
            return kill_checkpoint_payload(
                job_id=phase.job_id,
                phase_id=phase.id,
                phase_name=getattr(phase, "name", None),
                checkpointed=True,
                extra={"parked": True},
            )
        if phase.status == PhaseStatus.RUNNING:
            phase.status = PhaseStatus.QUEUED
            phase.react_state = None
            phase = self._store.update_phase(phase)
            try:
                self._commit_checkpoint(
                    phase,
                    verifier_status="none",
                    hitl_park_state=False,
                    last_fail_reason=reason,
                )
            except Exception:
                logger.exception("kill checkpoint write failed job=%s phase=%s", phase.job_id, phase.id)
            if job.status not in _TERMINAL_JOB:
                job = self._store.update_job_status(
                    job.id,
                    JobStatus.RUNNING.value,
                    current_phase_id=phase.id,
                )
            ev = getattr(self._store, "save_standing_journey_event", None)
            if callable(ev):
                try:
                    ev(
                        job_id=phase.job_id,
                        kind="kill_checkpointed",
                        payload={
                            "phase_id": phase.id,
                            "phase_index": phase.index,
                            "reason": reason,
                        },
                    )
                except Exception:
                    pass
            logger.info(
                "Kill-checkpointed job %s phase %s (RUNNING -> QUEUED)",
                phase.job_id,
                phase.id,
            )
            return kill_checkpoint_payload(
                job_id=phase.job_id,
                phase_id=phase.id,
                phase_name=getattr(phase, "name", None),
                checkpointed=True,
            )
        return kill_checkpoint_payload(
            job_id=phase.job_id,
            phase_id=phase.id,
            phase_name=getattr(phase, "name", None),
            checkpointed=True,
            extra={"already_queued": True},
        )

    def checkpoint_mid_llm_kill(self, session_id: str) -> dict:
        """Checkpoint every in-flight phase on a Chat session [CARD-259 / REQ-KILLR-001]."""
        lister = getattr(self._store, "list_jobs_for_session", None)
        if not callable(lister):
            return kill_checkpoint_payload(checkpointed=False, resumable=True)
        jobs = list(lister(session_id) or [])
        last = kill_checkpoint_payload(checkpointed=False, resumable=True)
        for job in jobs:
            status = job.status if isinstance(job.status, JobStatus) else JobStatus(str(job.status))
            if status in _TERMINAL_JOB:
                continue
            for phase in self._store.list_phases_for_job(job.id):
                if phase.status == PhaseStatus.RUNNING:
                    return self.checkpoint_mid_llm_kill_phase(phase.id)
                if phase.status in {PhaseStatus.QUEUED, PhaseStatus.WAITING_APPROVAL}:
                    last = kill_checkpoint_payload(
                        job_id=job.id,
                        phase_id=phase.id,
                        phase_name=getattr(phase, "name", None),
                        checkpointed=True,
                        extra={"phase_status": phase.status.value},
                    )
        return last

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

        if interrupted is None and parked is None:
            queued = next((p for p in phases if p.status == PhaseStatus.QUEUED), None)
            if (
                queued is not None
                and is_operator_kill_reason(getattr(checkpoint, "last_fail_reason", ""))
            ):
                if job.status not in _TERMINAL_JOB:
                    job = self._store.update_job_status(
                        job.id,
                        JobStatus.RUNNING.value,
                        current_phase_id=queued.id,
                    )
                ev = getattr(self._store, "save_standing_journey_event", None)
                if callable(ev):
                    try:
                        ev(
                            job_id=job_id,
                            kind="resumed_from_checkpoint",
                            payload={
                                "phase_index": checkpoint.phase_index if checkpoint else None,
                                "phase_id": queued.id,
                                "reason": "continued from durable checkpoint after operator kill",
                            },
                        )
                    except Exception:
                        pass
                return CrashResumeResult(
                    job=job,
                    checkpoint=checkpoint,
                    continue_phase=queued,
                    ok=True,
                    needs_replan=False,
                    resumed_from_checkpoint=True,
                    reason="continued from durable checkpoint after operator kill",
                    matched_capability_ids=matched_ids,
                )
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
