"""Trustable Learning OS progress summary for non-Studio surfaces [CARD-441].

Aggregates durable course / mastery / due state from education_* stores.
Never invents mastery percentages when the ledger is empty or the read fails.
Education Studio chrome stays; this module is the Tutor/Wiki progress source.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


PROGRESS_SKILL_HINT = "progress-summary"
PROGRESS_HTTP_CONTRACT = "GET /api/education/progress"


def _grade_bucket(row: Dict[str, Any]) -> str:
    g = str(row.get("grade") or "unseen").strip().lower()
    if g in ("pass", "passed", "correct"):
        return "pass"
    if g in ("miss", "fail", "failed", "incorrect"):
        return "miss"
    return "unseen"


def summarize_mastery_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Honest mastery counts from ledger rows (no invented % when empty)."""
    items = [r for r in (rows or []) if isinstance(r, dict)]
    pass_n = miss_n = unseen_n = 0
    for r in items:
        bucket = _grade_bucket(r)
        if bucket == "pass":
            pass_n += 1
        elif bucket == "miss":
            miss_n += 1
        else:
            unseen_n += 1
    graded = pass_n + miss_n
    # Only report a ratio when at least one graded item exists.
    mastery_pct: Optional[float] = None
    if graded > 0:
        mastery_pct = round(100.0 * pass_n / graded, 1)
    empty = len(items) == 0
    return {
        "item_count": len(items),
        "pass_count": pass_n,
        "miss_count": miss_n,
        "unseen_count": unseen_n,
        "graded_count": graded,
        "mastery_pct": mastery_pct,
        "empty": empty,
        "empty_state": "No mastery items." if empty else None,
    }


def summarize_due_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    items = [r for r in (rows or []) if isinstance(r, dict)]
    empty = len(items) == 0
    return {
        "count": len(items),
        "empty": empty,
        "empty_state": "No due reviews." if empty else None,
        "item_ids": [str(r.get("item_id") or "") for r in items if r.get("item_id")],
    }


def summarize_courses(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    courses = [r for r in (rows or []) if isinstance(r, dict)]
    active = [
        c
        for c in courses
        if str(c.get("status") or "").strip().lower() in ("active", "in_progress", "started")
    ]
    # Prefer explicit active; else most recently updated / first row as "current"
    current = active[0] if active else (courses[0] if courses else None)
    empty = len(courses) == 0
    return {
        "count": len(courses),
        "active_count": len(active),
        "empty": empty,
        "empty_state": "No courses." if empty else None,
        "courses": courses,
        "current": current,
    }


def build_progress_summary(
    memory_repo: Any,
    *,
    agent_id: str = "tutor",
    topic_id: str = "",
    course_id: str = "",
    mastery_limit: int = 200,
    course_limit: int = 50,
) -> Dict[str, Any]:
    """Assemble trustable progress from Learning OS stores.

    On repository failures, returns ``success=False`` with an error string —
    never a decorative 100% mastery bar.
    """
    from src.application.education.course import course_chrome_snapshot

    try:
        courses_raw: List[Dict[str, Any]] = []
        if hasattr(memory_repo, "list_education_courses"):
            courses_raw = list(memory_repo.list_education_courses(limit=course_limit) or [])

        mastery_raw: List[Dict[str, Any]] = []
        if hasattr(memory_repo, "list_education_mastery"):
            mastery_raw = list(memory_repo.list_education_mastery(limit=mastery_limit) or [])

        due_raw: List[Dict[str, Any]] = []
        if hasattr(memory_repo, "list_due_education_mastery"):
            due_raw = list(memory_repo.list_due_education_mastery(limit=mastery_limit) or [])

        course_summary = summarize_courses(courses_raw)
        # Prefer binding topic/course when provided
        resolved_course_id = (course_id or "").strip()
        resolved_topic = (topic_id or "").strip()
        current = course_summary.get("current")
        if resolved_course_id and hasattr(memory_repo, "get_education_course"):
            bound = memory_repo.get_education_course(resolved_course_id)
            if bound:
                current = bound
                resolved_topic = resolved_topic or str(bound.get("topic_id") or "")
        elif resolved_topic and hasattr(memory_repo, "get_education_course_by_topic"):
            bound = memory_repo.get_education_course_by_topic(
                resolved_topic, prefer_active=True
            ) or memory_repo.get_education_course_by_topic(
                resolved_topic, prefer_active=False
            )
            if bound:
                current = bound
                resolved_course_id = str(bound.get("course_id") or "")

        if current and not resolved_topic:
            resolved_topic = str(current.get("topic_id") or "")
        if current and not resolved_course_id:
            resolved_course_id = str(current.get("course_id") or "")

        # Topic-scoped mastery when we have a topic
        scoped_mastery = mastery_raw
        if resolved_topic:
            scoped_mastery = [
                r
                for r in mastery_raw
                if str(r.get("topic") or "") == resolved_topic
            ]
            if not scoped_mastery:
                # Honest: show global ledger when topic has zero rows (do not invent)
                scoped_mastery = []

        mastery_summary = summarize_mastery_rows(scoped_mastery if resolved_topic else mastery_raw)
        # When topic scoped empty but global has items, still report global counts under "all"
        mastery_all = summarize_mastery_rows(mastery_raw)
        due_summary = summarize_due_rows(due_raw)

        chrome = course_chrome_snapshot(
            memory_repo,
            topic_id=resolved_topic,
            course_id=resolved_course_id,
            mastery_limit=min(20, mastery_limit),
        )

        learner: Optional[Dict[str, Any]] = None
        try:
            from src.application.education.learner_model import summarize_learner_model

            learner = summarize_learner_model(memory_repo)
        except Exception:  # noqa: BLE001
            learner = None

        empty = bool(course_summary.get("empty")) and bool(mastery_all.get("empty"))
        return {
            "success": True,
            "agent_id": agent_id,
            "skill_hint": PROGRESS_SKILL_HINT,
            "http_contract": PROGRESS_HTTP_CONTRACT,
            "sources": {
                "course": "GET /api/education/course (+ list_education_courses)",
                "mastery": "GET /api/education/mastery",
                "due": "GET /api/education/mastery/due",
                "learner": "GET /api/education/learner",
            },
            "topic": resolved_topic or None,
            "course_id": resolved_course_id or None,
            "course": course_summary,
            "current_course": current,
            "chrome": chrome,
            "mastery": mastery_summary,
            "mastery_all": mastery_all,
            "due": due_summary,
            "learner": learner,
            "empty": empty,
            "empty_state": (
                "No course or mastery progress yet." if empty else None
            ),
            "studio_required": False,
            "studio_chrome_retained": True,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "agent_id": agent_id,
            "error": f"progress summary failed: {exc}",
            "durable": False,
            "skill_hint": PROGRESS_SKILL_HINT,
            "http_contract": PROGRESS_HTTP_CONTRACT,
            "mastery": {
                "item_count": 0,
                "pass_count": 0,
                "miss_count": 0,
                "unseen_count": 0,
                "graded_count": 0,
                "mastery_pct": None,
                "empty": True,
                "empty_state": "Progress unavailable.",
            },
            "due": {"count": 0, "empty": True, "empty_state": "Progress unavailable."},
            "course": {"count": 0, "active_count": 0, "empty": True, "empty_state": "Progress unavailable."},
            "empty": True,
            "empty_state": "Progress unavailable.",
            "studio_required": False,
            "studio_chrome_retained": True,
        }
