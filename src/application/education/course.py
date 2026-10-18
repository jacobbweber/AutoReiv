"""Education Learning OS Course + Mastery pipeline [CARD-320].

Durable course in agent *_memory.db (education_course). Course pipeline is the
DEFAULT Ask path; mode-picker is secondary jump-to-step only. Mastery gate is
binary external only (grade_answer_binary). No Dual Coding chrome on this card.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from src.application.education.course_step_artifacts import (
    _course_note_meta as _course_note_meta,
)
from src.application.education.course_step_artifacts import (
    _nothing_written as _nothing_written,
)
from src.application.education.course_step_artifacts import (
    _write_step_artifact as _write_step_artifact,
)
from src.application.education.course_step_artifacts import (
    _write_step_artifact_body as _write_step_artifact_body,
)
from src.application.education.quiz_engine import grade_answer_binary

COURSE_KIND = "education_course"

# Ordered Learning OS default pipeline (CARD-320 baseline).
DEFAULT_COURSE_STEPS: tuple[str, ...] = (
    "priming",
    "retrieval",
    "elaboration",
    "construction",
    "application",
    "analysis",
    "environment",
    "retention",
)

# Ordered Learning OS pipeline with Dual Coding as an ordered step [CARD-321].
ORDERED_COURSE_STEPS: tuple[str, ...] = (
    "priming",
    "dual_coding",
    "retrieval",
    "elaboration",
    "construction",
    "application",
    "analysis",
    "environment",
    "retention",
)

# Steps that no longer exist. Courses stored before their removal may still list them; they are skipped
# without writing anything. "amplifiers" wrote filler wiki notes and filler quiz items [CARD-639].
RETIRED_COURSE_STEPS: frozenset[str] = frozenset({"amplifiers"})


def _live_steps(steps: Sequence[str]) -> List[str]:
    """Step names with blanks and retired steps removed [CARD-639]."""
    return [str(s).strip() for s in steps if str(s).strip() and str(s).strip() not in RETIRED_COURSE_STEPS]


# Steps allowed via mode-picker jump (includes all ordered steps + custom).
JUMPABLE_STEPS: frozenset[str] = frozenset(
    list(ORDERED_COURSE_STEPS) + ["custom"]
)


def is_course_pipeline_default() -> bool:
    """Course pipeline is the DEFAULT Studio path (mode-picker = jump-to-step)."""
    return True


def _normalize_topic(topic_id: str) -> str:
    return (topic_id or "").strip()


def start_or_resume_course(
    memory_repo: Any,
    *,
    topic_id: str,
    steps: Optional[Sequence[str]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Start a durable course or resume the active one for topic_id."""
    topic = _normalize_topic(topic_id)
    if not topic:
        raise ValueError("topic_id required")
    step_list = _live_steps(steps or DEFAULT_COURSE_STEPS)
    if not step_list:
        step_list = list(DEFAULT_COURSE_STEPS)

    existing = memory_repo.get_education_course_by_topic(topic, prefer_active=True)
    if existing and existing.get("status") == "active":
        return existing

    latest = memory_repo.get_education_course_by_topic(topic, prefer_active=False)
    if latest and latest.get("status") != "completed":
        if latest.get("status") != "active":
            return memory_repo.update_education_course_step(
                course_id=latest["course_id"],
                current_step=latest["current_step"],
                status="active",
                now=now,
            )
        return latest

    course_id = memory_repo.upsert_education_course(
        topic_id=topic,
        steps=step_list,
        current_step=step_list[0],
        status="active",
        now=now,
    )
    row = memory_repo.get_education_course(course_id)
    assert row is not None
    return row


def get_course(memory_repo: Any, *, course_id: str) -> Optional[Dict[str, Any]]:
    return memory_repo.get_education_course(course_id)


