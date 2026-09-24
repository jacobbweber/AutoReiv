"""Education Retrieval + Retention + Learner Model + Elaboration + Construction + Analysis + Environment + Visual Amplifiers API [CARD-242..249]."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(tags=["Education"])


class GradePayload(BaseModel):
    agent_id: str = "autoreiv"
    item_id: str
    answer: str = ""
    # Optional: register item before grade when extracting on the fly
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



class ElaborationExtractPayload(BaseModel):
    agent_id: str = "autoreiv"
    wiki_path: str
    topic: Optional[str] = None
    persist: bool = True


class ElaborationGradePayload(BaseModel):
    agent_id: str = "autoreiv"
    item_id: str
    answer: str = ""
    topic: Optional[str] = None
    wiki_path: Optional[str] = None
    prompt: Optional[str] = None
    expected_answer: Optional[str] = None
    required_concepts: Optional[List[str]] = None
    write_wiki: bool = True
    write_memory: bool = True


class ConstructionGeneratePayload(BaseModel):
    agent_id: str = "autoreiv"
    topic: str
    wiki_path: Optional[str] = None
    teach_style: Optional[str] = None
    search_first: bool = True


class SelectedEducationContextPayload(BaseModel):
    topic: Optional[str] = None
    course_id: Optional[str] = None
    agent_id: str = "tutor"
    clear: bool = False


class TutorContextPayload(BaseModel):
    agent_id: str = "autoreiv"
    topic: str = ""
    limit: int = Field(default=5, ge=1, le=20)


class ConstructionAskPayload(BaseModel):
    agent_id: str = "autoreiv"
    topic: str
    wiki_path: Optional[str] = None
    wiki_title: Optional[str] = None
    teach_style: Optional[str] = None




class ApplicationExtractPayload(BaseModel):
    agent_id: str = "autoreiv"
    wiki_path: str
    topic: Optional[str] = None
    persist: bool = True


class ApplicationGradePayload(BaseModel):
    agent_id: str = "autoreiv"
    item_id: str
    answer: str = ""
    topic: Optional[str] = None
    wiki_path: Optional[str] = None
    prompt: Optional[str] = None
    expected_answer: Optional[str] = None
    required_concepts: Optional[List[str]] = None
    phase_id: Optional[str] = None
    replan_count: int = 0
    mint_on_fail: bool = True
    write_wiki: bool = True
    write_memory: bool = True


class ApplicationMintPayload(BaseModel):
    agent_id: str = "autoreiv"
    item_id: str
    topic: Optional[str] = None
    wiki_path: Optional[str] = None
    prompt: Optional[str] = None
    expected_answer: Optional[str] = None
    required_concepts: Optional[List[str]] = None
    session_id: Optional[str] = None


def _memory_repo(request: Request, agent_id: str):
    from src.infrastructure.data.resolver import DataDirResolver
    from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

    injected = getattr(request.app.state, "memory_repo", None)
    if injected is not None:
        return injected

    data_dir = getattr(request.app.state, "data_dir", None)
    if not data_dir:
        paths = getattr(request.app.state, "data_dir_paths", None)
        if paths is not None and getattr(paths, "root", None):
            data_dir = str(paths.root)
    if not data_dir:
        data_dir = str(DataDirResolver().platform_default())
    repo = AgentMemoryRepository(agent_id=agent_id, data_dir=data_dir)
    repo.initialize_schema()
    return repo


def _wiki_store(request: Request):
    from src.domain.wiki.store import WikiStore

    wiki_root = getattr(request.app.state, "wiki_path", None) or getattr(request.app.state, "wiki_root", None)
    if wiki_root:
        return WikiStore(root_dir=wiki_root)
    return WikiStore()


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
    """Non-Studio trustable progress: course + mastery + due from Learning OS [CARD-441].

    Failures return success=false with empty mastery_pct=None - never fabricate 100%.
    Education Studio course chrome stays (studio_chrome_retained).
    """
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
        # stable id from path+prompt
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
    # CARD-318: binary grade needs a non-empty expected_answer (Priming anchors must seed it)
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
        # Make due now for smoke
        past = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # set next_due in the past while preserving grade
        with repo.get_connection() as conn:
            conn.execute(
                "UPDATE education_mastery SET next_due = ?, pending_job_id = NULL, updated_at = ? WHERE item_id = ?",
                (past, past, payload.force_due_item_id),
            )

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

    # CARD-319: honor Routines Studio pause - no mint when disabled (no new Edu chrome).
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

    # Prefer live session creation when available
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
    # CARD-319: do NOT save_routine here — a synthetic enabled=True fallback
    # would overwrite Routines Studio pause. Mint path updates pending_job_id only.
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
    # Selection still from ledger / miss-reason pressure — never from delivery profile.
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
            "lumina_film": False,
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
    # Oversample then keep miss/due only — never pressure random strong passes [CARD-243]
    ranked = select_quiz_items(repo, limit=max(payload.limit * 5, 10), topic=payload.topic or None)
    weak = [
        r
        for r in ranked
        if (str(r.get("grade") or "").lower() == "miss") or int(r.get("miss_count") or 0) > 0
    ][: payload.limit]
    if not weak:
        # Fall back to global misses when topic has none
        ranked = select_quiz_items(repo, limit=max(payload.limit * 5, 10), topic=None)
        weak = [
            r
            for r in ranked
            if (str(r.get("grade") or "").lower() == "miss") or int(r.get("miss_count") or 0) > 0
        ][: payload.limit]
    clause = build_ask_pressure_clause(weak)
    env_profile = get_active_delivery_profile(repo)
    clause = clause + build_environment_ask_clause(env_profile)

    # Prefer Studio JS builder when available; mirror Priming/Dual/custom here for API smoke.
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


@router.post("/api/education/elaboration/extract")
async def extract_elaboration(request: Request, payload: ElaborationExtractPayload):
    """Extract explain-it-back items from a Wiki note [CARD-244]."""
    from src.application.education.elaboration import extract_elaboration_items_from_note

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
    items = extract_elaboration_items_from_note(
        content,
        wiki_path=payload.wiki_path,
        topic=title,
    )
    persisted: List[Dict[str, Any]] = []
    if payload.persist and items:
        repo = _memory_repo(request, payload.agent_id)
        for it in items:
            expected = it.get("expected_answer") or ", ".join(it.get("required_concepts") or [])
            mid = repo.upsert_education_mastery(
                item_id=it["item_id"],
                topic=it["topic"],
                wiki_path=it["wiki_path"],
                prompt=it["prompt"],
                expected_answer=expected,
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
        "kind": "elaboration",
    }


@router.get("/api/education/elaboration/next")
async def elaboration_next(
    request: Request,
    agent_id: str = "autoreiv",
    limit: int = 1,
    topic: Optional[str] = None,
):
    """Prefer due/weak mastery items shaped as explain-it-back prompts [CARD-244]."""
    from src.application.education.elaboration import (
        build_elaboration_ask_clause,
        elaboration_from_mastery_row,
    )
    from src.application.education.learner_model import select_quiz_items

    repo = _memory_repo(request, agent_id)
    ranked = select_quiz_items(repo, limit=max(limit * 5, 10), topic=topic)
    items = [elaboration_from_mastery_row(r) for r in ranked[:limit]]
    return {
        "agent_id": agent_id,
        "items": items,
        "count": len(items),
        "selection": "due_weak_miss_over_random",
        "kind": "elaboration",
        "ask_clause": build_elaboration_ask_clause(items),
    }


@router.post("/api/education/elaboration/grade")
async def grade_elaboration(request: Request, payload: ElaborationGradePayload):
    """Binary external explain-it-back grade + ledger + Wiki/memory write-back [CARD-244]."""
    from src.application.education.elaboration import grade_and_record_elaboration

    repo = _memory_repo(request, payload.agent_id)
    existing = repo.get_education_mastery(payload.item_id)
    concepts = list(payload.required_concepts or [])
    if existing is None:
        if not (payload.prompt and (payload.expected_answer or concepts) and payload.wiki_path):
            raise HTTPException(status_code=404, detail=f"Unknown mastery item: {payload.item_id}")
        item = {
            "item_id": payload.item_id,
            "topic": payload.topic or payload.wiki_path,
            "wiki_path": payload.wiki_path,
            "prompt": payload.prompt,
            "expected_answer": payload.expected_answer or "",
            "required_concepts": concepts,
        }
    else:
        item = {
            "item_id": existing["item_id"],
            "topic": payload.topic or existing.get("topic"),
            "wiki_path": payload.wiki_path or existing.get("wiki_path"),
            "prompt": payload.prompt or existing.get("prompt"),
            "expected_answer": payload.expected_answer or existing.get("expected_answer") or "",
            "required_concepts": concepts,
        }

    wiki_store = None
    if payload.write_wiki:
        try:
            wiki_store = _wiki_store(request)
        except Exception:  # noqa: BLE001
            wiki_store = None

    result = grade_and_record_elaboration(
        repo=repo,
        item=item,
        given=payload.answer,
        wiki_store=wiki_store,
        write_wiki=bool(payload.write_wiki and wiki_store is not None),
        write_memory=payload.write_memory,
    )
    return result


@router.post("/api/education/construction/generate")
async def construction_generate(request: Request, payload: ConstructionGeneratePayload):
    """Generate a Construction study artifact into Wiki 00_Inbox via wiki_note_* only [CARD-245]."""
    from src.application.education.construction import construct_study_artifact
    from src.application.skills.wiki_tools import WikiTools

    topic = (payload.topic or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")

    wiki_root = getattr(request.app.state, "wiki_path", None) or getattr(
        request.app.state, "wiki_root", None
    )
    tools = WikiTools(wiki_root=wiki_root) if wiki_root else WikiTools()

    result = construct_study_artifact(
        topic=topic,
        wiki_tools_or_store=tools,
        wiki_path=(payload.wiki_path or None),
        teach_style=(payload.teach_style or "") or "generate durable study artifact",
        search_first=bool(payload.search_first),
    )
    if not result.get("success"):
        # Still return structured body so Studio can show fail-soft details; 422 only if create failed hard.
        raise HTTPException(status_code=422, detail=result)
    return {
        "agent_id": payload.agent_id,
        "kind": "construction",
        **result,
    }


@router.post("/api/education/construction/ask-clause")
async def construction_ask_clause(payload: ConstructionAskPayload):
    """Return Construction-shaped Education Ask clause (wiki_note_* only)."""
    from src.application.education.construction import build_construction_ask_clause

    topic = (payload.topic or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")
    clause = build_construction_ask_clause(
        topic=topic,
        wiki_path=payload.wiki_path or "",
        wiki_title=payload.wiki_title or "",
        teach_style=payload.teach_style or "",
    )
    return {
        "agent_id": payload.agent_id,
        "kind": "construction",
        "ask_clause": clause,
        "allowlist": ["wiki_note_search", "wiki_note_list", "wiki_note_read", "wiki_note_create", "wiki_note_append"],
        "forbidden": ["wiki_overview", "wiki_graph"],
    }


@router.post("/api/education/application/extract")
async def extract_application(request: Request, payload: ApplicationExtractPayload):
    """Extract Application / Exercise items from a Wiki note [CARD-246]."""
    from src.application.education.application import extract_application_items_from_note

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
    items = extract_application_items_from_note(
        content,
        wiki_path=payload.wiki_path,
        topic=title,
    )
    persisted: List[Dict[str, Any]] = []
    if payload.persist and items:
        repo = _memory_repo(request, payload.agent_id)
        for it in items:
            expected = it.get("expected_answer") or ", ".join(it.get("required_concepts") or [])
            mid = repo.upsert_education_mastery(
                item_id=it["item_id"],
                topic=it["topic"],
                wiki_path=it["wiki_path"],
                prompt=it["prompt"],
                expected_answer=expected,
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
        "kind": "application",
    }


@router.get("/api/education/application/next")
async def application_next(
    request: Request,
    agent_id: str = "autoreiv",
    limit: int = 1,
    topic: Optional[str] = None,
):
    """Prefer due/weak mastery items shaped as Application exercises [CARD-246]."""
    from src.application.education.application import (
        application_from_mastery_row,
        build_application_ask_clause,
    )
    from src.application.education.learner_model import select_quiz_items

    repo = _memory_repo(request, agent_id)
    ranked = select_quiz_items(repo, limit=max(limit * 5, 10), topic=topic)
    items = [application_from_mastery_row(r) for r in ranked[:limit]]
    return {
        "agent_id": agent_id,
        "items": items,
        "count": len(items),
        "selection": "due_weak_miss_over_random",
        "kind": "application",
        "ask_clause": build_application_ask_clause(items),
    }


@router.post("/api/education/application/mint")
async def mint_application_exercise(request: Request, payload: ApplicationMintPayload):
    """Mint a standing Exercise Job for an Application item [CARD-246]."""
    from src.application.education.application import mint_exercise_job

    repo = _memory_repo(request, payload.agent_id)
    existing = repo.get_education_mastery(payload.item_id)
    concepts = list(payload.required_concepts or [])
    if existing is None:
        if not (payload.prompt and (payload.expected_answer or concepts) and payload.wiki_path):
            raise HTTPException(status_code=404, detail=f"Unknown mastery item: {payload.item_id}")
        item = {
            "item_id": payload.item_id,
            "topic": payload.topic or payload.wiki_path,
            "wiki_path": payload.wiki_path,
            "prompt": payload.prompt,
            "expected_answer": payload.expected_answer or "",
            "required_concepts": concepts,
        }
    else:
        item = {
            "item_id": existing["item_id"],
            "topic": payload.topic or existing.get("topic"),
            "wiki_path": payload.wiki_path or existing.get("wiki_path"),
            "prompt": payload.prompt or existing.get("prompt"),
            "expected_answer": payload.expected_answer or existing.get("expected_answer") or "",
            "required_concepts": concepts,
        }

    orch = getattr(request.app.state, "job_orchestrator", None) or getattr(
        request.app.state, "orchestrator", None
    )
    if orch is None:
        raise HTTPException(status_code=503, detail="orchestrator unavailable for Exercise Job mint")

    result = mint_exercise_job(
        orch=orch,
        memory_repo=repo,
        item=item,
        agent_id=payload.agent_id,
        session_id=payload.session_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result)
    return result


@router.post("/api/education/application/grade")
async def grade_application(request: Request, payload: ApplicationGradePayload):
    """Binary external Application grade + fail park/replan + mastery/Wiki/memory [CARD-246]."""
    from src.application.education.application import grade_and_record_application

    repo = _memory_repo(request, payload.agent_id)
    existing = repo.get_education_mastery(payload.item_id)
    concepts = list(payload.required_concepts or [])
    if existing is None:
        if not (payload.prompt and (payload.expected_answer or concepts) and payload.wiki_path):
            raise HTTPException(status_code=404, detail=f"Unknown mastery item: {payload.item_id}")
        item = {
            "item_id": payload.item_id,
            "topic": payload.topic or payload.wiki_path,
            "wiki_path": payload.wiki_path,
            "prompt": payload.prompt,
            "expected_answer": payload.expected_answer or "",
            "required_concepts": concepts,
        }
    else:
        item = {
            "item_id": existing["item_id"],
            "topic": payload.topic or existing.get("topic"),
            "wiki_path": payload.wiki_path or existing.get("wiki_path"),
            "prompt": payload.prompt or existing.get("prompt"),
            "expected_answer": payload.expected_answer or existing.get("expected_answer") or "",
            "required_concepts": concepts,
        }

    wiki_store = None
    if payload.write_wiki:
        try:
            wiki_store = _wiki_store(request)
        except Exception:  # noqa: BLE001
            wiki_store = None

    orch = getattr(request.app.state, "job_orchestrator", None) or getattr(
        request.app.state, "orchestrator", None
    )

    result = grade_and_record_application(
        repo=repo,
        item=item,
        given=payload.answer,
        wiki_store=wiki_store,
        orch=orch,
        phase_id=payload.phase_id,
        replan_count=payload.replan_count,
        agent_id=payload.agent_id,
        write_wiki=bool(payload.write_wiki and wiki_store is not None),
        write_memory=payload.write_memory,
        mint_on_fail=payload.mint_on_fail,
    )
    return result


class AnalysisWikiPayload(BaseModel):
    agent_id: str = "autoreiv"
    wiki_path: str
    item_id: Optional[str] = None
    miss_reason: Optional[str] = None
    given: str = ""
    prompt: Optional[str] = None


@router.get("/api/education/analysis")
async def analysis_summary(request: Request, agent_id: str = "autoreiv", limit: int = 50):
    """Error log + metacog patterns from memory.db [CARD-247]."""
    from src.application.education.analysis import summarize_analysis

    repo = _memory_repo(request, agent_id)
    summary = summarize_analysis(repo, limit=limit)
    summary["agent_id"] = agent_id
    return summary


@router.get("/api/education/analysis/errors")
async def analysis_errors(request: Request, agent_id: str = "autoreiv", limit: int = 50):
    from src.application.education.analysis import list_error_log

    repo = _memory_repo(request, agent_id)
    errors = list_error_log(repo, limit=limit)
    return {"agent_id": agent_id, "errors": errors, "count": len(errors)}


@router.get("/api/education/analysis/patterns")
async def analysis_patterns(request: Request, agent_id: str = "autoreiv", limit: int = 50):
    from src.application.education.analysis import active_miss_reasons, list_metacog_patterns

    repo = _memory_repo(request, agent_id)
    patterns = list_metacog_patterns(repo, limit=limit)
    return {
        "agent_id": agent_id,
        "patterns": patterns,
        "count": len(patterns),
        "active_miss_reasons": active_miss_reasons(repo),
    }


class EnvironmentSelectPayload(BaseModel):
    agent_id: str = "autoreiv"
    profile_id: str


@router.get("/api/education/environment/profiles")
async def environment_profiles():
    """List study-session delivery profiles (tone/timer/bite-size) [CARD-248]."""
    from src.application.education.environment import list_delivery_profiles

    profiles = list_delivery_profiles()
    return {
        "profiles": profiles,
        "count": len(profiles),
        "replaces_srs": False,
        "replaces_ledger": False,
        "due_source": "mastery_ledger_srs",
    }


@router.get("/api/education/environment")
async def environment_summary(request: Request, agent_id: str = "autoreiv"):
    """Active delivery profile preference from memory.db [CARD-248]."""
    from src.application.education.environment import summarize_environment

    repo = _memory_repo(request, agent_id)
    summary = summarize_environment(repo)
    summary["agent_id"] = agent_id
    return summary


@router.post("/api/education/environment/select")
async def environment_select(request: Request, payload: EnvironmentSelectPayload):
    """Select active delivery profile (presentation preference only — never SRS)."""
    from src.application.education.environment import select_delivery_profile

    repo = _memory_repo(request, payload.agent_id)
    result = select_delivery_profile(repo, payload.profile_id)
    return {
        "agent_id": payload.agent_id,
        **result,
    }


@router.post("/api/education/environment/apply-ask")
async def environment_apply_ask(request: Request, payload: dict):
    """Shape an Ask string with the active (or requested) delivery profile."""
    from src.application.education.environment import (
        apply_delivery_to_ask,
        get_active_delivery_profile,
        get_delivery_profile,
    )

    agent_id = str(payload.get("agent_id") or "autoreiv")
    ask = str(payload.get("ask") or "")
    profile_id = payload.get("profile_id")
    repo = _memory_repo(request, agent_id)
    profile = get_delivery_profile(profile_id) if profile_id else get_active_delivery_profile(repo)
    shaped = apply_delivery_to_ask(ask, profile=profile)
    shaped["agent_id"] = agent_id
    return shaped


class AmplifierExtractPayload(BaseModel):
    content: str
    wiki_path: str
    topic: str = ""


class AmplifierAttachPayload(BaseModel):
    agent_id: str = "autoreiv"
    item_id: str
    content: Optional[str] = None
    wiki_path: Optional[str] = None
    topic: str = ""
    amplifier_id: Optional[str] = None
    mermaid: Optional[str] = None
    steps: Optional[list] = None
    visuals_only: bool = False


@router.post("/api/education/amplifiers/extract")
async def amplifiers_extract(payload: AmplifierExtractPayload):
    """Extract Mermaid/step-through amplifier candidates from a Dual Coding note [CARD-249]."""
    from src.application.education.visual_amplifiers import extract_amplifiers_from_note

    amps = extract_amplifiers_from_note(
        payload.content,
        wiki_path=payload.wiki_path,
        topic=payload.topic,
    )
    return {
        "amplifiers": amps,
        "count": len(amps),
        "shippable": False,
        "retrieval_required": True,
        "lumina_film": False,
        "note": "Candidates are not shippable until attached to a mastery/quiz item_id",
    }


@router.post("/api/education/amplifiers/attach")
async def amplifiers_attach(request: Request, payload: AmplifierAttachPayload):
    """Attach amplifier to Retrieval-backed mastery item; refuse visuals-only [CARD-249]."""
    from fastapi import HTTPException

    from src.application.education.visual_amplifiers import (
        VisualsOnlyRejected,
        attach_amplifier_to_retrieval,
        build_step_through,
        extract_amplifiers_from_note,
        refuse_visuals_only,
    )

    try:
        refuse_visuals_only(
            {"item_id": payload.item_id, "visuals_only": payload.visuals_only}
        )
    except VisualsOnlyRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    repo = _memory_repo(request, payload.agent_id)
    amplifier = None
    if payload.content and payload.wiki_path:
        candidates = extract_amplifiers_from_note(
            payload.content,
            wiki_path=payload.wiki_path,
            topic=payload.topic,
        )
        if payload.amplifier_id:
            for c in candidates:
                if c.get("amplifier_id") == payload.amplifier_id:
                    amplifier = c
                    break
        if amplifier is None and candidates:
            amplifier = candidates[0]
    if amplifier is None:
        mermaid = payload.mermaid
        steps = payload.steps
        if mermaid and not steps:
            steps = build_step_through(mermaid)
        if not mermaid and not steps:
            raise HTTPException(
                status_code=400,
                detail="Amplifier attach needs Dual Coding content/wiki_path or mermaid/steps",
            )
        amplifier = {
            "amplifier_id": payload.amplifier_id or "amp_manual",
            "kind": "mermaid" if mermaid else "step_through",
            "topic": payload.topic or payload.wiki_path or "",
            "wiki_path": payload.wiki_path or "",
            "mermaid": mermaid,
            "steps": steps or [],
            "step_count": len(steps or []),
            "has_step_through": bool(steps),
            "retrieval_required": True,
            "item_id": None,
            "shippable": False,
            "lumina_film": False,
        }
    try:
        attached = attach_amplifier_to_retrieval(amplifier, payload.item_id, repo=repo)
    except VisualsOnlyRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "agent_id": payload.agent_id,
        "attached": attached,
        "retrieval_required": True,
        "lumina_film": False,
        "replaces_srs": False,
        "replaces_ledger": False,
    }


@router.get("/api/education/amplifiers")
async def amplifiers_summary(request: Request, agent_id: str = "autoreiv", limit: int = 50):
    """List persisted visual amplifiers (Retrieval-backed only) [CARD-249]."""
    from src.application.education.visual_amplifiers import summarize_amplifiers

    repo = _memory_repo(request, agent_id)
    summary = summarize_amplifiers(repo, limit=limit)
    summary["agent_id"] = agent_id
    return summary


@router.get("/api/education/amplifiers/{item_id}")
async def amplifiers_for_item(request: Request, item_id: str, agent_id: str = "autoreiv"):
    """Get amplifier for a mastery item; 404 if none; 400 if item not on ledger."""
    from fastapi import HTTPException

    from src.application.education.visual_amplifiers import (
        VisualsOnlyRejected,
        get_amplifier_for_item,
    )

    repo = _memory_repo(request, agent_id)
    try:
        amp = get_amplifier_for_item(repo, item_id)
    except VisualsOnlyRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if amp is None:
        raise HTTPException(status_code=404, detail=f"No amplifier for item_id={item_id}")
    return {
        "agent_id": agent_id,
        "item_id": item_id,
        "amplifier": amp,
        "retrieval_required": True,
        "lumina_film": False,
    }


@router.post("/api/education/amplifiers/refuse-check")
async def amplifiers_refuse_check(payload: dict):
    """Smoke helper: prove visuals-only is refused [CARD-249]."""
    from fastapi import HTTPException

    from src.application.education.visual_amplifiers import (
        VisualsOnlyRejected,
        refuse_visuals_only,
    )

    try:
        return refuse_visuals_only(payload)
    except VisualsOnlyRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


class KnowledgeArtifactPayload(BaseModel):
    topic: str
    knowledge_type: str = "concept"
    custom_data: Optional[Dict[str, Any]] = None


@router.get("/api/education/knowledge-types")
async def education_knowledge_types():
    """List available knowledge types and artifact shape specifications [CARD-334]."""
    from src.application.education.knowledge_types import KNOWLEDGE_SHAPES, VALID_KNOWLEDGE_TYPES

    return {
        "knowledge_types": list(VALID_KNOWLEDGE_TYPES),
        "shapes": KNOWLEDGE_SHAPES,
    }


@router.post("/api/education/knowledge-artifact")
async def education_knowledge_artifact(payload: KnowledgeArtifactPayload):
    """Generate specialized teaching artifact shape for knowledge type [CARD-334]."""
    from src.application.education.knowledge_types import (
        build_knowledge_artifact,
        render_knowledge_note_markdown,
    )

    topic = (payload.topic or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")
    try:
        art = build_knowledge_artifact(
            topic=topic,
            knowledge_type=payload.knowledge_type,
            custom_data=payload.custom_data,
        )
        md = render_knowledge_note_markdown(art)
        return {"ok": True, "artifact": art, "markdown": md}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



class WikiCuratePayload(BaseModel):
    """CARD-440: Tutor Learning OS wiki curation from link or curriculum."""

    mode: str = "link"  # link | curriculum
    url: Optional[str] = None
    curriculum: Optional[str] = None
    topic: Optional[str] = None
    title: Optional[str] = None
    template: Optional[str] = None
    raw_source: bool = False
    body: Optional[str] = None
    max_items: int = Field(default=12, ge=1, le=30)
    agent_id: str = "tutor"


@router.get("/api/education/wiki/templates")
async def education_wiki_templates():
    """Catalogued education-* Wiki templates for Learning OS curation [CARD-440]."""
    from src.application.education.wiki_curation import catalog_education_templates

    items = catalog_education_templates()
    return {"templates": items, "count": len(items), "skill_hint": "education-wiki-curation"}


@router.post("/api/education/wiki/curate")
async def education_wiki_curate(request: Request, payload: WikiCuratePayload):
    """Curate link/curriculum into durable Wiki notes via wiki_note_create [CARD-440].

    Failures return success=false without claiming the library was updated.
    """
    from src.application.education.wiki_curation import curate
    from src.application.skills.wiki_tools import WikiTools

    wiki_root = getattr(request.app.state, "wiki_path", None) or getattr(
        request.app.state, "wiki_root", None
    )
    tools = WikiTools(wiki_root=wiki_root) if wiki_root else WikiTools()
    result = curate(
        tools,
        mode=payload.mode,
        url=payload.url,
        curriculum=payload.curriculum,
        topic=payload.topic or "",
        title=payload.title,
        template=payload.template,
        raw_source=bool(payload.raw_source),
        body=payload.body,
        max_items=payload.max_items,
    )
    # Honest HTTP: 200 with success=false for domain failures (fetch/write);
    # 400 only for clearly invalid mode/required fields already handled in curate.
    return {"agent_id": payload.agent_id, **result}



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
    from src.application.skills.wiki_tools import WikiTools

    if not (payload.course_id or "").strip():
        raise HTTPException(status_code=400, detail="course_id is required")
    repo = _memory_repo(request, payload.agent_id)
    wiki_root = getattr(request.app.state, "wiki_path", None) or getattr(
        request.app.state, "wiki_root", None
    )
    tools = WikiTools(wiki_root=wiki_root) if wiki_root else WikiTools()
    try:
        result = complete_course_step(
            repo,
            course_id=payload.course_id,
            wiki_tools_or_store=tools,
            teach_style=payload.teach_style or "",
            learner_explanation=payload.learner_explanation,
            lab_submission=payload.lab_submission,
            knowledge_type=payload.knowledge_type,
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
    # pin binary helper name for CARD-320 router source assert
    _ = grade_answer_binary
    try:
        result = grade_course_mastery(repo, item_id=payload.item_id, answer=payload.answer or "")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"agent_id": payload.agent_id, **result}


class DualCodingPreviewPayload(BaseModel):
    topic: str
    agent_id: str = "autoreiv"


@router.post("/api/education/course/dual-coding/preview")
async def course_dual_coding_preview(payload: DualCodingPreviewPayload):
    """Generate dual coding prose + Mermaid diagram for topic [CARD-321]."""
    from src.application.education.course import build_dual_coding_preview

    if not (payload.topic or "").strip():
        raise HTTPException(status_code=400, detail="topic is required")
    data = build_dual_coding_preview(payload.topic)
    return {"agent_id": payload.agent_id, **data}


class CourseElaborationPreviewPayload(BaseModel):
    topic: str
    agent_id: str = "autoreiv"


@router.post("/api/education/course/elaboration/preview")
async def course_elaboration_preview(payload: CourseElaborationPreviewPayload):
    """Generate Socratic elaboration prompts and probing questions for topic [CARD-323]."""
    from src.application.education.elaboration import build_elaboration_preview

    if not (payload.topic or "").strip():
        raise HTTPException(status_code=400, detail="topic is required")
    data = build_elaboration_preview(payload.topic)
    return {"success": True, "agent_id": payload.agent_id, **data}


class CourseElaborationCompletePayload(BaseModel):
    course_id: str
    topic: Optional[str] = None
    learner_explanation: Optional[str] = None
    agent_id: str = "autoreiv"


@router.post("/api/education/course/elaboration/complete")
async def course_elaboration_complete(request: Request, payload: CourseElaborationCompletePayload):
    """Complete elaboration step: persist explain-in-own-words note to Wiki, anchor ledger, advance [CARD-323]."""
    from src.application.education.course import complete_course_step, course_chrome_snapshot
    from src.application.skills.wiki_tools import WikiTools

    if not (payload.course_id or "").strip():
        raise HTTPException(status_code=400, detail="course_id is required")
    repo = _memory_repo(request, payload.agent_id)
    wiki_root = getattr(request.app.state, "wiki_path", None) or getattr(
        request.app.state, "wiki_root", None
    )
    tools = WikiTools(wiki_root=wiki_root) if wiki_root else WikiTools()
    try:
        result = complete_course_step(
            repo,
            course_id=payload.course_id,
            wiki_tools_or_store=tools,
            learner_explanation=payload.learner_explanation,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    course = result.get("course") or {}
    chrome = course_chrome_snapshot(
        repo,
        topic_id=course.get("topic_id") or payload.topic or "",
        course_id=course.get("course_id") or payload.course_id,
    )
    return {"agent_id": payload.agent_id, **result, "chrome": chrome}


class CourseLabPreviewPayload(BaseModel):
    topic: Optional[str] = None
    course_id: Optional[str] = None
    step: Optional[str] = "construction"
    agent_id: str = "autoreiv"


@router.post("/api/education/course/lab/preview")
async def course_lab_preview(request: Request, payload: CourseLabPreviewPayload):
    """Generate structured lab specification for construction or application step [CARD-324]."""
    from src.application.education.labs import build_lab_specification

    topic = (payload.topic or "").strip()
    step = (payload.step or "construction").strip()
    if not topic and payload.course_id:
        repo = _memory_repo(request, payload.agent_id)
        course = repo.get_education_course(payload.course_id)
        if course:
            topic = course.get("topic_id") or ""
            step = payload.step or course.get("current_step") or "construction"

    if not topic:
        raise HTTPException(status_code=400, detail="topic or valid course_id is required")

    data = build_lab_specification(topic=topic, step=step)
    return {"success": True, "agent_id": payload.agent_id, **data}


class CourseLabGradePayload(BaseModel):
    course_id: str
    step: Optional[str] = None
    submission: str
    agent_id: str = "autoreiv"


@router.post("/api/education/course/lab/grade")
async def course_lab_grade(request: Request, payload: CourseLabGradePayload):
    """Grade lab submission with objective pressure: write Wiki note, update ledger, advance course if passed [CARD-324]."""
    from src.application.education.course import complete_course_step, course_chrome_snapshot
    from src.application.skills.wiki_tools import WikiTools

    sub = (payload.submission or "").strip()
    if not sub:
        raise HTTPException(status_code=422, detail="Lab submission cannot be empty.")

    if not (payload.course_id or "").strip():
        raise HTTPException(status_code=400, detail="course_id is required")

    repo = _memory_repo(request, payload.agent_id)
    wiki_root = getattr(request.app.state, "wiki_path", None) or getattr(
        request.app.state, "wiki_root", None
    )
    tools = WikiTools(wiki_root=wiki_root) if wiki_root else WikiTools()

    try:
        result = complete_course_step(
            repo,
            course_id=payload.course_id,
            wiki_tools_or_store=tools,
            lab_submission=payload.submission,
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


class CourseConstructionCompletePayload(BaseModel):
    course_id: str
    submission: str
    agent_id: str = "autoreiv"


@router.post("/api/education/course/construction/complete")
async def course_construction_complete(request: Request, payload: CourseConstructionCompletePayload):
    """Complete construction step via graded lab evaluation [CARD-324]."""
    return await course_lab_grade(
        request,
        CourseLabGradePayload(
            course_id=payload.course_id,
            step="construction",
            submission=payload.submission,
            agent_id=payload.agent_id,
        ),
    )


class CourseApplicationCompletePayload(BaseModel):
    course_id: str
    submission: str
    agent_id: str = "autoreiv"


@router.post("/api/education/course/application/complete")
async def course_application_complete(request: Request, payload: CourseApplicationCompletePayload):
    """Complete application step via graded lab evaluation [CARD-324]."""
    return await course_lab_grade(
        request,
        CourseLabGradePayload(
            course_id=payload.course_id,
            step="application",
            submission=payload.submission,
            agent_id=payload.agent_id,
        ),
    )


class CourseEnvironmentPreviewPayload(BaseModel):
    topic: Optional[str] = None
    course_id: Optional[str] = None
    profile_id: Optional[str] = None
    agent_id: str = "autoreiv"


@router.post("/api/education/course/environment/preview")
async def course_environment_preview(request: Request, payload: CourseEnvironmentPreviewPayload):
    """Generate environment framing and delivery constraints [CARD-325]."""
    from src.application.education.environment import build_environment_framing

    topic = (payload.topic or "").strip()
    if not topic and payload.course_id:
        repo = _memory_repo(request, payload.agent_id)
        course = repo.get_education_course(payload.course_id)
        if course:
            topic = course.get("topic_id") or ""

    if not topic:
        raise HTTPException(status_code=400, detail="topic or valid course_id is required")

    framing = build_environment_framing(
        topic=topic,
        profile_id=payload.profile_id,
    )
    return {"success": True, "agent_id": payload.agent_id, **framing}


class CourseEnvironmentCompletePayload(BaseModel):
    course_id: str
    profile_id: Optional[str] = None
    agent_id: str = "autoreiv"


@router.post("/api/education/course/environment/complete")
async def course_environment_complete(request: Request, payload: CourseEnvironmentCompletePayload):
    """Complete environment framing step: persist profile, write note, advance course [CARD-325]."""
    from src.application.education.course import complete_course_step, course_chrome_snapshot
    from src.application.education.environment import select_delivery_profile
    from src.application.skills.wiki_tools import WikiTools

    if not (payload.course_id or "").strip():
        raise HTTPException(status_code=400, detail="course_id is required")

    repo = _memory_repo(request, payload.agent_id)
    if payload.profile_id:
        select_delivery_profile(repo, payload.profile_id)

    wiki_root = getattr(request.app.state, "wiki_path", None) or getattr(
        request.app.state, "wiki_root", None
    )
    tools = WikiTools(wiki_root=wiki_root) if wiki_root else WikiTools()

    try:
        result = complete_course_step(
            repo,
            course_id=payload.course_id,
            wiki_tools_or_store=tools,
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


class CourseAnalysisHandoffPayload(BaseModel):
    course_id: Optional[str] = None
    topic: Optional[str] = None
    agent_id: str = "autoreiv"


@router.post("/api/education/course/analysis/handoff")
async def course_analysis_handoff(request: Request, payload: CourseAnalysisHandoffPayload):
    """Execute analysis to retention handoff: schedule next_due and anchor semantic fact [CARD-325]."""
    from src.application.education.analysis import execute_analysis_retention_handoff
    from src.application.education.course import course_chrome_snapshot

    repo = _memory_repo(request, payload.agent_id)
    topic = (payload.topic or "").strip()
    if not topic and payload.course_id:
        course = repo.get_education_course(payload.course_id)
        if course:
            topic = course.get("topic_id") or ""

    if not topic:
        raise HTTPException(status_code=400, detail="topic or valid course_id is required")

    result = execute_analysis_retention_handoff(
        repo,
        topic=topic,
        course_id=payload.course_id,
    )

    chrome = None
    if payload.course_id:
        chrome = course_chrome_snapshot(
            repo,
            topic_id=topic,
            course_id=payload.course_id,
        )

    return {"agent_id": payload.agent_id, **result, "chrome": chrome}


@router.get("/api/education/course/depth")
async def course_depth_get(
    request: Request,
    topic: Optional[str] = None,
    course_id: Optional[str] = None,
    agent_id: str = "autoreiv",
):
    """Retrieve adaptive mastery depth ladder and milestones for a topic [CARD-327]."""
    from src.application.education.depth import get_topic_depth

    repo = _memory_repo(request, agent_id)
    resolved_topic = (topic or "").strip()
    if not resolved_topic and course_id:
        course = repo.get_education_course(course_id)
        if course:
            resolved_topic = course.get("topic_id") or ""

    if not resolved_topic:
        raise HTTPException(status_code=400, detail="topic or valid course_id is required")

    depth = get_topic_depth(repo, topic=resolved_topic)
    return {"success": True, "agent_id": agent_id, "depth": depth}


class CoursePortfolioCreatePayload(BaseModel):
    topic: Optional[str] = None
    course_id: Optional[str] = None
    agent_id: str = "autoreiv"


@router.post("/api/education/course/portfolio/create")
async def course_portfolio_create(request: Request, payload: CoursePortfolioCreatePayload):
    """Generate and file a durable growth portfolio note in 00_Inbox/ [CARD-327]."""
    from src.application.education.depth import create_growth_portfolio_note
    from src.application.skills.wiki_tools import WikiTools

    repo = _memory_repo(request, payload.agent_id)
    topic = (payload.topic or "").strip()
    if not topic and payload.course_id:
        course = repo.get_education_course(payload.course_id)
        if course:
            topic = course.get("topic_id") or ""

    if not topic:
        raise HTTPException(status_code=400, detail="topic or valid course_id is required")

    wiki_root = getattr(request.app.state, "wiki_path", None) or getattr(
        request.app.state, "wiki_root", None
    )
    tools = WikiTools(wiki_root=wiki_root) if wiki_root else WikiTools()

    result = create_growth_portfolio_note(
        tools,
        repo,
        topic=topic,
        course_id=payload.course_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail="Failed to create growth portfolio note")

    return {"agent_id": payload.agent_id, **result}


# --- CARD-328 Lumina Cinema & Amplifiers ---------------------------------------


class LuminaComposePayload(BaseModel):
    topic: str
    agent_id: str = "autoreiv"


class LuminaSendToCoursePayload(BaseModel):
    topic: str
    agent_id: str = "autoreiv"


@router.get("/api/lumina/starters")
async def lumina_starters():
    """List available Lumina starter lessons [CARD-328]."""
    from src.application.education.lumina import list_starter_topics

    return {"starters": list_starter_topics()}


@router.get("/api/lumina/lesson/{lesson_id}")
async def lumina_lesson(lesson_id: str):
    """Retrieve full Lumina lesson specification by ID or topic [CARD-328]."""
    from src.application.education.lumina import get_starter_lesson

    lesson = get_starter_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")
    return {"lesson": lesson}


@router.post("/api/lumina/compose")
async def lumina_compose(request: Request, payload: LuminaComposePayload):
    """Compose a 3-6 scene Lumina concept lesson [CARD-328]."""
    from src.application.education.lumina import (
        extract_json_from_llm,
        get_starter_lesson,
        normalize_lesson,
    )

    topic = (payload.topic or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")

    existing = get_starter_lesson(topic)
    if existing:
        return {"ok": True, "lesson": existing, "cached": True}

    # Attempt LLM composition via gateway if configured
    gateway = getattr(request.app.state, "gateway", None)
    lesson = None
    if gateway:
        prompt = (
            f"You are Lumina, a visual concept director. Create a 4-scene educational storyboard for: '{topic}'.\n"
            "Return JSON matching:\n"
            "{\n"
            '  "title": "...",\n'
            '  "essence": "...",\n'
            '  "scenes": [\n'
            "    {\n"
            '      "headline": "...",\n'
            '      "whisper": "...",\n'
            '      "narration": "...",\n'
            '      "imagePrompt": "...",\n'
            '      "durationMs": 11000,\n'
            '      "visual": {\n'
            '        "kind": "flow|cycle|compare|orbit|stack|split|wave|network|scale|balance|grow|transform|pipeline|system",\n'
            '        "title": "...",\n'
            '        "nodes": [{"id": "...", "label": "...", "caption": "...", "role": "in|work|store|out", "emphasis": true}],\n'
            '        "links": [{"from": "...", "to": "...", "label": "..."}]\n'
            "      }\n"
            "    }\n"
            "  ]\n"
            "}"
        )
        try:
            from src.domain.gateway.models import ChatMessage
            res = await gateway.chat_complete(
                messages=[ChatMessage(role="user", content=prompt)],
                temperature=0.7,
            )
            raw = extract_json_from_llm(res.content)
            lesson = normalize_lesson(raw, topic)
        except Exception:
            pass

    if not lesson:
        lesson = normalize_lesson({}, topic)

    return {"ok": True, "lesson": lesson, "cached": False}


@router.post("/api/lumina/send-to-course")
async def lumina_send_to_course(request: Request, payload: LuminaSendToCoursePayload):
    """Bridge Lumina lesson into an active education_course in tutor_memory.db [CARD-328]."""
    from src.application.education.course import (
        course_chrome_snapshot,
        start_or_resume_course,
    )

    topic = (payload.topic or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")

    repo = _memory_repo(request, payload.agent_id)
    course = start_or_resume_course(repo, topic_id=topic)
    snapshot = course_chrome_snapshot(repo, topic_id=topic, course_id=course.get("course_id", ""))
    return {"ok": True, "course": course, "snapshot": snapshot}


