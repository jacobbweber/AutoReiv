"""Education Retrieval + Retention API [CARD-242]."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(tags=["Education"])


class GradePayload(BaseModel):
    agent_id: str = "assistant"
    item_id: str
    answer: str = ""
    # Optional: register item before grade when extracting on the fly
    topic: Optional[str] = None
    wiki_path: Optional[str] = None
    prompt: Optional[str] = None
    expected_answer: Optional[str] = None


class UpsertItemPayload(BaseModel):
    agent_id: str = "assistant"
    item_id: Optional[str] = None
    topic: str
    wiki_path: str
    prompt: str
    expected_answer: str


class ExtractPayload(BaseModel):
    agent_id: str = "assistant"
    wiki_path: str
    topic: Optional[str] = None
    persist: bool = True


class RetentionRunPayload(BaseModel):
    agent_id: str = "assistant"
    force_due_item_id: Optional[str] = None


def _memory_repo(request: Request, agent_id: str):
    from src.infrastructure.data.resolver import DataDirResolver
    from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

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
async def list_mastery(request: Request, agent_id: str = "assistant", due_only: bool = False):
    repo = _memory_repo(request, agent_id)
    if due_only:
        rows = repo.list_due_education_mastery()
    else:
        rows = repo.list_education_mastery()
    return {"agent_id": agent_id, "items": rows, "count": len(rows)}


@router.get("/api/education/mastery/due")
async def list_due(request: Request, agent_id: str = "assistant"):
    repo = _memory_repo(request, agent_id)
    rows = repo.list_due_education_mastery()
    return {"agent_id": agent_id, "items": rows, "count": len(rows)}


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
    correct = grade_answer_binary(expected, payload.answer)
    row = repo.record_education_grade(item_id=payload.item_id, correct=correct)
    return {
        "correct": correct,
        "grade": row.get("grade"),
        "next_due": row.get("next_due"),
        "interval_stage": row.get("interval_stage"),
        "item": row,
        "grader": "binary_external",
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
    )
    if hasattr(store, "save_routine"):
        try:
            store.save_routine(routine)
        except Exception:  # noqa: BLE001
            pass
    return {
        "routine_id": EDUCATION_RETENTION_ROUTINE_ID,
        "result": result,
        "session_id": session_id,
    }
