"""
Capability Gap Durable SQLite Repository [REQ-FACT-027].

Persists and queries detected agent capability gaps for the "Needs Training" backlog.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional

from src.domain.orchestration.capability_gaps import CapabilityGap


class CapabilityGapRepository:
    """Repository for managing agent capability gaps."""

    def __init__(
        self,
        connection_manager: Any = None,
        connection_factory: Optional[Callable[[], Any]] = None,
    ):
        self._cm = connection_manager
        self._connection_factory = connection_factory

    def _get_connection(self):
        if self._connection_factory:
            return self._connection_factory()
        if self._cm and hasattr(self._cm, "_get_connection"):
            return self._cm._get_connection()
        raise ValueError("CapabilityGapRepository requires connection_manager or connection_factory.")

    @property
    def _mem_conn(self):
        return getattr(self._cm, "_mem_conn", None)

    def create_gap(
        self,
        agent_id: str,
        turn_text: Optional[str] = None,
        identified_capability: Optional[str] = None,
        suggested_tool_name: Optional[str] = None,
        session_id: Optional[str] = None,
        user_prompt: Optional[str] = None,
        missing_capability: Optional[str] = None,
        context_summary: Optional[str] = None,
    ) -> CapabilityGap:
        effective_turn = turn_text or user_prompt or ""
        effective_cap = identified_capability or missing_capability or ""
        gap_id = f"gap_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO agent_capability_gaps (
                    id, agent_id, session_id, turn_text, identified_capability,
                    suggested_tool_name, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (gap_id, agent_id, session_id, effective_turn, effective_cap, suggested_tool_name, now_str),
            )
            conn.commit()
            return CapabilityGap(
                id=gap_id,
                agent_id=agent_id,
                session_id=session_id,
                turn_text=effective_turn,
                identified_capability=effective_cap,
                suggested_tool_name=suggested_tool_name,
                status="pending",
                created_at=now_str,
            )
        finally:
            if not self._connection_factory and getattr(self, "_mem_conn", None) is None and hasattr(conn, "close"):
                conn.close()

    def get_gap(self, gap_id: str) -> Optional[CapabilityGap]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, agent_id, session_id, turn_text, identified_capability,
                       suggested_tool_name, status, created_at
                FROM agent_capability_gaps WHERE id = ?
                """,
                (gap_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return CapabilityGap(
                id=row["id"],
                agent_id=row["agent_id"],
                session_id=row["session_id"],
                turn_text=row["turn_text"],
                identified_capability=row["identified_capability"],
                suggested_tool_name=row["suggested_tool_name"],
                status=row["status"],
                created_at=str(row["created_at"]),
            )
        finally:
            if not self._connection_factory and getattr(self, "_mem_conn", None) is None and hasattr(conn, "close"):
                conn.close()

    def list_gaps(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = "pending",
    ) -> List[CapabilityGap]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            query = "SELECT id, agent_id, session_id, turn_text, identified_capability, suggested_tool_name, status, created_at FROM agent_capability_gaps"
            params = []
            conditions = []
            if agent_id:
                conditions.append("agent_id = ?")
                params.append(agent_id)
            if status:
                conditions.append("status = ?")
                params.append(status)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY created_at DESC"

            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            return [
                CapabilityGap(
                    id=row["id"],
                    agent_id=row["agent_id"],
                    session_id=row["session_id"],
                    turn_text=row["turn_text"],
                    identified_capability=row["identified_capability"],
                    suggested_tool_name=row["suggested_tool_name"],
                    status=row["status"],
                    created_at=str(row["created_at"]),
                )
                for row in rows
            ]
        finally:
            if not self._connection_factory and getattr(self, "_mem_conn", None) is None and hasattr(conn, "close"):
                conn.close()

    def update_gap_status(self, gap_id: str, status: str) -> bool:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE agent_capability_gaps SET status = ? WHERE id = ?",
                (status, gap_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            if not self._connection_factory and getattr(self, "_mem_conn", None) is None and hasattr(conn, "close"):
                conn.close()

    def delete_gap(self, gap_id: str) -> bool:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM agent_capability_gaps WHERE id = ?",
                (gap_id,),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            if not self._connection_factory and getattr(self, "_mem_conn", None) is None and hasattr(conn, "close"):
                conn.close()
