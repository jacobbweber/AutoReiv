"""Education practice, elaboration, construction, application, analysis, environment, amplifiers, and wiki curation routes [CARD-715]."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.web.routers.education_deps import _memory_repo, _wiki_store

router = APIRouter(tags=["Education"])


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


class AnalysisWikiPayload(BaseModel):
    agent_id: str = "autoreiv"
    wiki_path: str
    item_id: Optional[str] = None
    miss_reason: Optional[str] = None
    given: str = ""
    prompt: Optional[str] = None


class EnvironmentSelectPayload(BaseModel):
    agent_id: str = "autoreiv"
    profile_id: str


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
        "note": "Candidates are not shippable until attached to a mastery/quiz item_id",
    }


@router.post("/api/education/amplifiers/attach")
async def amplifiers_attach(request: Request, payload: AmplifierAttachPayload):
    """Attach amplifier to Retrieval-backed mastery item; refuse visuals-only [CARD-249]."""
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
        }
    try:
        attached = attach_amplifier_to_retrieval(amplifier, payload.item_id, repo=repo)
    except VisualsOnlyRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "agent_id": payload.agent_id,
        "attached": attached,
        "retrieval_required": True,
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
    }


@router.post("/api/education/amplifiers/refuse-check")
async def amplifiers_refuse_check(payload: dict):
    """Smoke helper: prove visuals-only is refused [CARD-249]."""
    from src.application.education.visual_amplifiers import (
        VisualsOnlyRejected,
        refuse_visuals_only,
    )

    try:
        return refuse_visuals_only(payload)
    except VisualsOnlyRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/education/knowledge-types")
async def education_knowledge_types():
    """List available knowledge types and artifact shape specifications [CARD-334]."""
    from src.application.education.knowledge_types import KNOWLEDGE_SHAPES, VALID_KNOWLEDGE_TYPES

    return {
        "knowledge_types": list(VALID_KNOWLEDGE_TYPES),
        "shapes": KNOWLEDGE_SHAPES,
    }


@router.get("/api/education/wiki/templates")
async def education_wiki_templates():
    """Catalogued education-* Wiki templates for Learning OS curation [CARD-440]."""
    from src.application.education.wiki_curation import catalog_education_templates

    items = catalog_education_templates()
    return {"templates": items, "count": len(items), "skill_hint": "education-wiki-curation"}


@router.post("/api/education/wiki/curate")
async def education_wiki_curate(request: Request, payload: WikiCuratePayload):
    """Curate link/curriculum into durable Wiki notes via wiki_note_create [CARD-440]."""
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
    return {"agent_id": payload.agent_id, **result}
