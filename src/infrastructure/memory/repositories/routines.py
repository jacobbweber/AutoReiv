"""
Autonomous Routine & Execution Run Repository Mixin [REQ-ROUT-001 - REQ-ROUT-003].
"""

import json
from datetime import datetime, timezone
from typing import Any, List, Optional

from src.domain.routines.models import Routine, RoutineRun, RoutineStatus, ScheduleType


class RoutineRepositoryMixin:
    """Methods for persisting scheduled routines and logging execution runs."""

    def save_routine(self, routine: Routine) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(routine.metadata) if routine.metadata else None
        last_run_str = routine.last_run_at.isoformat() if routine.last_run_at else None
        next_run_str = routine.next_run_at.isoformat() if routine.next_run_at else None

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO routines (
                    id, name, description, agent_id, prompt, schedule_type,
                    interval_seconds, cron_expression, enabled, last_run_at,
                    next_run_at, last_status, metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    agent_id = excluded.agent_id,
                    prompt = excluded.prompt,
                    schedule_type = excluded.schedule_type,
                    interval_seconds = excluded.interval_seconds,
                    cron_expression = excluded.cron_expression,
                    enabled = excluded.enabled,
                    last_run_at = excluded.last_run_at,
                    next_run_at = excluded.next_run_at,
                    last_status = excluded.last_status,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    routine.id,
                    routine.name,
                    routine.description,
                    routine.agent_id,
                    routine.prompt,
                    routine.schedule_type.value
                    if hasattr(routine.schedule_type, "value")
                    else str(routine.schedule_type),
                    routine.interval_seconds,
                    routine.cron_expression,
                    1 if routine.enabled else 0,
                    last_run_str,
                    next_run_str,
                    routine.last_status.value if hasattr(routine.last_status, "value") else str(routine.last_status),
                    metadata_json,
                    routine.created_at.isoformat(),
                    now_str,
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_routine(self, routine_id: str) -> Optional[Routine]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, description, agent_id, prompt, schedule_type,
                       interval_seconds, cron_expression, enabled, last_run_at,
                       next_run_at, last_status, metadata_json, created_at, updated_at
                FROM routines WHERE id = ?
                """,
                (routine_id,),
            )
            r = cur.fetchone()
            if not r:
                return None

            meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
            last_run = datetime.fromisoformat(r["last_run_at"]) if r["last_run_at"] else None
            next_run = datetime.fromisoformat(r["next_run_at"]) if r["next_run_at"] else None

            return Routine(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                agent_id=r["agent_id"],
                prompt=r["prompt"],
                schedule_type=ScheduleType(r["schedule_type"]),
                interval_seconds=r["interval_seconds"],
                cron_expression=r["cron_expression"],
                enabled=bool(r["enabled"]),
                last_run_at=last_run,
                next_run_at=next_run,
                last_status=RoutineStatus(r["last_status"]),
                metadata=meta,
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            )
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_routines(
        self,
        enabled_only: bool = False,
        agent_id: Optional[str] = None,
    ) -> List[Routine]:
        query = "SELECT id, name, description, agent_id, prompt, schedule_type, interval_seconds, cron_expression, enabled, last_run_at, next_run_at, last_status, metadata_json, created_at, updated_at FROM routines WHERE 1=1"
        params: List[Any] = []
        if enabled_only:
            query += " AND enabled = 1"
        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
        query += " ORDER BY created_at ASC"

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            routines = []
            for r in rows:
                meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                last_run = datetime.fromisoformat(r["last_run_at"]) if r["last_run_at"] else None
                next_run = datetime.fromisoformat(r["next_run_at"]) if r["next_run_at"] else None
                routines.append(
                    Routine(
                        id=r["id"],
                        name=r["name"],
                        description=r["description"],
                        agent_id=r["agent_id"],
                        prompt=r["prompt"],
                        schedule_type=ScheduleType(r["schedule_type"]),
                        interval_seconds=r["interval_seconds"],
                        cron_expression=r["cron_expression"],
                        enabled=bool(r["enabled"]),
                        last_run_at=last_run,
                        next_run_at=next_run,
                        last_status=RoutineStatus(r["last_status"]),
                        metadata=meta,
                        created_at=datetime.fromisoformat(r["created_at"]),
                        updated_at=datetime.fromisoformat(r["updated_at"]),
                    )
                )
            return routines
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_routine(self, routine_id: str) -> bool:
        """Delete routine from SQLite storage (protects built-in routines)."""
        from src.domain.routines.manifests import BUILTIN_ROUTINES

        builtin_ids = {r.id for r in BUILTIN_ROUTINES}
        if routine_id in builtin_ids:
            return False

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM routines WHERE id = ?", (routine_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()

    def toggle_routine(self, routine_id: str) -> Optional[bool]:
        """Toggle enabled flag of a routine and return the new enabled state."""
        routine = self.get_routine(routine_id)
        if not routine:
            return None
        new_state = not routine.enabled
        routine.enabled = new_state
        self.save_routine(routine)
        return new_state

    def record_routine_run(self, run: RoutineRun) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO routine_runs (id, routine_id, agent_id, status, output, error_message, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.routine_id,
                    run.agent_id,
                    run.status.value if hasattr(run.status, "value") else str(run.status),
                    run.output,
                    run.error_message,
                    run.duration_ms,
                    run.created_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_routine_runs(self, routine_id: Optional[str] = None, limit: int = 50) -> List[RoutineRun]:
        query = "SELECT id, routine_id, agent_id, status, output, error_message, duration_ms, created_at FROM routine_runs WHERE 1=1"
        params: List[Any] = []
        if routine_id:
            query += " AND routine_id = ?"
            params.append(routine_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            return [
                RoutineRun(
                    id=r["id"],
                    routine_id=r["routine_id"],
                    agent_id=r["agent_id"],
                    status=RoutineStatus(r["status"]),
                    output=r["output"],
                    error_message=r["error_message"],
                    duration_ms=r["duration_ms"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                for r in rows
            ]
        finally:
            if self._mem_conn is None:
                conn.close()
