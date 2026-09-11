"""
Routine Executor for Autonomous Agent Execution [REQ-ROUTINE-004, REQ-ROUTINE-005].
Standing Job/Phase path for multi-step routines [CARD-222 / REQ-ROUTSTAND-*].
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

from src.application.kernel.agent_kernel import AgentKernel
from src.application.orchestration.chat_job_binding import (
    output_packet_for_phase,
)
from src.application.orchestration.external_verifier_policy import (
    apply_phase_complete_verify_gate,
)
from src.application.orchestration.job_phase_memory import prior_lines_from_job_memory
from src.application.orchestration.standing_job_graph import (
    STANDING_PHASE_LLM_TIMEOUT_SECONDS,
    StandingRoute,
    route_standing_chat,
)
from src.application.orchestration.working_set_context import (
    build_phase_working_set,
    distill_durable_note,
    format_phase_working_set_prompt,
    resolve_matched_metadata_for_job,
)
from src.application.routines.matcher import ScheduleMatcher
from src.application.routines.skill_eval_sleep import (
    ROUTINE_ID as SKILL_EVAL_SLEEP_ID,
)
from src.application.routines.skill_eval_sleep import (
    job_output_text,
    run_skill_eval_job,
)
from src.application.skills.skill_curator import (
    ROUTINE_ID as SKILL_CURATOR_ID,
)
from src.application.skills.skill_curator import (
    job_output_text as curator_job_output_text,
)
from src.application.skills.skill_curator import (
    run_curator_job,
)
from src.application.telemetry.collector import TelemetryCollector
from src.domain.orchestration.models import PhaseStatus
from src.domain.routines.models import Routine, RoutineRun, RoutineStatus
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class RoutineExecutor:
    """
    Executes autonomous routine cycles via AgentKernel in isolated ephemeral sessions.

    Multi-step prompts enter the same standing Job/Phase path as Chat
    (catalog resolve -> matched IDs -> verifier advance -> CARD-221 gate -> crash-resume).
    Cron/scheduler remains trigger-only [CARD-222].
    """

    def __init__(
        self,
        agent_registry: BuiltinAgentRegistry,
        kernel: AgentKernel,
        state_store: SQLiteStateStore,
        telemetry: TelemetryCollector,
        job_orchestrator: Any = None,
    ):
        self.agent_registry = agent_registry
        self.kernel = kernel
        self.state_store = state_store
        self.telemetry = telemetry
        self.job_orchestrator = job_orchestrator

    async def _run_standing_phases(
        self,
        *,
        orch: Any,
        job: Any,
        agent: Any,
        session_id: str,
        approval_mode: str,
        routine_id: str,
    ) -> Tuple[str, Optional[str]]:
        """
        Advance R/H/E phases on the standing orchestrator (Chat-equivalent, no SSE).
        Returns (combined_output, terminal_note) where terminal_note is parked/failed or None.
        """
        phases = list(self.state_store.list_phases_for_job(job.id))
        # CARD-229: durable notes only across phases (not raw content / skill bodies).
        durable_notes: list[str] = []
        matched_metadata = resolve_matched_metadata_for_job(orch, job.id)
        outputs: list[str] = []
        for phase in phases:
            fresh = self.state_store.get_phase(phase.id)
            if fresh.status not in {PhaseStatus.QUEUED, PhaseStatus.WAITING_APPROVAL}:
                continue
            started = orch.start_phase(fresh.id)
            bound_skill_id = None
            bound_skill_body = None
            bind_fn = getattr(orch, "bind_matched_skill_on_phase_start", None)
            if callable(bind_fn):
                for bound in bind_fn(started.id) or []:
                    if bound.get("success") and bound.get("body"):
                        bound_skill_id = bound.get("skill_id")
                        bound_skill_body = bound.get("body")
                        break
            memory_facts = list(
                prior_lines_from_job_memory(
                    agent_id=getattr(job, "agent_id", None) or "assistant",
                    job_id=job.id,
                    data_dir=getattr(self.job_orchestrator, "_data_dir", None),
                )
            )
            ws = build_phase_working_set(
                job=job,
                phase=started,
                phase_count=len(phases),
                matched_metadata=matched_metadata,
                bound_skill_id=bound_skill_id,
                bound_skill_body=bound_skill_body,
                prior_phase_notes=durable_notes,
                all_memory_facts=memory_facts,
            )
            assignment = format_phase_working_set_prompt(ws)
            try:
                assistant_msg = await asyncio.wait_for(
                    self.kernel.run_turn(
                        agent=agent,
                        session_id=session_id,
                        user_content=assignment,
                        approval_mode=approval_mode,
                        routine_id=routine_id,
                        job_id=job.id,
                        phase_id=started.id,
                    ),
                    timeout=STANDING_PHASE_LLM_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                # Honest fail with checkpoint — never leave orphan RUNNING [reliability].
                orch.fail_phase(
                    started.id,
                    f"phase_llm_timeout after {STANDING_PHASE_LLM_TIMEOUT_SECONDS}s",
                )
                outputs.append("[phase_llm_timeout]")
                return "\n\n".join(outputs), "failed"
            except asyncio.CancelledError:
                orch.fail_phase(started.id, "phase_cancelled_during_llm")
                raise
            except Exception as exc:  # noqa: BLE001 — surface as durable phase failure
                orch.fail_phase(started.id, f"phase_llm_error: {exc}")
                outputs.append(f"[phase_failed] {exc}")
                return "\n\n".join(outputs), "failed"
            content = (assistant_msg.content or "").strip()

            # HITL park: same REQUIRE_CONFIRM path as Chat [REQ-ROUTSTAND-003].
            pending = []
            getter = getattr(self.state_store, "get_pending_approvals", None)
            if callable(getter):
                try:
                    pending = getter(session_id=session_id) or []
                except TypeError:
                    try:
                        pending = getter(agent_id=agent.id) or []
                    except Exception:
                        pending = []
                except Exception:
                    pending = []
            if pending:
                orch.park_phase(started.id)
                outputs.append(content or "[waiting_approval]")
                return "\n\n".join(outputs), "parked"

            gate = apply_phase_complete_verify_gate(
                orch,
                phase_id=started.id,
                output_packet=output_packet_for_phase(started, content),
                checker_passed=None,
            )
            # Execute / checker phases that skip must not silent-advance; gate encodes that.
            if gate.get("status") == "failed":
                outputs.append(content or "[phase_failed]")
                return "\n\n".join(outputs), "failed"
            if not gate.get("advanced", True) and gate.get("status") == "skipped_no_checker":
                # Standing rule: Execute does not advance on skip — stop honestly.
                lane = (started.name or "").strip().lower()
                has_checker = bool((getattr(started, "verify_checker", None) or "").strip())
                if lane.startswith("execute") or has_checker:
                    outputs.append(content or "[skipped_no_checker]")
                    return "\n\n".join(outputs), "skipped_no_checker"

            outputs.append(content)
            # CARD-229: prior phase -> short durable note (strip tool dumps).
            durable_notes.append(
                distill_durable_note(
                    phase_name=started.name,
                    phase_index=started.index,
                    raw_output=content or "",
                )
            )
        return "\n\n".join(outputs), None

    async def execute_routine(self, routine: Routine) -> RoutineRun:
        """
        Execute an autonomous routine turn with full tool authorization and run logging.
        """
        start_time = time.perf_counter()
        now = datetime.now(timezone.utc)

        agent = self.agent_registry.get_profile(routine.agent_id)
        if not agent:
            run = RoutineRun(
                id=str(uuid.uuid4()),
                routine_id=routine.id,
                agent_id=routine.agent_id,
                status=RoutineStatus.FAILED,
                error_message=f"Agent '{routine.agent_id}' not found in registry.",
                duration_ms=0.0,
                created_at=now,
            )
            routine.last_status = RoutineStatus.FAILED
            routine.last_run_at = now
            self.state_store.save_routine(routine)
            self.state_store.record_routine_run(run)
            return run

        # Create isolated ephemeral session for autonomous execution
        session = self.state_store.create_session(
            agent_id=agent.id,
            title=f"Autonomous Routine: {routine.name}",
        )

        try:
            if routine.id == SKILL_CURATOR_ID:
                data_dir = getattr(self.kernel, "data_dir", None)
                if not data_dir:
                    from src.infrastructure.data.resolver import DataDirResolver

                    data_dir = str(DataDirResolver().platform_default())
                from src.application.skills.user_catalog import UserSkillCatalog

                catalog = UserSkillCatalog(skills_dir=str(Path(data_dir) / "skills"))
                result = run_curator_job(catalog, routine=routine)
                dur_ms = (time.perf_counter() - start_time) * 1000
                status = RoutineStatus.FAILED if not result.get("success") else RoutineStatus.SUCCESS
                run = RoutineRun(
                    id=str(uuid.uuid4()),
                    routine_id=routine.id,
                    agent_id=agent.id,
                    status=status,
                    output=curator_job_output_text(result),
                    error_message=None if status == RoutineStatus.SUCCESS else str(result.get("error") or ""),
                    duration_ms=round(dur_ms, 2),
                    created_at=now,
                )
                routine.last_status = status
                routine.last_run_at = now
                routine.next_run_at = ScheduleMatcher.compute_next_run(routine, base_time=now)
                self.state_store.save_routine(routine)
                self.state_store.record_routine_run(run)
                return run

            if routine.id == SKILL_EVAL_SLEEP_ID:
                data_dir = getattr(self.kernel, "data_dir", None)
                if not data_dir:
                    from src.infrastructure.data.resolver import DataDirResolver

                    data_dir = str(DataDirResolver().platform_default())
                result = run_skill_eval_job(
                    self.state_store,
                    data_dir,
                    routine=routine,
                    session_id=session.id,
                    agent_id=agent.id,
                )
                dur_ms = (time.perf_counter() - start_time) * 1000
                status = RoutineStatus.FAILED if result.get("status") == "failed" else RoutineStatus.SUCCESS
                run = RoutineRun(
                    id=str(uuid.uuid4()),
                    routine_id=routine.id,
                    agent_id=agent.id,
                    status=status,
                    output=job_output_text(result),
                    error_message=None if status == RoutineStatus.SUCCESS else str(result.get("reason") or ""),
                    duration_ms=round(dur_ms, 2),
                    created_at=now,
                )
                routine.last_status = status
                routine.last_run_at = now
                routine.next_run_at = ScheduleMatcher.compute_next_run(routine, base_time=now)
                self.state_store.save_routine(routine)
                self.state_store.record_routine_run(run)
                return run

            mode = "run" if str((routine.metadata or {}).get("approval_mode") or "").strip().lower() == "run" else "ask"
            standing_job_id: Optional[str] = None
            orch = self.job_orchestrator
            standing = route_standing_chat(routine.prompt)

            # Standing path [CARD-222]: multi-step -> create_job_from_catalog_resolve (same as Chat).
            if (
                orch is not None
                and standing == StandingRoute.MULTI_STEP_JOB_GRAPH
                and hasattr(orch, "create_job_from_catalog_resolve")
            ):
                job = orch.create_job_from_catalog_resolve(
                    intent=routine.prompt,
                    session_id=session.id,
                    agent_id=agent.id,
                    role=agent.id,
                    verify_checker=None,
                )
                standing_job_id = job.id
                meta = dict(routine.metadata or {})
                meta["last_standing_job_id"] = standing_job_id
                routine.metadata = meta
                # Persist job_id before phase loop so mid-phase kill / HTTP timeout
                # still leaves durable standing linkage [REQ-ROUTSTAND-004].
                self.state_store.save_routine(routine)
                output_text, terminal = await self._run_standing_phases(
                    orch=orch,
                    job=job,
                    agent=agent,
                    session_id=session.id,
                    approval_mode=mode,
                    routine_id=routine.id,
                )
                # Parked HITL is still a successful trigger (work durable on job_id).
                status = RoutineStatus.SUCCESS
                if terminal == "failed":
                    status = RoutineStatus.FAILED
                dur_ms = (time.perf_counter() - start_time) * 1000
                run = RoutineRun(
                    id=str(uuid.uuid4()),
                    routine_id=routine.id,
                    agent_id=agent.id,
                    status=status,
                    output=output_text,
                    error_message="phase_failed" if terminal == "failed" else None,
                    duration_ms=round(dur_ms, 2),
                    created_at=now,
                    job_id=standing_job_id,
                )
                routine.last_status = status
                routine.last_run_at = now
                routine.next_run_at = ScheduleMatcher.compute_next_run(routine, base_time=now)
                self.state_store.save_routine(routine)
                self.state_store.record_routine_run(run)
                return run

            # Short turns: plain ReAct (same standing SHORT_REACT decision as Chat).
            assistant_msg = await self.kernel.run_turn(
                agent=agent,
                session_id=session.id,
                user_content=routine.prompt,
                approval_mode=mode,
                routine_id=routine.id,
            )
            dur_ms = (time.perf_counter() - start_time) * 1000

            run = RoutineRun(
                id=str(uuid.uuid4()),
                routine_id=routine.id,
                agent_id=agent.id,
                status=RoutineStatus.SUCCESS,
                output=assistant_msg.content,
                duration_ms=round(dur_ms, 2),
                created_at=now,
                job_id=None,
            )
            routine.last_status = RoutineStatus.SUCCESS
            routine.last_run_at = now
            routine.next_run_at = ScheduleMatcher.compute_next_run(routine, base_time=now)
            self.state_store.save_routine(routine)
            self.state_store.record_routine_run(run)
            return run

        except Exception as e:
            dur_ms = (time.perf_counter() - start_time) * 1000
            # If standing job was created but phase loop raised before fail_phase, close orphan.
            orphan_job_id = None
            try:
                orphan_job_id = (routine.metadata or {}).get("last_standing_job_id")
                orch_exc = self.job_orchestrator
                if orphan_job_id and orch_exc is not None:
                    for ph in self.state_store.list_phases_for_job(orphan_job_id):
                        if ph.status == PhaseStatus.RUNNING:
                            orch_exc.fail_phase(ph.id, f"routine_exception: {e}")
                            break
            except Exception:
                pass
            run = RoutineRun(
                id=str(uuid.uuid4()),
                routine_id=routine.id,
                agent_id=agent.id,
                status=RoutineStatus.FAILED,
                error_message=str(e),
                duration_ms=round(dur_ms, 2),
                created_at=now,
                job_id=orphan_job_id,
            )
            routine.last_status = RoutineStatus.FAILED
            routine.last_run_at = now
            self.state_store.save_routine(routine)
            self.state_store.record_routine_run(run)
            return run

    async def trigger_routine_by_id(self, routine_id: str) -> Optional[RoutineRun]:
        """
        Manually trigger a routine by ID out-of-schedule.
        """
        routine = self.state_store.get_routine(routine_id)
        if not routine:
            return None
        return await self.execute_routine(routine)
