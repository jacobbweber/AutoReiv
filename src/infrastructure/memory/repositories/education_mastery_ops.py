"""Education mastery ledger ops for agent memory.db [CARD-242]."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS education_mastery (
    item_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    wiki_path TEXT NOT NULL,
    prompt TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    grade TEXT NOT NULL DEFAULT 'unseen',
    interval_stage INTEGER NOT NULL DEFAULT 0,
    next_due TEXT,
    last_graded_at TEXT,
    miss_count INTEGER NOT NULL DEFAULT 0,
    pass_count INTEGER NOT NULL DEFAULT 0,
    pending_job_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_education_mastery_next_due ON education_mastery(next_due);
CREATE INDEX IF NOT EXISTS idx_education_mastery_topic ON education_mastery(topic);
"""


def ensure_education_mastery_schema(conn) -> None:
    conn.executescript(SCHEMA_SQL)


def upsert_education_mastery(
    self,
    *,
    item_id: str,
    topic: str,
    wiki_path: str,
    prompt: str,
    expected_answer: str,
    grade: str = "unseen",
    next_due: Optional[str] = None,
    interval_stage: int = 0,
    pending_job_id: Optional[str] = None,
) -> str:
    mid = (item_id or "").strip() or f"edu_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with self.get_connection() as conn:
        ensure_education_mastery_schema(conn)
        conn.execute(
            """
            INSERT INTO education_mastery (
                item_id, topic, wiki_path, prompt, expected_answer, grade,
                interval_stage, next_due, pending_job_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                topic = excluded.topic,
                wiki_path = excluded.wiki_path,
                prompt = excluded.prompt,
                expected_answer = excluded.expected_answer,
                grade = excluded.grade,
                interval_stage = excluded.interval_stage,
                next_due = excluded.next_due,
                pending_job_id = COALESCE(excluded.pending_job_id, education_mastery.pending_job_id),
                updated_at = excluded.updated_at
            """,
            (
                mid,
                (topic or "").strip(),
                (wiki_path or "").strip(),
                (prompt or "").strip(),
                (expected_answer or "").strip(),
                (grade or "unseen").strip(),
                int(interval_stage or 0),
                next_due,
                pending_job_id,
                now,
                now,
            ),
        )
    return mid


def get_education_mastery(self, item_id: str) -> Optional[Dict[str, Any]]:
    with self.get_connection() as conn:
        ensure_education_mastery_schema(conn)
        row = conn.execute(
            "SELECT * FROM education_mastery WHERE item_id = ?",
            (item_id,),
        ).fetchone()
        return dict(row) if row else None


def list_education_mastery(self, limit: int = 200) -> List[Dict[str, Any]]:
    with self.get_connection() as conn:
        ensure_education_mastery_schema(conn)
        rows = conn.execute(
            """
            SELECT * FROM education_mastery
            ORDER BY COALESCE(next_due, created_at) ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_due_education_mastery(
    self,
    as_of: Optional[datetime] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    as_of_s = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with self.get_connection() as conn:
        ensure_education_mastery_schema(conn)
        rows = conn.execute(
            """
            SELECT * FROM education_mastery
            WHERE next_due IS NOT NULL AND next_due != '' AND next_due <= ?
            ORDER BY next_due ASC
            LIMIT ?
            """,
            (as_of_s, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def record_education_grade(
    self,
    *,
    item_id: str,
    correct: bool,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    from src.application.education.srs import next_due_after_grade

    existing = self.get_education_mastery(item_id)
    if not existing:
        raise KeyError(f"education mastery item not found: {item_id}")
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    stage = int(existing.get("interval_stage") or 0)
    new_stage, due = next_due_after_grade(correct=correct, interval_stage=stage, now=base)
    grade = "pass" if correct else "miss"
    now_s = base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    due_s = due.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    miss_count = int(existing.get("miss_count") or 0) + (0 if correct else 1)
    pass_count = int(existing.get("pass_count") or 0) + (1 if correct else 0)
    with self.get_connection() as conn:
        conn.execute(
            """
            UPDATE education_mastery SET
                grade = ?,
                interval_stage = ?,
                next_due = ?,
                last_graded_at = ?,
                miss_count = ?,
                pass_count = ?,
                pending_job_id = NULL,
                updated_at = ?
            WHERE item_id = ?
            """,
            (grade, new_stage, due_s, now_s, miss_count, pass_count, now_s, item_id),
        )
    row = self.get_education_mastery(item_id)
    assert row is not None
    return row


def mark_education_mastery_resurfaced(
    self,
    *,
    item_id: str,
    job_id: str,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    now_s = base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with self.get_connection() as conn:
        conn.execute(
            """
            UPDATE education_mastery SET
                pending_job_id = ?,
                updated_at = ?
            WHERE item_id = ?
            """,
            (job_id, now_s, item_id),
        )
    row = self.get_education_mastery(item_id)
    assert row is not None
    return row


def install_on(cls):
    """Bind mastery methods onto AgentMemoryRepository."""
    cls.upsert_education_mastery = upsert_education_mastery
    cls.get_education_mastery = get_education_mastery
    cls.list_education_mastery = list_education_mastery
    cls.list_due_education_mastery = list_due_education_mastery
    cls.record_education_grade = record_education_grade
    cls.mark_education_mastery_resurfaced = mark_education_mastery_resurfaced
    return cls
