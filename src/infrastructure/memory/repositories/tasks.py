"""
Task Management Repository Mixin.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class TaskRepositoryMixin:
    """Methods for creating, querying, updating, and deleting structured tasks."""

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        due_date: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        tid = task_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO tasks (id, title, description, status, priority, due_date, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (tid, title, description, priority, due_date, now, now),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()
        return {
            "id": tid,
            "title": title,
            "description": description,
            "status": "pending",
            "priority": priority,
            "due_date": due_date,
            "created_at": now,
            "updated_at": now,
        }

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT id, title, description, status, priority, due_date, created_at, updated_at FROM tasks WHERE 1=1"
        params: List[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        query += " ORDER BY created_at DESC"

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            if self._mem_conn is None:
                conn.close()

    def update_task_status(self, task_id: str, status: str) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, task_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            cur.execute(
                "SELECT id, title, description, status, priority, due_date, created_at, updated_at FROM tasks WHERE id = ?",
                (task_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_task(self, task_id: str) -> bool:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()
