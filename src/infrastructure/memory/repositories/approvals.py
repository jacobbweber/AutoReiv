"""
Human-In-The-Loop (HITL) Action Approvals Repository Mixin [REQ-SAFE-004, REQ-HITL-002].
"""

import json
import uuid
from typing import Any, Dict, List, Optional


class ApprovalRepositoryMixin:
    """Methods for creating, retrieving, and resolving HITL action approvals."""

    def create_approval(
        self,
        session_id: str,
        agent_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        routine_id: Optional[str] = None,
    ) -> str:
        """Record a pending tool execution awaiting operator approval."""
        conn = self._get_connection()
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        rid = str(routine_id or "").strip() or None
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO pending_approvals (id, session_id, agent_id, routine_id, tool_name, arguments_json, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending');
                """,
                (approval_id, session_id, agent_id, rid, tool_name, json.dumps(arguments)),
            )
            conn.commit()
            return approval_id
        finally:
            if self._mem_conn is None:
                conn.close()

    def _approval_from_row(self, r: Any, include_resolved: bool = False) -> Dict[str, Any]:
        keys = r.keys() if hasattr(r, "keys") else []
        routine_id = r["routine_id"] if "routine_id" in keys else None
        payload = {
            "id": r["id"],
            "session_id": r["session_id"],
            "agent_id": r["agent_id"],
            "routine_id": routine_id or None,
            "tool_name": r["tool_name"],
            "arguments": json.loads(r["arguments_json"]),
            "status": r["status"],
            "decision_reason": r["decision_reason"],
            "created_at": str(r["created_at"]),
        }
        if include_resolved:
            payload["resolved_at"] = str(r["resolved_at"]) if r["resolved_at"] else None
        return payload

    def get_pending_approvals(
        self,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve list of pending approvals, optionally filtered by session or agent."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            sid = str(session_id or "").strip()
            aid = str(agent_id or "").strip()
            select_sql = (
                "SELECT id, session_id, agent_id, routine_id, tool_name, arguments_json, "
                "status, decision_reason, created_at FROM pending_approvals "
            )
            if sid and aid:
                cur.execute(
                    select_sql
                    + "WHERE (session_id = ? OR session_id LIKE ? || '_child_%' OR session_id LIKE ? || '::phase::%') "
                    + "AND agent_id = ? AND status = 'pending' ORDER BY created_at ASC;",
                    (sid, sid, sid, aid),
                )
            elif sid:
                cur.execute(
                    select_sql
                    + "WHERE (session_id = ? OR session_id LIKE ? || '_child_%' OR session_id LIKE ? || '::phase::%') "
                    + "AND status = 'pending' ORDER BY created_at ASC;",
                    (sid, sid, sid),
                )
            elif aid:
                cur.execute(
                    select_sql + "WHERE agent_id = ? AND status = 'pending' ORDER BY created_at ASC;",
                    (aid,),
                )
            else:
                cur.execute(select_sql + "WHERE status = 'pending' ORDER BY created_at ASC;")
            return [self._approval_from_row(r) for r in cur.fetchall()]
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_approval(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific approval record."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, session_id, agent_id, routine_id, tool_name, arguments_json, status, "
                "decision_reason, created_at, resolved_at FROM pending_approvals WHERE id = ?;",
                (approval_id,),
            )
            r = cur.fetchone()
            if not r:
                return None
            return self._approval_from_row(r, include_resolved=True)
        finally:
            if self._mem_conn is None:
                conn.close()

    def resolve_approval(
        self,
        approval_id: str,
        decision: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Resolve a pending approval with 'approved' or 'rejected' decision."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE pending_approvals
                SET status = ?, decision_reason = ?, resolved_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending';
                """,
                (decision.lower(), reason, approval_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()
