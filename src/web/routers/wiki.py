"""
Wiki Document Management & Knowledge Graph Router [REQ-WEB-003, REQ-WIKI-006, REQ-WIKI-008].
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.application.wiki.service import WikiService


class WikiExportRequest(BaseModel):
    title: str
    content: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    agent_id: str = "assistant"
    session_id: Optional[str] = None
    category: str = "03_Resources"
    tags: Optional[List[str]] = None


router = APIRouter(tags=["Wiki"])


def _get_wiki_service(request: Request) -> WikiService:
    if hasattr(request.app.state, "wiki_service") and request.app.state.wiki_service:
        return request.app.state.wiki_service
    wiki_path = getattr(request.app.state, "wiki_path", "./data/wiki")
    return WikiService(wiki_root=wiki_path)


@router.post("/api/export/wiki")
async def export_to_wiki(request: Request, req: WikiExportRequest):
    service = _get_wiki_service(request)

    if req.messages:
        formatted_messages = []
        for msg in req.messages:
            role = msg.get("role", "user").capitalize()
            text = msg.get("content", "")
            formatted_messages.append(f"**{role}**:\n\n{text}\n")
        body = "\n---\n\n".join(formatted_messages)
        doc_type = "chat_export"
        default_tags = ["chat_thread", req.agent_id]
    else:
        body = req.content or ""
        doc_type = "atomic_note"
        default_tags = ["single_note", req.agent_id]

    tags = req.tags if req.tags else default_tags
    target_category = (
        "inbox"
        if (not req.category or req.category in ("03_Resources", "01_Projects", "02_Areas", "inbox"))
        else req.category
    )

    res = service.create_note(
        title=req.title,
        content=body,
        category=target_category,
        domain="general",
        topic="general",
        document_type=doc_type,
        tags=tags,
        summary=f"Chat export from {req.agent_id} (Session: {req.session_id or 'default'})",
    )

    return {
        "status": "success" if res.get("success") else "error",
        "filepath": res.get("path"),
        "filename": res.get("path", "").rsplit("/", 1)[-1],
        "note": res,
    }


@router.get("/api/wiki/tree")
async def get_wiki_tree(request: Request):
    service = _get_wiki_service(request)
    return service.get_tree()


@router.get("/api/wiki/note")
async def get_wiki_note(request: Request, path: str):
    service = _get_wiki_service(request)
    res = service.get_note(path)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", f"Note '{path}' not found"))
    return res


@router.post("/api/wiki/note")
async def create_wiki_note(request: Request, payload: Dict[str, Any]):
    service = _get_wiki_service(request)
    res = service.create_note(**payload)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to create note"))
    return res


@router.put("/api/wiki/note")
async def update_wiki_note(request: Request, payload: Dict[str, Any]):
    service = _get_wiki_service(request)
    rel_path = payload.get("path") or payload.get("relative_path")
    if not rel_path:
        raise HTTPException(status_code=400, detail="Note path is required")
    res = service.update_note(
        relative_path=rel_path,
        content=payload.get("content", ""),
        update_frontmatter=payload.get("update_frontmatter"),
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to update note"))
    return res


@router.post("/api/wiki/note/append")
async def append_wiki_note(request: Request, payload: Dict[str, Any]):
    service = _get_wiki_service(request)
    rel_path = payload.get("path") or payload.get("relative_path")
    if not rel_path:
        raise HTTPException(status_code=400, detail="Note path is required")
    res = service.append_note(
        relative_path=rel_path,
        content=payload.get("content", ""),
        heading=payload.get("heading"),
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to append to note"))
    return res


@router.get("/api/wiki/notes")
async def list_wiki_notes(
    request: Request,
    category: Optional[str] = None,
    domain: Optional[str] = None,
    topic: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    author: Optional[str] = None,
    pinned: Optional[bool] = None,
    priority: Optional[str] = None,
):
    service = _get_wiki_service(request)
    return service.list_notes(
        category=category,
        domain=domain,
        topic=topic,
        status=status,
        tag=tag,
        author=author,
        pinned=pinned,
        priority=priority,
    )


@router.delete("/api/wiki/note")
async def delete_wiki_note(request: Request, path: str):
    service = _get_wiki_service(request)
    deleted = service.delete_note(path)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Note '{path}' not found")
    return {"success": True, "path": path}


@router.get("/api/wiki/search")
async def search_wiki_notes(request: Request, q: str, limit: int = 5):
    service = _get_wiki_service(request)
    hits = service.search(query=q, limit=limit)
    return {"hits": hits, "query": q}


@router.get("/api/wiki/graph")
async def get_wiki_graph(request: Request):
    service = _get_wiki_service(request)
    return service.get_graph()


@router.get("/api/wiki/mindmap")
async def get_wiki_mindmap(request: Request, include_tags: bool = True, include_taxonomy: bool = True):
    service = _get_wiki_service(request)
    return service.get_mindmap(include_tags=include_tags, include_taxonomy=include_taxonomy)


@router.get("/api/wiki/overview")
async def get_wiki_overview(request: Request):
    service = _get_wiki_service(request)
    return {"overview": service.get_overview()}


@router.get("/api/wiki/stats")
async def get_wiki_stats(request: Request):
    service = _get_wiki_service(request)
    return service.get_stats()
