"""
Routine Executor for Autonomous Agent Execution [REQ-ROUTINE-004, REQ-ROUTINE-005].
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.application.kernel.agent_kernel import AgentKernel
from src.application.routines.matcher import ScheduleMatcher
from src.application.telemetry.collector import TelemetryCollector
from src.domain.routines.models import Routine, RoutineRun, RoutineStatus
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class RoutineExecutor:
    """
    Executes autonomous routine cycles via AgentKernel in isolated ephemeral sessions.
    """

    def __init__(
        self,
        agent_registry: BuiltinAgentRegistry,
        kernel: AgentKernel,
        state_store: SQLiteStateStore,
        telemetry: TelemetryCollector,
    ):
        self.agent_registry = agent_registry
        self.kernel = kernel
        self.state_store = state_store
        self.telemetry = telemetry

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
            mode = "run" if str((routine.metadata or {}).get("approval_mode") or "").strip().lower() == "run" else "ask"
            assistant_msg = await self.kernel.run_turn(
                agent=agent,
                session_id=session.id,
                user_content=routine.prompt,
                approval_mode=mode,
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
            )
            routine.last_status = RoutineStatus.SUCCESS
            routine.last_run_at = now
            routine.next_run_at = ScheduleMatcher.compute_next_run(routine, base_time=now)
            self.state_store.save_routine(routine)
            self.state_store.record_routine_run(run)
            return run

        except Exception as e:
            dur_ms = (time.perf_counter() - start_time) * 1000
            run = RoutineRun(
                id=str(uuid.uuid4()),
                routine_id=routine.id,
                agent_id=agent.id,
                status=RoutineStatus.FAILED,
                error_message=str(e),
                duration_ms=round(dur_ms, 2),
                created_at=now,
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
