"""Standing journey durable correlation helpers [CARD-227]."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional


class StandingJourneyRepositoryMixin:
    """A2A parent/child links + standing journey resume/event log."""

    def save_job_a2a_link(self, *, parent_job_id: str, child_job_id: str) -> None:
        parent = str(parent_job_id or "").strip()
        child = str(child_job_id or "").strip()
        if not parent or not child:
            return
        conn = self._get_connection()  # type: ignore[attr-defined]
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO job_a2a_links (parent_job_id, child_job_id)
                VALUES (?, ?)
                """,
                (parent, child),
            )
            conn.commit()
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def list_job_a2a_children(self, parent_job_id: str) -> List[str]:
        parent = str(parent_job_id or "").strip()
        if not parent:
            return []
        conn = self._get_connection()  # type: ignore[attr-defined]
        try:
            rows = conn.execute(
                "SELECT child_job_id FROM job_a2a_links WHERE parent_job_id = ? ORDER BY created_at ASC",
                (parent,),
            ).fetchall()
            return [str(r[0]) for r in rows]
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def get_job_a2a_parent(self, child_job_id: str) -> Optional[str]:
        child = str(child_job_id or "").strip()
        if not child:
            return None
        conn = self._get_connection()  # type: ignore[attr-defined]
        try:
            row = conn.execute(
                "SELECT parent_job_id FROM job_a2a_links WHERE child_job_id = ? LIMIT 1",
                (child,),
            ).fetchone()
            return str(row[0]) if row else None
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def save_standing_journey_event(
        self,
        *,
        job_id: str,
        kind: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        eid = f"sje_{uuid.uuid4().hex[:12]}"
        conn = self._get_connection()  # type: ignore[attr-defined]
        try:
            conn.execute(
                """
                INSERT INTO standing_journey_events (id, job_id, kind, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (eid, str(job_id), str(kind), json.dumps(payload or {})),
            )
            conn.commit()
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()
        return eid

    def list_standing_journey_events(self, job_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        jid = str(job_id or "").strip()
        if not jid:
            return []
        conn = self._get_connection()  # type: ignore[attr-defined]
        try:
            cur = conn.execute(
                """
                SELECT id, job_id, kind, payload_json, created_at
                FROM standing_journey_events
                WHERE job_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (jid, int(limit)),
            )
            out: List[Dict[str, Any]] = []
            for row in cur.fetchall():
                try:
                    payload = json.loads(row["payload_json"] or "{}")
                except Exception:
                    payload = {}
                out.append(
                    {
                        "id": row["id"],
                        "job_id": row["job_id"],
                        "kind": row["kind"],
                        "payload": payload,
                        "created_at": row["created_at"],
                    }
                )
            return out
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()
