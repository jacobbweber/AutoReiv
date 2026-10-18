"""Education Retrieval + Retention + Learner Model + Course API [CARD-242..327, CARD-715]."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.web.routers.education_courses import router as education_courses_router
from src.web.routers.education_deps import (
    _compose_current_step as _compose_current_step,
)
from src.web.routers.education_deps import (
    _course_wiki_tools as _course_wiki_tools,
)
from src.web.routers.education_deps import (
    _memory_repo as _memory_repo,
)
from src.web.routers.education_deps import (
    _repeat_of as _repeat_of,
)
from src.web.routers.education_deps import (
    _wiki_store as _wiki_store,
)
from src.web.routers.education_practice import router as education_practice_router

router = APIRouter(tags=["Education"])
router.include_router(education_practice_router)
router.include_router(education_courses_router)


class GradePayload(BaseModel):
    agent_id: str = "autoreiv"
    item_id: str
    answer: str = ""
    topic: Optional[str] = None
    wiki_path: Optional[str] = None
    prompt: Optional[str] = None
    expected_answer: Optional[str] = None


class UpsertItemPayload(BaseModel):
    agent_id: str = "autoreiv"
    item_id: Optional[str] = None
    topic: str
    wiki_path: str
    prompt: str
    expected_answer: str


class ExtractPayload(BaseModel):
    agent_id: str = "autoreiv"
    wiki_path: str
    topic: Optional[str] = None
    persist: bool = True


class RetentionRunPayload(BaseModel):
    agent_id: str = "autoreiv"
    force_due_item_id: Optional[str] = None


class QuizNextPayload(BaseModel):
    agent_id: str = "autoreiv"
    limit: int = Field(default=5, ge=1, le=50)
    topic: Optional[str] = None


class AskPressurePayload(BaseModel):
    agent_id: str = "autoreiv"
    topic: str = ""
    teach_style: Optional[str] = None
    wiki_path: Optional[str] = None
    wiki_title: Optional[str] = None
    mode: Optional[str] = None
    limit: int = Field(default=3, ge=1, le=10)


class SelectedEducationContextPayload(BaseModel):
    topic: Optional[str] = None
    course_id: Optional[str] = None
    agent_id: str = "tutor"
    clear: bool = False


class TutorContextPayload(BaseModel):
    agent_id: str = "autoreiv"
    topic: str = ""
    limit: int = Field(default=5, ge=1, le=20)


@router.get("/api/education/mastery")
async def list_mastery(request: Request, agent_id: str = "autoreiv", due_only: bool = False):
    repo = _memory_repo(request, agent_id)
    if due_only:
        rows = repo.list_due_education_mastery()
    else:
        rows = repo.list_education_mastery()
    return {"agent_id": agent_id, "items": rows, "count": len(rows)}


@router.get("/api/education/mastery/due")
async def list_due(request: Request, agent_id: str = "autoreiv"):
    repo = _memory_repo(request, agent_id)
    rows = repo.list_due_education_mastery()
    return {"agent_id": agent_id, "items": rows, "count": len(rows)}


@router.get("/api/education/progress")
async def progress_summary(
    request: Request,
    agent_id: str = "tutor",
    topic_id: Optional[str] = None,
    course_id: Optional[str] = None,
):
    """Non-Studio trustable progress: course + mastery + due from Learning OS [CARD-441]."""
    from src.application.education.progress_summary import build_progress_summary

    repo = _memory_repo(request, agent_id)
    return build_progress_summary(
        repo,
        agent_id=agent_id,
        topic_id=(topic_id or "").strip(),
        course_id=(course_id or "").strip(),
    )


@router.post("/api/education/mastery/upsert")
async def upsert_item(request: Request, payload: UpsertItemPayload):
    from src.application.education.quiz_engine import extract_quiz_items_from_note

    repo = _memory_repo(request, payload.agent_id)
    item_id = payload.item_id
    if not item_id:
        fake = extract_quiz_items_from_note(
            f"## Quiz\n- Q: {payload.prompt}\n  A: {payload.expected_answer}\n",
            wiki_path=payload.wiki_path,
            topic=payload.topic,
        )
        item_id = fake[0]["item_id"] if fake else None
    mid = repo.upsert_education_mastery(
        item_id=item_id or "",
        topic=payload.topic,
        wiki_path=payload.wiki_path,
        prompt=payload.prompt,
        expected_answer=payload.expected_answer,
        grade="unseen",
    )
    return {"item_id": mid, "item": repo.get_education_mastery(mid)}


@router.post("/api/education/quiz/extract")
async def extract_quiz(request: Request, payload: ExtractPayload):
    from src.application.education.quiz_engine import extract_quiz_items_from_note

    store = _wiki_store(request)
    try:
        note = store.read_note(payload.wiki_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=f"Wiki note not found: {payload.wiki_path}") from exc
    if not isinstance(note, dict) or note.get("success") is False:
        err = (note or {}).get("error") if isinstance(note, dict) else "not found"
        raise HTTPException(status_code=404, detail=f"Wiki note not found: {payload.wiki_path} ({err})")
    content = note.get("content") or note.get("body") or ""
    title = payload.topic or note.get("title") or payload.wiki_path

    items = extract_quiz_items_from_note(
        content,
        wiki_path=payload.wiki_path,
        topic=title,
    )
    persisted: List[Dict[str, Any]] = []
    if payload.persist and items:
        repo = _memory_repo(request, payload.agent_id)
        for it in items:
            mid = repo.upsert_education_mastery(
                item_id=it["item_id"],
                topic=it["topic"],
                wiki_path=it["wiki_path"],
                prompt=it["prompt"],
                expected_answer=it["expected_answer"],
                grade="unseen",
            )
            row = repo.get_education_mastery(mid)
            if row:
                persisted.append(row)
    return {
        "wiki_path": payload.wiki_path,
        "items": items,
        "persisted": persisted,
        "count": len(items),
    }


@router.post("/api/education/quiz/grade")
async def grade_quiz(request: Request, payload: GradePayload):
    from src.application.education.analysis import (
        record_error_and_metacog,
        write_analysis_wiki_outcome,
    )
    from src.application.education.quiz_engine import grade_answer_binary

    repo = _memory_repo(request, payload.agent_id)
    existing = repo.get_education_mastery(payload.item_id)
    if existing is None:
        if not (payload.prompt and payload.expected_answer and payload.wiki_path):
            raise HTTPException(status_code=404, detail=f"Unknown mastery item: {payload.item_id}")
        repo.upsert_education_mastery(
            item_id=payload.item_id,
            topic=payload.topic or payload.wiki_path,
            wiki_path=payload.wiki_path,
            prompt=payload.prompt,
            expected_answer=payload.expected_answer,
            grade="unseen",
        )
        existing = repo.get_education_mastery(payload.item_id)
    assert existing is not None
    expected = existing.get("expected_answer") or payload.expected_answer or ""
    if not str(expected).strip():
        raise HTTPException(
            status_code=422,
            detail=(
                f"Mastery item {payload.item_id} has empty expected_answer; "
                "re-seed via Priming writeback or mastery/upsert before grading"
            ),
        )
    correct = grade_answer_binary(expected, payload.answer)
    row = repo.record_education_grade(item_id=payload.item_id, correct=correct)
    analysis = record_error_and_metacog(
        repo,
        item=row,
        given=payload.answer,
        correct=correct,
        source="quiz",
    )
    wiki_writeback: Dict[str, Any] = {"success": False, "skipped": True}
    if not correct:
        try:
            wiki_store = _wiki_store(request)
            wiki_writeback = write_analysis_wiki_outcome(
                wiki_store,
                wiki_path=str(row.get("wiki_path") or existing.get("wiki_path") or ""),
                item=row,
                miss_reason=str(analysis.get("miss_reason") or ""),
                given=payload.answer,
            )
        except Exception as exc:  # noqa: BLE001
            wiki_writeback = {"success": False, "error": str(exc)}
    return {
        "correct": correct,
        "grade": row.get("grade"),
        "next_due": row.get("next_due"),
        "interval_stage": row.get("interval_stage"),
        "item": row,
        "grader": "binary_external",
        "analysis": analysis,
        "wiki_writeback": wiki_writeback,
    }


@router.post("/api/education/retention/run")
async def run_retention(request: Request, payload: RetentionRunPayload):
    """Force Education retention Routine path: due ledger -> standing Job mint."""
    from src.application.education.retention_routine import (
        EDUCATION_RETENTION_ROUTINE_ID,
        run_education_retention,
    )
    from src.domain.routines.models import Routine, ScheduleType

    repo = _memory_repo(request, payload.agent_id)
    if payload.force_due_item_id:
        row = repo.get_education_mastery(payload.force_due_item_id)
        if not row:
            raise HTTPException(status_code=404, detail="item not found")
        repo.force_education_mastery_due(payload.force_due_item_id, now=datetime.now(timezone.utc))

    store = request.app.state.store
    orch = getattr(request.app.state, "job_orchestrator", None) or getattr(
        request.app.state, "orchestrator", None
    )
    routine = store.get_routine(EDUCATION_RETENTION_ROUTINE_ID) if hasattr(store, "get_routine") else None
    if routine is None:
        routine = Routine(
            id=EDUCATION_RETENTION_ROUTINE_ID,
            name="Education Retrieval + Retention",
            description="Resurface due Education quiz reviews as standing Jobs",
            agent_id=payload.agent_id,
            prompt="Resurface due Education quiz reviews as standing Jobs.",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=3600,
            enabled=True,
        )

    if not bool(getattr(routine, "enabled", True)):
        return {
            "routine_id": EDUCATION_RETENTION_ROUTINE_ID,
            "result": {
                "status": "ok",
                "due_count": 0,
                "minted_job_ids": [],
                "reason": "routine_disabled",
            },
            "session_id": None,
            "enabled": False,
        }

    session_id = f"edu-retention-api-{datetime.now(timezone.utc).strftime('%H%M%S')}"
    try:
        if hasattr(store, "create_session"):
            sess = store.create_session(agent_id=payload.agent_id, title="Education Retention")
            session_id = getattr(sess, "id", None) or sess.get("id") or session_id
    except Exception:  # noqa: BLE001
        pass

    result = run_education_retention(
        memory_repo=repo,
        orch=orch,
        routine=routine,
        agent_id=payload.agent_id,
        session_id=session_id,
        respect_enabled=True,
    )
    return {
        "routine_id": EDUCATION_RETENTION_ROUTINE_ID,
        "result": result,
        "session_id": session_id,
        "enabled": bool(getattr(routine, "enabled", True)),
    }


@router.get("/api/education/quiz/next")
async def quiz_next(
    request: Request,
    agent_id: str = "autoreiv",
    limit: int = 5,
    topic: Optional[str] = None,
    profile_id: Optional[str] = None,
):
    """Prefer miss-reason pressure then due/weak/missed; delivery + visual amplifiers on Retrieval [CARD-243..249]."""
    from src.application.education.analysis import (
        active_miss_reasons,
        build_analysis_ask_clause,
        select_quiz_with_miss_reason_pressure,
        summarize_analysis,
    )
    from src.application.education.environment import (
        build_environment_ask_clause,
        get_active_delivery_profile,
        get_delivery_profile,
        shape_quiz_presentation,
    )
    from src.application.education.learner_model import build_ask_pressure_clause
    from src.application.education.visual_amplifiers import (
        amplify_quiz_items,
        build_amplifier_ask_clause,
    )

    repo = _memory_repo(request, agent_id)
    items = select_quiz_with_miss_reason_pressure(repo, limit=limit, topic=topic)
    analysis_summary = summarize_analysis(repo, limit=20)
    if profile_id:
        profile = get_delivery_profile(profile_id)
    else:
        profile = get_active_delivery_profile(repo)
    delivery = shape_quiz_presentation(items, profile=profile)
    amplified = amplify_quiz_items(delivery["items"], repo)
    amp_clause = ""
    for it in amplified["items"]:
        if it.get("has_visual_amplifier") and it.get("amplifier"):
            amp_clause += build_amplifier_ask_clause(it["amplifier"])
            break
    if not amp_clause:
        amp_clause = build_amplifier_ask_clause(None)
    return {
        "agent_id": agent_id,
        "items": amplified["items"],
        "all_items": delivery["all_items"],
        "count": delivery["presented_count"],
        "ledger_count": delivery["ledger_count"],
        "amplified_count": amplified["amplified_count"],
        "selection": "miss_reason_then_due_weak_miss_priming_unseen",
        "pressure_clause": (
            build_ask_pressure_clause(items)
            + build_analysis_ask_clause(analysis_summary)
            + build_environment_ask_clause(profile)
            + amp_clause
        ),
        "active_miss_reasons": active_miss_reasons(repo),
        "analysis_pressure": bool(analysis_summary.get("pressured_item_ids")),
        "delivery": {
            "profile": profile,
            "timer_seconds": delivery.get("timer_seconds"),
            "tone": delivery.get("tone"),
            "bite_size": delivery.get("bite_size"),
            "replaces_srs": False,
            "replaces_ledger": False,
            "due_source": "mastery_ledger_srs",
        },
        "amplifiers": {
            "amplified_count": amplified["amplified_count"],
            "retrieval_required": True,
        },
    }


@router.get("/api/education/learner")
async def learner_summary(request: Request, agent_id: str = "autoreiv"):
    """Durable second-mind learner summary from memory.db [CARD-243]."""
    from src.application.education.learner_model import summarize_learner_model

    repo = _memory_repo(request, agent_id)
    summary = summarize_learner_model(repo)
    summary["agent_id"] = agent_id
    return summary


@router.post("/api/education/ask/pressure")
async def ask_with_pressure(request: Request, payload: AskPressurePayload):
    """Build an Education Ask that pressures known misses from the learner model."""
    from src.application.education.environment import (
        build_environment_ask_clause,
        get_active_delivery_profile,
    )
    from src.application.education.learner_model import (
        build_ask_pressure_clause,
        select_quiz_items,
    )

    repo = _memory_repo(request, payload.agent_id)
    ranked = select_quiz_items(repo, limit=max(payload.limit * 5, 10), topic=payload.topic or None)
    weak = [
        r
        for r in ranked
        if (str(r.get("grade") or "").lower() == "miss") or int(r.get("miss_count") or 0) > 0
    ][: payload.limit]
    if not weak:
        ranked = select_quiz_items(repo, limit=max(payload.limit * 5, 10), topic=None)
        weak = [
            r
            for r in ranked
            if (str(r.get("grade") or "").lower() == "miss") or int(r.get("miss_count") or 0) > 0
        ][: payload.limit]
    clause = build_ask_pressure_clause(weak)
    env_profile = get_active_delivery_profile(repo)
    clause = clause + build_environment_ask_clause(env_profile)

    topic = (payload.topic or "").strip() or (
        (weak[0].get("topic") if weak else "") or "Education review"
    )
    mode = (payload.mode or "custom").strip().lower()
    teach = (payload.teach_style or "").strip() or "pressure known misses from learner model"
    wiki_path = (payload.wiki_path or "").strip()
    wiki_title = (payload.wiki_title or "").strip()
    wiki_bit = (
        f' Ground the teaching in my Wiki note "{wiki_title or wiki_path}" ({wiki_path}).'
        if wiki_path
        else " Ground the teaching in my existing Wiki notes when relevant."
    )
    marker = "[Education Studio]"
    if mode == "priming":
        ask = (
            f'{marker} [Mode: Priming] Teach me about "{topic}" using the education-priming skill.'
            + wiki_bit
            + f" How to teach me: {teach}."
            + " Use only wiki_note_search/wiki_note_list/wiki_note_read/wiki_note_create (never wiki_overview)."
            + f' Done-when: a Priming schema note exists in Wiki for "{topic}".'
        )
    elif mode == "dual_coding":
        ask = (
            f'{marker} [Mode: Dual Coding] Teach me about "{topic}" using the education-dual-coding skill.'
            + wiki_bit
            + f" How to teach me: {teach}."
            + " Use only wiki_note_search/wiki_note_read/wiki_note_create (never wiki_overview)."
            + f' Done-when: a Dual Coding study note exists in Wiki for "{topic}".'
        )
    elif mode in ("construction", "construct", "study_artifact"):
        ask = (
            f'{marker} [Mode: Construction] Construct a generative study artifact for "{topic}" '
            "using the education-construction skill."
            + wiki_bit
            + f" How to teach me: {teach}."
            + " Use only wiki_note_search/wiki_note_list/wiki_note_read/wiki_note_create (never wiki_overview)."
            + f' Done-when: a Construction study artifact note exists in Wiki 00_Inbox/ for "{topic}".'
        )
    elif mode in ("amplifiers", "visual_amplifiers", "visual-amplifiers"):
        ask = (
            f'{marker} [Mode: Visual Amplifiers] Teach me about "{topic}" with Dual Coding Mermaid/step-through on Retrieval.'
            + wiki_bit
            + f" How to teach me: {teach}."
            + " Attach amplifiers only to quiz/mastery items; never visuals-only (edutainment guard)."
            + " Video/film player is OUT of P0."
            + " Use only wiki_note_search/wiki_note_read when grounding (never wiki_overview)."
            + f' Done-when: a visual amplifier is attached to a Retrieval-backed quiz item for "{topic}".'
        )
    else:
        ask = (
            f'{marker} [Mode: Learner Pressure] Teach/reteach me about "{topic}".'
            + wiki_bit
            + f" How to teach me: {teach}."
            + " Write a short study note back to Wiki summarizing what I should retain."
            + f' Done-when: I have attempted recall on the known weak item(s) for "{topic}".'
        )
    ask = ask + clause
    return {
        "agent_id": payload.agent_id,
        "ask": ask,
        "weak_items": weak,
        "pressure_clause": clause,
        "selection": "due_weak_miss_over_random",
    }


@router.get("/api/education/selected")
async def get_selected_education_context_api(request: Request):
    """Studio-active topic/course (Projects selected parallel) [CARD-447]."""
    from src.application.education.selected_context import get_selected_education_context

    store = getattr(request.app.state, "store", None)
    return {
        "selected": get_selected_education_context(store),
        "http_contract": "GET /api/education/selected",
        "projects_parallel": "GET /api/projects/selected",
    }


@router.put("/api/education/selected")
async def put_selected_education_context_api(request: Request, payload: SelectedEducationContextPayload):
    """Persist Studio-active topic/course for Tutor injection [CARD-447]."""
    from src.application.education.selected_context import set_selected_education_context

    store = getattr(request.app.state, "store", None)
    res = set_selected_education_context(
        store,
        topic=payload.topic,
        course_id=payload.course_id,
        agent_id=payload.agent_id,
        clear=bool(payload.clear),
        source="education_studio",
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "selected education context failed"))
    return {
        **res,
        "http_contract": "PUT /api/education/selected",
        "projects_parallel": "PUT /api/projects/selected",
    }


@router.post("/api/education/tutor/context")
async def tutor_topic_context(request: Request, payload: TutorContextPayload):
    """Assemble Socratic tutor context for active topic from existing memory.db and Wiki [CARD-326]."""
    from src.application.education.tutor import assemble_tutor_topic_context
    from src.application.skills.wiki_tools import WikiTools

    repo = _memory_repo(request, payload.agent_id)
    wiki_store = _wiki_store(request)
    wiki_tools = WikiTools(wiki_root=wiki_store.root_dir)

    return assemble_tutor_topic_context(
        topic=payload.topic,
        memory_repo=repo,
        wiki_tools=wiki_tools,
        limit=payload.limit,
    )


# --- CARD-320 Course + Mastery -------------------------------------------------


class CourseStartPayload(BaseModel):
    agent_id: str = "autoreiv"
    topic_id: str
    steps: Optional[List[str]] = None


class CourseIdPayload(BaseModel):
    agent_id: str = "autoreiv"
    course_id: str


class CourseJumpPayload(BaseModel):
    agent_id: str = "autoreiv"
    course_id: str
    step: str


class CourseCompletePayload(BaseModel):
    agent_id: str = "autoreiv"
    course_id: str
    teach_style: Optional[str] = None
    learner_explanation: Optional[str] = None
    lab_submission: Optional[str] = None
    knowledge_type: Optional[str] = None


class CourseMasteryGradePayload(BaseModel):
    agent_id: str = "autoreiv"
    item_id: str
    answer: str = ""


@router.post("/api/education/course/start")
async def course_start(request: Request, payload: CourseStartPayload):
    """Start or resume durable course pipeline (DEFAULT Ask path) [CARD-320]."""
    from src.application.education.course import course_chrome_snapshot, start_or_resume_course

    topic = (payload.topic_id or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic_id is required")
    repo = _memory_repo(request, payload.agent_id)
    course = start_or_resume_course(repo, topic_id=topic, steps=payload.steps)
    chrome = course_chrome_snapshot(repo, topic_id=topic, course_id=course.get("course_id") or "")
    return {"agent_id": payload.agent_id, "course": course, "chrome": chrome, "pipeline_default": True}


@router.get("/api/education/course")
async def course_get(
    request: Request,
    topic_id: Optional[str] = None,
    course_id: Optional[str] = None,
    agent_id: str = "autoreiv",
):
    """Retrieve active course row + chrome snapshot [CARD-320]."""
    from src.application.education.course import (
        course_chrome_snapshot,
        get_course,
        start_or_resume_course,
    )

    repo = _memory_repo(request, agent_id)
    course = None
    if course_id:
        course = get_course(repo, course_id=course_id)
    elif topic_id:
        course = start_or_resume_course(repo, topic_id=topic_id)
    chrome = course_chrome_snapshot(
        repo,
        topic_id=(topic_id or (course or {}).get("topic_id") or ""),
        course_id=(course or {}).get("course_id") or course_id or "",
    )
    return {"agent_id": agent_id, "course": course, "chrome": chrome, "pipeline_default": True}


@router.post("/api/education/course/complete-step")
async def course_complete_step(request: Request, payload: CourseCompletePayload):
    """Complete current course step: Wiki + ledger anchors, advance [CARD-320, CARD-334]."""
    from src.application.education.course import complete_course_step, course_chrome_snapshot

    if not (payload.course_id or "").strip():
        raise HTTPException(status_code=400, detail="course_id is required")
    repo = _memory_repo(request, payload.agent_id)
    tools = _course_wiki_tools(request)
    composed = await _compose_current_step(
        request, repo, payload.course_id, tools, payload.learner_explanation, payload.lab_submission
    )
    try:
        result = complete_course_step(
            repo,
            course_id=payload.course_id,
            wiki_tools_or_store=tools,
            teach_style=payload.teach_style or "",
            learner_explanation=payload.learner_explanation,
            lab_submission=payload.lab_submission,
            knowledge_type=payload.knowledge_type,
            composed=composed,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    course = result.get("course") or {}
    chrome = course_chrome_snapshot(
        repo,
        topic_id=course.get("topic_id") or "",
        course_id=course.get("course_id") or payload.course_id,
    )
    return {"agent_id": payload.agent_id, **result, "chrome": chrome}


@router.post("/api/education/course/jump")
async def course_jump(request: Request, payload: CourseJumpPayload):
    """Secondary mode-picker jump-to-step [CARD-320]."""
    from src.application.education.course import course_chrome_snapshot, jump_to_course_step

    if not (payload.course_id or "").strip() or not (payload.step or "").strip():
        raise HTTPException(status_code=400, detail="course_id and step are required")
    repo = _memory_repo(request, payload.agent_id)
    try:
        course = jump_to_course_step(repo, course_id=payload.course_id, step=payload.step)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    chrome = course_chrome_snapshot(
        repo, topic_id=course.get("topic_id") or "", course_id=course.get("course_id") or ""
    )
    return {"agent_id": payload.agent_id, "course": course, "chrome": chrome}


@router.post("/api/education/course/mastery/grade")
async def course_mastery_grade(request: Request, payload: CourseMasteryGradePayload):
    """Binary external mastery gate for course practice [CARD-320]."""
    from src.application.education.course import grade_course_mastery
    from src.application.education.quiz_engine import grade_answer_binary

    if not (payload.item_id or "").strip():
        raise HTTPException(status_code=400, detail="item_id is required")
    repo = _memory_repo(request, payload.agent_id)
    _ = grade_answer_binary
    try:
        result = grade_course_mastery(repo, item_id=payload.item_id, answer=payload.answer or "")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"agent_id": payload.agent_id, **result}