def jump_to_course_step(
    memory_repo: Any,
    *,
    course_id: str,
    step: str,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Secondary mode-picker: jump current_step without inventing a new course."""
    course = memory_repo.get_education_course(course_id)
    if not course:
        raise KeyError(f"education course not found: {course_id}")
    target = (step or "").strip().lower()
    if not target:
        raise ValueError("step required")
    if target in RETIRED_COURSE_STEPS:
        raise ValueError(f"course step removed: {target}")
    steps = list(course.get("steps") or DEFAULT_COURSE_STEPS)
    if target not in JUMPABLE_STEPS and target not in steps:
        raise ValueError(f"unknown course step: {target}")
    status = "active" if course.get("status") != "completed" else course.get("status")
    return memory_repo.update_education_course_step(
        course_id=course_id,
        current_step=target,
        status=status,
        now=now,
    )


def _next_step(steps: Sequence[str], current: str) -> Optional[str]:
    """Next step after current, skipping retired steps a stored course may still list [CARD-639]."""
    cur = (current or "").strip()
    ordered = [str(s).strip() for s in steps if str(s).strip()]
    live = _live_steps(ordered)
    if cur not in ordered:
        return live[0] if live else None
    for candidate in ordered[ordered.index(cur) + 1:]:
        if candidate not in RETIRED_COURSE_STEPS:
            return candidate
    return None



def complete_course_step(
    memory_repo: Any,
    *,
    course_id: str,
    wiki_tools_or_store: Any = None,
    teach_style: str = "",
    learner_explanation: Optional[str] = None,
    lab_submission: Optional[str] = None,
    knowledge_type: Optional[str] = None,
    dual_coding: Optional[Dict[str, Any]] = None,
    composed: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Complete current step: Wiki + ledger anchors, then advance (or mark completed).

    `composed` is the grounded content for the current step from
    `grounded_steps.compose_course_step` [CARD-640, CARD-646] (`dual_coding` is the older name for
    the dual coding step). Without it, steps built from the learner's notes write nothing.
    """
    course = memory_repo.get_education_course(course_id)
    if not course:
        raise KeyError(f"education course not found: {course_id}")

    step = (course.get("current_step") or "").strip()
    topic = course.get("topic_id") or ""
    steps = list(course.get("steps") or DEFAULT_COURSE_STEPS)

    if step in RETIRED_COURSE_STEPS:
        # A stored course sitting on a removed step moves on and writes nothing [CARD-639].
        nxt = _next_step(steps, step)
        updated = memory_repo.update_education_course_step(
            course_id=course_id,
            current_step=nxt or step,
            status="active" if nxt else "completed",
            now=now,
        )
        return {
            "success": True,
            "passed": True,
            "skipped": True,
            "skip_reason": "retired_step",
            "completed_step": step,
            "knowledge_type": None,
            "course": updated,
            "wiki_path": None,
            "artifact": {},
            "ledger": {},
            "item_ids": [],
            "tools_used": [],
            "grade_result": {},
        }

    artifact = _write_step_artifact(
        step=step,
        topic=topic,
        wiki_tools_or_store=wiki_tools_or_store,
        memory_repo=memory_repo,
        teach_style=teach_style,
        learner_explanation=learner_explanation,
        lab_submission=lab_submission,
        course_id=course_id,
        knowledge_type=knowledge_type,
        dual_coding=dual_coding,
        composed=composed,
        now=now,
    )

    if step in ("construction", "application") and not artifact.get("passed", True):
        # Honesty gate: failed lab halts course step advancement
        return {
            "success": False,
            "passed": False,
            "completed_step": step,
            "knowledge_type": artifact.get("knowledge_type"),
            "course": course,
            "wiki_path": artifact.get("wiki_path"),
            "artifact": artifact.get("artifact") or {},
            "ledger": artifact.get("ledger") or {},
            "item_ids": artifact.get("item_ids") or [],
            "tools_used": artifact.get("tools_used") or [],
            "grade_result": artifact.get("grade_result") or {},
            "graded": artifact.get("graded"),
            "grounding_skip_reason": artifact.get("grounding_skip_reason"),
            "quiz_skip_reason": artifact.get("quiz_skip_reason"),
            "quiz_duplicate": artifact.get("quiz_duplicate"),
            "quiz_retry": artifact.get("quiz_retry"),
        }

    nxt = _next_step(steps, step)
    if nxt is None:
        updated = memory_repo.update_education_course_step(
            course_id=course_id,
            current_step=step,
            status="completed",
            now=now,
        )
    else:
        updated = memory_repo.update_education_course_step(
            course_id=course_id,
            current_step=nxt,
            status="active",
            now=now,
        )

    return {
        "success": bool(artifact.get("success")),
        "passed": artifact.get("passed", True),
        "skipped": False,
        "skip_reason": artifact.get("skip_reason"),
        "skip_detail": artifact.get("skip_detail") or "",
        "completed_step": step,
        "knowledge_type": artifact.get("knowledge_type"),
        "course": updated,
        "wiki_path": artifact.get("wiki_path"),
        "artifact": artifact.get("artifact") or {},
        "ledger": artifact.get("ledger") or {},
        "item_ids": artifact.get("item_ids") or [],
        "tools_used": artifact.get("tools_used") or [],
        "grade_result": artifact.get("grade_result") or {},
        "graded": artifact.get("graded"),
        "grounding_skip_reason": artifact.get("grounding_skip_reason"),
        "quiz_skip_reason": artifact.get("quiz_skip_reason"),
        "quiz_duplicate": artifact.get("quiz_duplicate"),
        "quiz_retry": artifact.get("quiz_retry"),
    }


def grade_course_mastery(
    memory_repo: Any,
    *,
    item_id: str,
    answer: str,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Binary external mastery gate only -- miss uses existing Retention next_due."""
    existing = memory_repo.get_education_mastery(item_id)
    if not existing:
        raise KeyError(f"education mastery item not found: {item_id}")
    expected = (existing.get("expected_answer") or "").strip()
    if not expected:
        raise ValueError(
            "empty expected_answer -- re-seed via Priming/course step before grading"
        )
    correct = grade_answer_binary(expected, answer)
    row = memory_repo.record_education_grade(
        item_id=item_id, correct=correct, now=now
    )
    return {
        "grader": "binary_external",
        "correct": bool(correct),
        "item_id": item_id,
        "item": row,
    }


def course_chrome_snapshot(
    memory_repo: Any,
    *,
    topic_id: str = "",
    course_id: str = "",
    mastery_limit: int = 20,
) -> Dict[str, Any]:
    """UI chrome: topic -> ordered steps -> current step -> mastery from ledger."""
    course: Optional[Dict[str, Any]] = None
    if course_id:
        course = memory_repo.get_education_course(course_id)
    elif topic_id:
        course = memory_repo.get_education_course_by_topic(topic_id, prefer_active=True)
        if not course:
            course = memory_repo.get_education_course_by_topic(
                topic_id, prefer_active=False
            )

    mastery: List[Dict[str, Any]] = []
    if hasattr(memory_repo, "list_education_mastery"):
        rows = memory_repo.list_education_mastery(limit=mastery_limit)
        if course:
            topic = course.get("topic_id") or ""
            mastery = [r for r in rows if (r.get("topic") or "") == topic][:mastery_limit]
        else:
            mastery = list(rows)[:mastery_limit]

    resolved_topic = (course or {}).get("topic_id") or topic_id or ""
    depth_data: Optional[Dict[str, Any]] = None
    if resolved_topic and memory_repo is not None:
        from src.application.education.depth import calculate_topic_depth

        depth_data = calculate_topic_depth(memory_repo, topic=resolved_topic)

    delivery_profile_data: Optional[Dict[str, Any]] = None
    if memory_repo is not None:
        from src.application.education.environment import get_active_delivery_profile

        delivery_profile_data = get_active_delivery_profile(memory_repo)

    cur_step = (course or {}).get("current_step") or DEFAULT_COURSE_STEPS[0]
    from src.application.education.knowledge_types import (
        VALID_KNOWLEDGE_TYPES,
        resolve_step_knowledge_type,
    )

    ktype = resolve_step_knowledge_type(cur_step)

    return {
        "kind": COURSE_KIND,
        "pipeline_default": is_course_pipeline_default(),
        "default_steps": list(DEFAULT_COURSE_STEPS),
        "course": course,
        "topic": resolved_topic,
        "steps": _live_steps((course or {}).get("steps") or DEFAULT_COURSE_STEPS),
        "current_step": cur_step,
        "knowledge_type": ktype,
        "available_knowledge_types": list(VALID_KNOWLEDGE_TYPES),
        "status": (course or {}).get("status") or "none",
        "mastery": mastery,
        "depth": depth_data,
        "delivery_profile": delivery_profile_data,
    }

