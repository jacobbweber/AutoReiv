"""Education Priming write-back API [CARD-317]."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.web.routers.education import _memory_repo

router = APIRouter(tags=["Education"])


class PrimingWritebackPayload(BaseModel):
    agent_id: str = "tutor"
    topic: str
    teach_style: Optional[str] = None
    search_first: bool = True
    write_learner_fact: bool = True
    attempt_forbidden_tools: Optional[List[str]] = None


class PrimingAskPayload(BaseModel):
    agent_id: str = "tutor"
    topic: str
    wiki_path: Optional[str] = None
    wiki_title: Optional[str] = None
    teach_style: Optional[str] = None


@router.post("/api/education/priming/writeback")
async def priming_writeback_api(request: Request, payload: PrimingWritebackPayload):
    """Priming write-back: Wiki schema/outline note + memory.db ledger anchors [CARD-317]."""
    from src.application.education.priming import priming_writeback
    from src.application.skills.wiki_tools import WikiTools

    topic = (payload.topic or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")

    wiki_root = getattr(request.app.state, "wiki_path", None) or getattr(
        request.app.state, "wiki_root", None
    )
    tools = WikiTools(wiki_root=wiki_root) if wiki_root else WikiTools()
    repo = _memory_repo(request, payload.agent_id)

    forbidden = payload.attempt_forbidden_tools
    if forbidden is None:
        forbidden = ["wiki_overview"]

    result = priming_writeback(
        topic=topic,
        wiki_tools_or_store=tools,
        memory_repo=repo,
        teach_style=(payload.teach_style or "") or "schema first",
        search_first=bool(payload.search_first),
        attempt_forbidden_tools=forbidden,
        write_learner_fact=bool(payload.write_learner_fact),
    )
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result)
    return {
        "agent_id": payload.agent_id,
        "kind": "priming",
        **result,
    }


@router.post("/api/education/priming/ask-clause")
async def priming_ask_clause(payload: PrimingAskPayload):
    """Return Priming-shaped Education Ask clause (wiki_note_* + ledger Done-when)."""
    from src.application.education.priming import build_priming_ask_clause

    topic = (payload.topic or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")
    clause = build_priming_ask_clause(
        topic=topic,
        wiki_path=payload.wiki_path or "",
        wiki_title=payload.wiki_title or "",
        teach_style=payload.teach_style or "",
    )
    return {
        "agent_id": payload.agent_id,
        "kind": "priming",
        "ask_clause": clause,
        "allowlist": [
            "wiki_note_search",
            "wiki_note_list",
            "wiki_note_read",
            "wiki_note_create",
            "wiki_note_append",
        ],
        "forbidden": ["wiki_overview", "wiki_graph"],
    }
