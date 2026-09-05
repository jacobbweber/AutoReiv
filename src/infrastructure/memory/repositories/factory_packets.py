"""
Factory Packet and Job Durable SQLite Repository [REQ-FACT-003, REQ-FACT-012].

Persists and queries typed inter-room packets, training jobs, and 4-stage evaluation runs.
"""

import json
from datetime import datetime, timezone
from typing import Any, List, Optional

from src.domain.orchestration.factory_packets import (
    FactoryEvalRun,
    FactoryJob,
    FactoryPacket,
)
from src.infrastructure.memory.connection import SQLiteConnectionManager


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


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class FactoryPacketRepositoryMixin:
    """Repository mixin for Factory jobs, packets, and evaluation runs."""

    def save_job(self, job: FactoryJob) -> None:
        conn = self._get_connection()
        try:
            created_at = job.created_at.isoformat() if job.created_at else _utc_iso()
            updated_at = job.updated_at.isoformat() if job.updated_at else _utc_iso()
            conn.execute(
                """
                INSERT INTO factory_jobs (
                    id, target_agent_id, session_id, status, seed_intent,
                    target_host, environment_manifest_json, active_graph_id,
                    current_node_id, budget_max_cycles, cycles_consumed,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    environment_manifest_json=excluded.environment_manifest_json,
                    current_node_id=excluded.current_node_id,
                    cycles_consumed=excluded.cycles_consumed,
                    updated_at=excluded.updated_at;
                """,
                (
                    job.id,
                    job.target_agent_id,
                    job.session_id,
                    job.status,
                    job.seed_intent,
                    job.target_host,
                    job.environment_manifest_json,
                    job.active_graph_id,
                    job.current_node_id,
                    job.budget_max_cycles,
                    job.cycles_consumed,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def get_job(self, job_id: str) -> Optional[FactoryJob]:
        conn = self._get_connection()
        try:
            row = conn.execute("SELECT * FROM factory_jobs WHERE id = ?", (job_id,)).fetchone()
            if not row:
                return None
            return FactoryJob(
                id=row["id"],
                target_agent_id=row["target_agent_id"],
                session_id=row["session_id"],
                status=row["status"],
                seed_intent=row["seed_intent"],
                target_host=row["target_host"],
                environment_manifest_json=row["environment_manifest_json"],
                active_graph_id=row["active_graph_id"],
                current_node_id=row["current_node_id"],
                budget_max_cycles=int(row["budget_max_cycles"]),
                cycles_consumed=int(row["cycles_consumed"]),
                created_at=_parse_dt(row["created_at"]),
                updated_at=_parse_dt(row["updated_at"]),
            )
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def update_job_status(
        self,
        job_id: str,
        status: str,
        current_node_id: Optional[str] = None,
        cycles_consumed: Optional[int] = None,
        environment_manifest_json: Optional[str] = None,
    ) -> None:
        conn = self._get_connection()
        try:
            updates = ["status = ?", "updated_at = ?"]
            params: List[Any] = [status, _utc_iso()]

            if current_node_id is not None:
                updates.append("current_node_id = ?")
                params.append(current_node_id)
            if cycles_consumed is not None:
                updates.append("cycles_consumed = ?")
                params.append(cycles_consumed)
            if environment_manifest_json is not None:
                updates.append("environment_manifest_json = ?")
                params.append(environment_manifest_json)

            params.append(job_id)
            conn.execute(
                f"UPDATE factory_jobs SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            conn.commit()
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def list_jobs(self, status: Optional[str] = None, target_agent_id: Optional[str] = None) -> List[FactoryJob]:
        conn = self._get_connection()
        try:
            clauses = []
            params = []
            if status:
                clauses.append("status = ?")
                params.append(status)
            if target_agent_id:
                clauses.append("target_agent_id = ?")
                params.append(target_agent_id)

            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            rows = conn.execute(
                f"SELECT * FROM factory_jobs {where} ORDER BY created_at DESC",
                tuple(params),
            ).fetchall()

            return [
                FactoryJob(
                    id=row["id"],
                    target_agent_id=row["target_agent_id"],
                    session_id=row["session_id"],
                    status=row["status"],
                    seed_intent=row["seed_intent"],
                    target_host=row["target_host"],
                    environment_manifest_json=row["environment_manifest_json"],
                    active_graph_id=row["active_graph_id"],
                    current_node_id=row["current_node_id"],
                    budget_max_cycles=int(row["budget_max_cycles"]),
                    cycles_consumed=int(row["cycles_consumed"]),
                    created_at=_parse_dt(row["created_at"]),
                    updated_at=_parse_dt(row["updated_at"]),
                )
                for row in rows
            ]
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def save_packet(self, packet: FactoryPacket) -> None:
        conn = self._get_connection()
        try:
            created_at = packet.created_at.isoformat() if packet.created_at else _utc_iso()
            payload_str = json.dumps(packet.payload)
            conn.execute(
                """
                INSERT INTO factory_packets (
                    id, job_id, packet_type, sender_role, recipient_role,
                    node_id, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload_json=excluded.payload_json;
                """,
                (
                    packet.id,
                    packet.job_id,
                    packet.packet_type,
                    packet.sender_role,
                    packet.recipient_role,
                    packet.node_id,
                    payload_str,
                    created_at,
                ),
            )
            conn.commit()
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def list_packets(
        self,
        job_id: str,
        packet_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> List[FactoryPacket]:
        conn = self._get_connection()
        try:
            clauses = ["job_id = ?"]
            params: List[Any] = [job_id]
            if packet_type:
                clauses.append("packet_type = ?")
                params.append(packet_type)
            if node_id:
                clauses.append("node_id = ?")
                params.append(node_id)

            where = f"WHERE {' AND '.join(clauses)}"
            rows = conn.execute(
                f"SELECT * FROM factory_packets {where} ORDER BY created_at ASC",
                tuple(params),
            ).fetchall()

            return [
                FactoryPacket(
                    id=row["id"],
                    job_id=row["job_id"],
                    packet_type=row["packet_type"],
                    sender_role=row["sender_role"],
                    recipient_role=row["recipient_role"],
                    node_id=row["node_id"],
                    payload=json.loads(row["payload_json"]),
                    created_at=_parse_dt(row["created_at"]),
                )
                for row in rows
            ]
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def save_eval_run(self, eval_run: FactoryEvalRun) -> None:
        conn = self._get_connection()
        try:
            created_at = eval_run.created_at.isoformat() if eval_run.created_at else _utc_iso()
            conn.execute(
                """
                INSERT INTO factory_eval_runs (
                    id, job_id, tool_name, stage_1_functional, stage_2_safety,
                    stage_3_idempotency, stage_4_critic, stdout_log, stderr_log,
                    critic_notes, duration_ms, overall_passed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    stage_1_functional=excluded.stage_1_functional,
                    stage_2_safety=excluded.stage_2_safety,
                    stage_3_idempotency=excluded.stage_3_idempotency,
                    stage_4_critic=excluded.stage_4_critic,
                    stdout_log=excluded.stdout_log,
                    stderr_log=excluded.stderr_log,
                    critic_notes=excluded.critic_notes,
                    duration_ms=excluded.duration_ms,
                    overall_passed=excluded.overall_passed;
                """,
                (
                    eval_run.id,
                    eval_run.job_id,
                    eval_run.tool_name,
                    1 if eval_run.stage_1_functional else 0,
                    1 if eval_run.stage_2_safety else 0,
                    1 if eval_run.stage_3_idempotency else 0,
                    1 if eval_run.stage_4_critic else 0,
                    eval_run.stdout_log or "",
                    eval_run.stderr_log or "",
                    eval_run.critic_notes or "",
                    float(eval_run.duration_ms),
                    1 if eval_run.overall_passed else 0,
                    created_at,
                ),
            )
            conn.commit()
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def list_eval_runs(self, job_id: str, tool_name: Optional[str] = None) -> List[FactoryEvalRun]:
        conn = self._get_connection()
        try:
            clauses = ["job_id = ?"]
            params: List[Any] = [job_id]
            if tool_name:
                clauses.append("tool_name = ?")
                params.append(tool_name)

            where = f"WHERE {' AND '.join(clauses)}"
            rows = conn.execute(
                f"SELECT * FROM factory_eval_runs {where} ORDER BY created_at ASC",
                tuple(params),
            ).fetchall()

            return [
                FactoryEvalRun(
                    id=row["id"],
                    job_id=row["job_id"],
                    tool_name=row["tool_name"],
                    stage_1_functional=bool(row["stage_1_functional"]),
                    stage_2_safety=bool(row["stage_2_safety"]),
                    stage_3_idempotency=bool(row["stage_3_idempotency"]),
                    stage_4_critic=bool(row["stage_4_critic"]),
                    stdout_log=row["stdout_log"],
                    stderr_log=row["stderr_log"],
                    critic_notes=row["critic_notes"],
                    duration_ms=float(row["duration_ms"]),
                    overall_passed=bool(row["overall_passed"]),
                    created_at=_parse_dt(row["created_at"]),
                )
                for row in rows
            ]
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()


class FactoryPacketRepository(FactoryPacketRepositoryMixin):
    """Standalone wrapper accepting any SQLiteConnectionManager or SQLiteStateStore instance."""

    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._cm = connection_manager

    def _get_connection(self):
        return self._cm._get_connection()

    @property
    def _mem_conn(self):
        return getattr(self._cm, "_mem_conn", None)
