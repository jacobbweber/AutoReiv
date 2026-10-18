"""Education course step preview, lab, environment, depth, and growth portfolio routes [CARD-715]."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.web.routers.education_deps import (
    _compose_current_step,
    _course_wiki_tools,
    _memory_repo,
)

router = APIRouter(tags=["Education"])


class DualCodingPreviewPayload(BaseModel):
    topic: str
    agent_id: str = "autoreiv"


@router.post("/api/education/course/dual-coding/preview")
async def course_dual_coding_preview(request: Request, payload: DualCodingPreviewPayload):
    """Dual coding built from your wiki notes on the topic, or the reason it was skipped [CARD-321, CARD-640]."""
    from src.application.education.dual_coding import compose_dual_coding

    if not (payload.topic or "").strip():
        raise HTTPException(status_code=400, detail="topic is required")
    composed = await compose_dual_coding(
        getattr(request.app.state, "gateway", None), _course_wiki_tools(request), payload.topic
    )
    return {"agent_id": payload.agent_id, **composed}


class CourseElaborationPreviewPayload(BaseModel):
    topic: str
    learner_explanation: Optional[str] = None
    agent_id: str = "autoreiv"


@router.post("/api/education/course/elaboration/preview")
async def course_elaboration_preview(request: Request, payload: CourseElaborationPreviewPayload):
    """The elaboration ask; follow-up questions only from the learner's own explanation [CARD-323, CARD-644]."""
    from src.application.education.elaboration import build_elaboration_preview
    from src.application.education.grounded_steps import compose_step_content

    if not (payload.topic or "").strip():
        raise HTTPException(status_code=400, detail="topic is required")
    data = build_elaboration_preview(payload.topic)
    composed = await compose_step_content(
        getattr(request.app.state, "gateway", None),
        _course_wiki_tools(request),
        payload.topic,
        "elaboration",
        learner_text=payload.learner_explanation,
    )
    if composed.get("ok"):
        data["probing_questions"] = list(composed.get("probes") or [])
    return {
        "success": True,
        "agent_id": payload.agent_id,
        **data,
        "skip_reason": composed.get("skip_reason"),
        "sources": composed.get("sources") or [],
    }


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
    composed = await _compose_current_step(request, repo, payload.course_id, tools, payload.learner_explanation)
    try:
        result = complete_course_step(
            repo,
            course_id=payload.course_id,
            wiki_tools_or_store=tools,
            learner_explanation=payload.learner_explanation,
            composed=composed,
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
    """Lab built from your wiki notes on the topic, or the reason it was skipped [CARD-324, CARD-643]."""
    from src.application.education.grounded_steps import compose_step_content

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
    if step not in ("construction", "application"):
        step = "construction"

    composed = await compose_step_content(
        getattr(request.app.state, "gateway", None), _course_wiki_tools(request), topic, step
    )
    return {"success": True, "agent_id": payload.agent_id, **composed, "step": step}


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
    composed = await _compose_current_step(request, repo, payload.course_id, tools)

    try:
        result = complete_course_step(
            repo,
            course_id=payload.course_id,
            wiki_tools_or_store=tools,
            lab_submission=payload.submission,
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
    """Where to practise the topic, from your wiki notes, with your delivery profile [CARD-325, CARD-642]."""
    from src.application.education.environment import get_active_delivery_profile, get_delivery_profile
    from src.application.education.grounded_steps import compose_step_content

    repo = _memory_repo(request, payload.agent_id)
    topic = (payload.topic or "").strip()
    if not topic and payload.course_id:
        course = repo.get_education_course(payload.course_id)
        if course:
            topic = course.get("topic_id") or ""

    if not topic:
        raise HTTPException(status_code=400, detail="topic or valid course_id is required")

    profile = get_delivery_profile(payload.profile_id) if payload.profile_id else get_active_delivery_profile(repo)
    composed = await compose_step_content(
        getattr(request.app.state, "gateway", None), _course_wiki_tools(request), topic, "environment"
    )
    return {"success": True, "agent_id": payload.agent_id, **composed, "profile": profile}


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
    composed = await _compose_current_step(request, repo, payload.course_id, tools)

    try:
        result = complete_course_step(
            repo,
            course_id=payload.course_id,
            wiki_tools_or_store=tools,
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
