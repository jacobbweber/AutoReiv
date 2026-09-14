"""Education Learning OS Course + Mastery pipeline [CARD-320].

Durable course in agent *_memory.db (education_course). Course pipeline is the
DEFAULT Ask path; mode-picker is secondary jump-to-step only. Mastery gate is
binary external only (grade_answer_binary). No Dual Coding chrome on this card.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.application.education.quiz_engine import grade_answer_binary

COURSE_KIND = "education_course"

# Ordered Learning OS default pipeline (Architect lock). Dual Coding is a
# secondary jump target only -- not a default step / decorative player.
DEFAULT_COURSE_STEPS: tuple[str, ...] = (
    "priming",
    "retrieval",
    "elaboration",
    "construction",
    "application",
    "analysis",
    "environment",
    "amplifiers",
    "retention",
)

# Steps allowed via mode-picker jump (includes dual_coding as secondary).
JUMPABLE_STEPS: frozenset[str] = frozenset(
    list(DEFAULT_COURSE_STEPS) + ["dual_coding", "custom"]
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
    step_list = [str(s).strip() for s in (steps or DEFAULT_COURSE_STEPS) if str(s).strip()]
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
    cur = (current or "").strip()
    ordered = [str(s).strip() for s in steps if str(s).strip()]
    if cur not in ordered:
        return ordered[0] if ordered else None
    idx = ordered.index(cur)
    if idx + 1 >= len(ordered):
        return None
    return ordered[idx + 1]


def _write_step_artifact(
    *,
    step: str,
    topic: str,
    wiki_tools_or_store: Any,
    memory_repo: Any,
    teach_style: str = "",
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Write Wiki artifact + ledger anchors for a completed step.

    Reuses Priming writeback for priming; other steps get a lightweight Inbox
    note + mastery/learner anchors (same memory.db brain).
    """
    step_name = (step or "").strip().lower()
    topic_clean = _normalize_topic(topic)

    if step_name == "priming":
        from src.application.education.priming import priming_writeback

        result = priming_writeback(
            topic=topic_clean,
            wiki_tools_or_store=wiki_tools_or_store,
            memory_repo=memory_repo,
            teach_style=teach_style or "schema first",
            search_first=True,
            now=now,
        )
        return {
            "success": bool(result.get("success")),
            "step": step_name,
            "wiki_path": result.get("path"),
            "artifact": {
                "path": result.get("path"),
                "kind": result.get("kind") or "priming",
                "title": result.get("title"),
            },
            "ledger": result.get("ledger") or {},
            "item_ids": list((result.get("ledger") or {}).get("item_ids") or []),
            "tools_used": result.get("tools_used") or [],
        }

    from src.application.education.priming_schema import slug_topic
    from src.application.education.priming_wiki_io import create_priming_note

    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    stamp = base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = f"Course {step_name.title()}: {topic_clean}"
    content = (
        f"# {title}\n\n"
        f"tags: [education, course, {step_name}]\n"
        f"kind: education_course_step\n"
        f"step: {step_name}\n"
        f"topic: {topic_clean}\n"
        f"created: {stamp}\n\n"
        f"## Outline\n"
        f"- Learning OS step `{step_name}` completed for **{topic_clean}**\n"
        f"- Durable course row lives in agent memory.db (`education_course`)\n"
        f"- Mastery gate remains binary external (quiz/flashcards)\n\n"
        f"## Quiz\n"
        f"Q: What Learning OS step did you just complete for {topic_clean}?\n"
        f"A: {step_name}\n"
    )
    create_res = create_priming_note(
        wiki_tools_or_store,
        title=title,
        content=content,
        topic=topic_clean,
        tags=["education", "course", step_name],
        summary=f"Course step {step_name} for {topic_clean}",
    )
    path = str(create_res.get("path") or "")
    note_ok = bool(create_res.get("success")) and (
        bool(create_res.get("inbox")) or path.replace("\\", "/").startswith("00_Inbox/")
    )

    ledger: Dict[str, Any] = {"success": False, "count": 0, "item_ids": []}
    if note_ok and memory_repo is not None:
        item_id = f"course_{slug_topic(topic_clean)}_{step_name}"[:48]
        prompt = f"What Learning OS step did you just complete for {topic_clean}?"
        expected = step_name
        mid = memory_repo.upsert_education_mastery(
            item_id=item_id,
            topic=topic_clean,
            wiki_path=path,
            prompt=prompt,
            expected_answer=expected,
            grade="unseen",
        )
        try:
            from src.application.education.learner_model import LEARNER_ENTITY

            memory_repo.add_semantic_fact(
                entity=LEARNER_ENTITY,
                attribute=f"course_step_{step_name}",
                value=f"{topic_clean}|{path}|{stamp}",
                category="education_learner",
                confidence=1.0,
                decay_half_life_days=90.0,
                fact_id=f"edu_course_{slug_topic(topic_clean)}_{step_name}"[:64],
            )
        except Exception:
            pass
        ledger = {"success": True, "count": 1, "item_ids": [mid]}

    return {
        "success": note_ok,
        "step": step_name,
        "wiki_path": path,
        "artifact": {
            "path": path,
            "kind": f"course_{step_name}",
            "title": title,
        },
        "ledger": ledger,
        "item_ids": list(ledger.get("item_ids") or []),
        "tools_used": ["wiki_note_create"] if note_ok else [],
    }


def complete_course_step(
    memory_repo: Any,
    *,
    course_id: str,
    wiki_tools_or_store: Any = None,
    teach_style: str = "",
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Complete current step: Wiki + ledger anchors, then advance (or mark completed)."""
    course = memory_repo.get_education_course(course_id)
    if not course:
        raise KeyError(f"education course not found: {course_id}")

    step = (course.get("current_step") or "").strip()
    topic = course.get("topic_id") or ""
    steps = list(course.get("steps") or DEFAULT_COURSE_STEPS)

    artifact = _write_step_artifact(
        step=step,
        topic=topic,
        wiki_tools_or_store=wiki_tools_or_store,
        memory_repo=memory_repo,
        teach_style=teach_style,
        now=now,
    )

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
        "completed_step": step,
        "course": updated,
        "wiki_path": artifact.get("wiki_path"),
        "artifact": artifact.get("artifact") or {},
        "ledger": artifact.get("ledger") or {},
        "item_ids": artifact.get("item_ids") or [],
        "tools_used": artifact.get("tools_used") or [],
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

    return {
        "kind": COURSE_KIND,
        "pipeline_default": is_course_pipeline_default(),
        "default_steps": list(DEFAULT_COURSE_STEPS),
        "course": course,
        "topic": (course or {}).get("topic_id") or topic_id or "",
        "steps": list((course or {}).get("steps") or DEFAULT_COURSE_STEPS),
        "current_step": (course or {}).get("current_step") or DEFAULT_COURSE_STEPS[0],
        "status": (course or {}).get("status") or "none",
        "mastery": mastery,
    }
