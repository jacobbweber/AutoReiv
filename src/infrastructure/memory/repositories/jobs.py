"""
Job and Phase repository mixin [REQ-ORCH-031, REQ-ORCH-032, REQ-ORCH-033].
SQLite-backed. Does not use in-memory ExecutionPlan as the store.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence

from src.domain.orchestration.errors import (
    InvalidJobStatusError,
    JobNotFoundError,
    MissingParentJobError,
    PhaseNotFoundError,
)
from src.domain.orchestration.models import (
    HandoffPacket,
    Job,
    JobPhaseCheckpoint,
    JobStatus,
    Phase,
    PhaseStatus,
    ReactState,
)

_JOB_STATUSES = {item.value for item in JobStatus}
_PHASE_STATUSES = {item.value for item in PhaseStatus}
_REACT_STATES = {item.value for item in ReactState}

_JOB_COLUMNS = (
    "id, goal, status, budget_max_phases, budget_max_handoffs, budget_max_ollama_slots, "
    "current_phase_id, template_id, session_id, agent_id, created_at, updated_at"
)
_PHASE_COLUMNS = (
    'id, job_id, name, "index", assigned_agent_id, status, success_rule, verify_checker, '
    "input_packet_json, output_packet_json, parent_phase_id, max_turns, react_state"
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _require_job_status(status: str) -> str:
    raw = status.value if isinstance(status, JobStatus) else str(status)
    if raw not in _JOB_STATUSES:
        raise InvalidJobStatusError(
            f"Invalid job status {raw!r}. Allowed: queued|running|waiting_approval|done|failed|cancelled."
        )
    return raw


def _require_phase_status(status: str) -> str:
    raw = status.value if isinstance(status, PhaseStatus) else str(status)
    if raw not in _PHASE_STATUSES:
        raise InvalidJobStatusError(
            f"Invalid phase status {raw!r}. Allowed: queued|running|waiting_approval|done|failed|cancelled."
        )
    return raw


def _require_react_state(react_state: Optional[Any]) -> Optional[str]:
    if react_state is None or react_state == "":
        return None
    raw = react_state.value if isinstance(react_state, ReactState) else str(react_state)
    if raw not in _REACT_STATES:
        raise InvalidJobStatusError(
            f"Invalid react_state {raw!r}. Allowed: THINKING|CALLING_TOOLS|PARKED|DONE|FAILED."
        )
    return raw


def packet_to_json(packet: Optional[HandoffPacket]) -> Optional[str]:
    if packet is None:
        return None
    return packet.model_dump_json()


class JobRepositoryMixin:
    """CRUD for durable Job and Phase rows on SQLiteStateStore."""

    def _job_from_row(self, row: Any) -> Job:
        return Job(
            id=row["id"],
            goal=row["goal"],
            status=row["status"],
            budget_max_phases=int(row["budget_max_phases"]),
            budget_max_handoffs=int(row["budget_max_handoffs"]),
            budget_max_ollama_slots=int(row["budget_max_ollama_slots"]),
            current_phase_id=row["current_phase_id"],
            template_id=row["template_id"],
            session_id=row["session_id"],
            agent_id=row["agent_id"],
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )

    def _phase_from_row(self, row: Any) -> Phase:
        return Phase(
            id=row["id"],
            job_id=row["job_id"],
            name=row["name"],
            index=int(row["index"]),
            assigned_agent_id=row["assigned_agent_id"],
            status=row["status"],
            success_rule=row["success_rule"] or "",
            verify_checker=row["verify_checker"] or None,
            input_packet_json=row["input_packet_json"],
            output_packet_json=row["output_packet_json"],
            parent_phase_id=row["parent_phase_id"],
            max_turns=int(row["max_turns"]),
            react_state=row["react_state"],
        )

    def create_job(self, job: Job, phases: Sequence[Phase] | None = None) -> Job:
        """Persist a job and optional linear phases in one transaction."""
        status = _require_job_status(job.status)
        phase_list = list(phases or [])
        for phase in phase_list:
            _require_phase_status(phase.status)
            _require_react_state(phase.react_state)
            if phase.job_id != job.id:
                raise MissingParentJobError(
                    f"Phase {phase.id} job_id {phase.job_id!r} does not match job {job.id!r}."
                )

        now = _utc_iso()
        created_at = job.created_at.isoformat() if isinstance(job.created_at, datetime) else now
        updated_at = job.updated_at.isoformat() if isinstance(job.updated_at, datetime) else now
        conn = self._get_connection()
        try:
            conn.execute(
                f"""
                INSERT INTO jobs ({_JOB_COLUMNS})
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.goal,
                    status,
                    int(job.budget_max_phases),
                    int(job.budget_max_handoffs),
                    int(job.budget_max_ollama_slots),
                    job.current_phase_id,
                    job.template_id,
                    job.session_id,
                    job.agent_id,
                    created_at,
                    updated_at,
                ),
            )
            for phase in phase_list:
                self._insert_phase(conn, phase)
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()
        return self.get_job(job.id)

    def _insert_phase(self, conn: Any, phase: Phase) -> None:
        parent = conn.execute("SELECT id FROM jobs WHERE id = ?", (phase.job_id,)).fetchone()
        if parent is None:
            raise MissingParentJobError(f"Cannot write phase {phase.id}: parent job {phase.job_id} is missing.")
        status = _require_phase_status(phase.status)
        react_state = _require_react_state(phase.react_state)
        conn.execute(
            f"""
            INSERT INTO phases ({_PHASE_COLUMNS})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                phase.id,
                phase.job_id,
                phase.name,
                int(phase.index),
                phase.assigned_agent_id,
                status,
                phase.success_rule,
                phase.verify_checker,
                phase.input_packet_json,
                phase.output_packet_json,
                phase.parent_phase_id,
                int(phase.max_turns),
                react_state,
            ),
        )

    def create_phase(self, phase: Phase) -> Phase:
        """Insert a single phase. Rejects missing parent job and invalid status."""
        _require_phase_status(phase.status)
        _require_react_state(phase.react_state)
        conn = self._get_connection()
        try:
            self._insert_phase(conn, phase)
            conn.commit()
        except MissingParentJobError:
            conn.rollback()
            raise
        finally:
            if self._mem_conn is None:
                conn.close()
        return self.get_phase(phase.id)

    def get_job(self, job_id: str) -> Job:
        conn = self._get_connection()
        try:
            row = conn.execute(
                f"SELECT {_JOB_COLUMNS} FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                raise JobNotFoundError(f"Job {job_id} not found.")
            return self._job_from_row(row)
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_phase(self, phase_id: str) -> Phase:
        conn = self._get_connection()
        try:
            row = conn.execute(
                f"SELECT {_PHASE_COLUMNS} FROM phases WHERE id = ?",
                (phase_id,),
            ).fetchone()
            if row is None:
                raise PhaseNotFoundError(f"Phase {phase_id} not found.")
            return self._phase_from_row(row)
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_jobs_for_session(self, session_id: str) -> List[Job]:
        """Jobs for a chat session, newest first. Used to resume an open job."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                f"SELECT {_JOB_COLUMNS} FROM jobs WHERE session_id = ? ORDER BY created_at DESC",
                (session_id,),
            ).fetchall()
            return [self._job_from_row(row) for row in rows]
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_phases_for_job(self, job_id: str) -> List[Phase]:
        """Phases for a job ordered by linear index [REQ-ORCH-033]."""
        conn = self._get_connection()
        try:
            parent = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if parent is None:
                raise JobNotFoundError(f"Job {job_id} not found.")
            rows = conn.execute(
                f'SELECT {_PHASE_COLUMNS} FROM phases WHERE job_id = ? ORDER BY "index" ASC',
                (job_id,),
            ).fetchall()
            return [self._phase_from_row(row) for row in rows]
        finally:
            if self._mem_conn is None:
                conn.close()

    def update_job_status(
        self,
        job_id: str,
        status: str,
        current_phase_id: Optional[str] = None,
    ) -> Job:
        status_value = _require_job_status(status)
        now = _utc_iso()
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE jobs
                SET status = ?, current_phase_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (status_value, current_phase_id, now, job_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                raise JobNotFoundError(f"Job {job_id} not found.")
        finally:
            if self._mem_conn is None:
                conn.close()
        return self.get_job(job_id)

    def update_job(self, job: Job) -> Job:
        status_value = _require_job_status(job.status)
        now = _utc_iso()
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE jobs
                SET goal = ?, status = ?, budget_max_phases = ?, budget_max_handoffs = ?,
                    budget_max_ollama_slots = ?, current_phase_id = ?, template_id = ?,
                    session_id = ?, agent_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    job.goal,
                    status_value,
                    int(job.budget_max_phases),
                    int(job.budget_max_handoffs),
                    int(job.budget_max_ollama_slots),
                    job.current_phase_id,
                    job.template_id,
                    job.session_id,
                    job.agent_id,
                    now,
                    job.id,
                ),
            )
            conn.commit()
            if cur.rowcount == 0:
                raise JobNotFoundError(f"Job {job.id} not found.")
        finally:
            if self._mem_conn is None:
                conn.close()
        return self.get_job(job.id)

    def update_phase(self, phase: Phase) -> Phase:
        status_value = _require_phase_status(phase.status)
        react_state = _require_react_state(phase.react_state)
        conn = self._get_connection()
        try:
            parent = conn.execute("SELECT id FROM jobs WHERE id = ?", (phase.job_id,)).fetchone()
            if parent is None:
                raise MissingParentJobError(f"Cannot update phase {phase.id}: parent job {phase.job_id} is missing.")
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE phases
                SET name = ?, "index" = ?, assigned_agent_id = ?, status = ?, success_rule = ?,
                    verify_checker = ?, input_packet_json = ?, output_packet_json = ?,
                    parent_phase_id = ?, max_turns = ?, react_state = ?
                WHERE id = ?
                """,
                (
                    phase.name,
                    int(phase.index),
                    phase.assigned_agent_id,
                    status_value,
                    phase.success_rule,
                    phase.verify_checker,
                    phase.input_packet_json,
                    phase.output_packet_json,
                    phase.parent_phase_id,
                    int(phase.max_turns),
                    react_state,
                    phase.id,
                ),
            )
            conn.commit()
            if cur.rowcount == 0:
                raise PhaseNotFoundError(f"Phase {phase.id} not found.")
        finally:
            if self._mem_conn is None:
                conn.close()
        return self.get_phase(phase.id)


    def save_job_phase_checkpoint(
        self,
        *,
        job_id: str,
        phase_id: Optional[str],
        phase_index: int,
        verifier_status: str,
        hitl_park_state: bool = False,
        matched_capability_ids: Optional[List[str]] = None,
        memory_fact_ids: Optional[List[str]] = None,
    ) -> JobPhaseCheckpoint:
        """Append a durable phase-commit checkpoint [REQ-RESUME-001 / REQ-CATJOB-002 / CARD-226]."""
        cp_id = f"jpc_{uuid.uuid4().hex[:12]}"
        now = _utc_iso()
        status = str(verifier_status or "skipped_no_checker")
        # Inherit prior matched IDs when caller omits (resume stability).
        ids = list(matched_capability_ids) if matched_capability_ids is not None else None
        if ids is None:
            prior = self.get_latest_job_phase_checkpoint(job_id)
            ids = list(prior.matched_capability_ids) if prior else []
        ids_json = json.dumps(list(ids))
        # Memory refs: explicit list wins; else inherit prior checkpoint refs [REQ-JPMEM-002].
        mem_ids = list(memory_fact_ids) if memory_fact_ids is not None else None
        if mem_ids is None:
            prior = self.get_latest_job_phase_checkpoint(job_id)
            mem_ids = list(prior.memory_fact_ids) if prior else []
        mem_json = json.dumps(list(mem_ids))
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO job_phase_checkpoints (
                    id, job_id, phase_id, phase_index, verifier_status,
                    hitl_park_state, corrupt, matched_capability_ids_json,
                    memory_fact_ids_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    cp_id,
                    job_id,
                    phase_id,
                    int(phase_index),
                    status,
                    1 if hitl_park_state else 0,
                    ids_json,
                    mem_json,
                    now,
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()
        return self.get_latest_job_phase_checkpoint(job_id)  # type: ignore[return-value]

    def get_latest_job_phase_checkpoint(self, job_id: str) -> Optional[JobPhaseCheckpoint]:
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT id, job_id, phase_id, phase_index, verifier_status,
                       hitl_park_state, corrupt, matched_capability_ids_json,
                       memory_fact_ids_json, created_at
                FROM job_phase_checkpoints
                WHERE job_id = ?
                ORDER BY created_at DESC, rowid DESC
                LIMIT 1
                """,
                (job_id,),
            ).fetchone()
            if row is None:
                return None
            raw_ids = []
            raw_mem = []
            try:
                keys = row.keys()
            except Exception:
                keys = []
            if "matched_capability_ids_json" in keys:
                try:
                    raw_ids = json.loads(row["matched_capability_ids_json"] or "[]")
                except Exception:
                    raw_ids = []
            if "memory_fact_ids_json" in keys:
                try:
                    raw_mem = json.loads(row["memory_fact_ids_json"] or "[]")
                except Exception:
                    raw_mem = []
            return JobPhaseCheckpoint(
                id=row["id"],
                job_id=row["job_id"],
                phase_id=row["phase_id"],
                phase_index=int(row["phase_index"]),
                verifier_status=row["verifier_status"] or "skipped_no_checker",
                hitl_park_state=bool(row["hitl_park_state"]),
                corrupt=bool(row["corrupt"]),
                matched_capability_ids=list(raw_ids or []),
                memory_fact_ids=list(raw_mem or []),
                created_at=_parse_dt(row["created_at"]),
            )
        finally:
            if self._mem_conn is None:
                conn.close()


    def list_job_phase_checkpoints(self, job_id: str, limit: int = 100) -> List[JobPhaseCheckpoint]:
        """All durable checkpoints for a job (oldest first) [CARD-227]."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT id, job_id, phase_id, phase_index, verifier_status,
                       hitl_park_state, corrupt, matched_capability_ids_json,
                       memory_fact_ids_json, created_at
                FROM job_phase_checkpoints
                WHERE job_id = ?
                ORDER BY created_at ASC, rowid ASC
                LIMIT ?
                """,
                (job_id, int(limit)),
            ).fetchall()
            out: List[JobPhaseCheckpoint] = []
            for row in rows:
                raw_ids = []
                raw_mem = []
                try:
                    keys = row.keys()
                except Exception:
                    keys = []
                if "matched_capability_ids_json" in keys:
                    try:
                        raw_ids = json.loads(row["matched_capability_ids_json"] or "[]")
                    except Exception:
                        raw_ids = []
                if "memory_fact_ids_json" in keys:
                    try:
                        raw_mem = json.loads(row["memory_fact_ids_json"] or "[]")
                    except Exception:
                        raw_mem = []
                out.append(
                    JobPhaseCheckpoint(
                        id=row["id"],
                        job_id=row["job_id"],
                        phase_id=row["phase_id"],
                        phase_index=int(row["phase_index"]),
                        verifier_status=row["verifier_status"] or "skipped_no_checker",
                        hitl_park_state=bool(row["hitl_park_state"]),
                        corrupt=bool(row["corrupt"]),
                        matched_capability_ids=list(raw_ids or []),
                        memory_fact_ids=list(raw_mem or []),
                        created_at=_parse_dt(row["created_at"]),
                    )
                )
            return out
        finally:
            if self._mem_conn is None:
                conn.close()

    def mark_checkpoint_corrupt(self, job_id: str) -> Optional[JobPhaseCheckpoint]:
        """Mark the latest checkpoint corrupt (forces replan on resume) [REQ-RESUME-002]."""
        latest = self.get_latest_job_phase_checkpoint(job_id)
        if latest is None:
            return None
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE job_phase_checkpoints SET corrupt = 1 WHERE id = ?",
                (latest.id,),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()
        return self.get_latest_job_phase_checkpoint(job_id)

