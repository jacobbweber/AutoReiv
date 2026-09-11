"""Tool policy decision log repository [CARD-221 / REQ-TOOLPOL-004]."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ToolPolicyRepositoryMixin:
    """Persist Observability decision-log rows for tool policy verdicts."""

    def save_tool_policy_decision(self, row: Dict[str, Any]) -> None:
        conn = self._get_connection()  # type: ignore[attr-defined]
        try:
            conn.execute(
                """
                INSERT INTO tool_policy_decisions (
                    id, session_id, agent_id, tool_name, verdict, reason, policy_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row.get("session_id"),
                    row.get("agent_id"),
                    row["tool_name"],
                    row["verdict"],
                    row.get("reason"),
                    row.get("policy_source"),
                ),
            )
            conn.commit()
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def list_tool_policy_decisions(
        self,
        *,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)
        if agent_id:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(int(limit))
        conn = self._get_connection()  # type: ignore[attr-defined]
        try:
            cur = conn.execute(
                f"""
                SELECT id, session_id, agent_id, tool_name, verdict, reason,
                       policy_source, created_at
                FROM tool_policy_decisions
                {where}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params,
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()
