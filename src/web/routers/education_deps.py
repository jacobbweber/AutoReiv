"""Shared dependency helpers for Education routers [CARD-715]."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from fastapi import Request


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


def _course_wiki_tools(request: Request):
    from src.application.skills.wiki_tools import WikiTools

    wiki_root = getattr(request.app.state, "wiki_path", None) or getattr(request.app.state, "wiki_root", None)
    return WikiTools(wiki_root=wiki_root) if wiki_root else WikiTools()


def _repeat_of(row: Optional[Dict[str, Any]]) -> Optional[Tuple[str, str]]:
    """The saved (question, answer) a new course question repeats [CARD-654]."""
    return (str(row.get("prompt") or ""), str(row.get("expected_answer") or "")) if row else None


async def _compose_current_step(
    request: Request,
    repo: Any,
    course_id: str,
    tools: Any,
    learner_explanation: Optional[str] = None,
    lab_submission: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Grounded content for the course's current step, built from the learner's wiki notes via one
    model call [CARD-640, CARD-646]. None for steps that need none; a skip dict when it can't be grounded."""
    from src.application.education.grounded import find_duplicate_item, ledger_items
    from src.application.education.grounded_steps import compose_course_step
    from src.application.education.priming_schema import slug_topic

    current = repo.get_education_course(course_id) or {}
    topic = current.get("topic_id") or ""
    step = current.get("current_step") or ""
    own = f"course_{slug_topic(topic.strip())}_{step}"[:48]
    asked = [
        (str(r.get("prompt") or ""), str(r.get("expected_answer") or ""))
        for r in ledger_items(repo)
        if (r.get("topic") or "").strip() == topic.strip() and r.get("item_id") != own
    ]
    avoid = [q for q, _ in asked]
    return await compose_course_step(
        getattr(request.app.state, "gateway", None),
        tools,
        topic,
        step,
        learner_explanation=learner_explanation,
        lab_submission=lab_submission,
        avoid_questions=avoid,
        duplicate_of=lambda q, a: _repeat_of(find_duplicate_item(repo, q, a, own_item_id=own)),
        asked=asked,
    )
