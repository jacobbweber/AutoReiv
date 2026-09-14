"""Education course pipeline ops for agent memory.db [CARD-320].

Durable course row beside education_mastery — never storage.db, never a second tutor DB.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS education_course (
    course_id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    current_step TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_education_course_topic ON education_course(topic_id);
CREATE INDEX IF NOT EXISTS idx_education_course_status ON education_course(status);
"""


def ensure_education_course_schema(conn) -> None:
    conn.executescript(SCHEMA_SQL)


def _now_s(now: Optional[datetime] = None) -> str:
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_course(row) -> Dict[str, Any]:
    d = dict(row)
    raw = d.get("steps_json") or "[]"
    try:
        steps = json.loads(raw) if isinstance(raw, str) else list(raw)
    except json.JSONDecodeError:
        steps = []
    if not isinstance(steps, list):
        steps = []
    return {
        "course_id": d.get("course_id"),
        "topic_id": d.get("topic_id"),
        "steps": steps,
        "steps_json": raw if isinstance(raw, str) else json.dumps(steps),
        "current_step": d.get("current_step"),
        "status": d.get("status") or "active",
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
    }


def upsert_education_course(
    self,
    *,
    course_id: Optional[str] = None,
    topic_id: str,
    steps: Sequence[str],
    current_step: str,
    status: str = "active",
    now: Optional[datetime] = None,
) -> str:
    cid = (course_id or "").strip() or f"course_{uuid.uuid4().hex[:12]}"
    topic = (topic_id or "").strip()
    if not topic:
        raise ValueError("topic_id required")
    step_list = [str(s).strip() for s in steps if str(s).strip()]
    if not step_list:
        raise ValueError("steps required")
    cur = (current_step or "").strip() or step_list[0]
    if cur not in step_list:
        step_list = list(step_list) + [cur]
    st = (status or "active").strip() or "active"
    stamp = _now_s(now)
    payload = json.dumps(step_list)
    with self.get_connection() as conn:
        ensure_education_course_schema(conn)
        conn.execute(
            """
            INSERT INTO education_course (
                course_id, topic_id, steps_json, current_step, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(course_id) DO UPDATE SET
                topic_id = excluded.topic_id,
                steps_json = excluded.steps_json,
                current_step = excluded.current_step,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (cid, topic, payload, cur, st, stamp, stamp),
        )
    return cid


def get_education_course(self, course_id: str) -> Optional[Dict[str, Any]]:
    with self.get_connection() as conn:
        ensure_education_course_schema(conn)
        row = conn.execute(
            "SELECT * FROM education_course WHERE course_id = ?",
            (course_id,),
        ).fetchone()
        return _row_to_course(row) if row else None


def get_education_course_by_topic(
    self, topic_id: str, *, prefer_active: bool = True
) -> Optional[Dict[str, Any]]:
    topic = (topic_id or "").strip()
    if not topic:
        return None
    with self.get_connection() as conn:
        ensure_education_course_schema(conn)
        if prefer_active:
            row = conn.execute(
                """
                SELECT * FROM education_course
                WHERE topic_id = ? AND status = 'active'
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (topic,),
            ).fetchone()
            if row:
                return _row_to_course(row)
        row = conn.execute(
            """
            SELECT * FROM education_course
            WHERE topic_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (topic,),
        ).fetchone()
        return _row_to_course(row) if row else None


def list_education_courses(self, limit: int = 100) -> List[Dict[str, Any]]:
    with self.get_connection() as conn:
        ensure_education_course_schema(conn)
        rows = conn.execute(
            """
            SELECT * FROM education_course
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_row_to_course(r) for r in rows]


def update_education_course_step(
    self,
    *,
    course_id: str,
    current_step: str,
    status: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    stamp = _now_s(now)
    with self.get_connection() as conn:
        ensure_education_course_schema(conn)
        if status is not None:
            conn.execute(
                """
                UPDATE education_course
                SET current_step = ?, status = ?, updated_at = ?
                WHERE course_id = ?
                """,
                (current_step, status, stamp, course_id),
            )
        else:
            conn.execute(
                """
                UPDATE education_course
                SET current_step = ?, updated_at = ?
                WHERE course_id = ?
                """,
                (current_step, stamp, course_id),
            )
    row = self.get_education_course(course_id)
    if not row:
        raise KeyError(f"education course not found: {course_id}")
    return row


def install_on(cls):
    """Bind course methods onto AgentMemoryRepository."""
    cls.upsert_education_course = upsert_education_course
    cls.get_education_course = get_education_course
    cls.get_education_course_by_topic = get_education_course_by_topic
    cls.list_education_courses = list_education_courses
    cls.update_education_course_step = update_education_course_step
    return cls
