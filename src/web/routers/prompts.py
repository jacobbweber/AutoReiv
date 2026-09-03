"""
Prompt Catalog REST API Endpoints [CARD-147, REQ-PROMPT-002].
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status

from src.domain.prompts.models import PromptCreate, PromptItem, PromptUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


def _get_store(request: Request) -> Any:
    store = getattr(request.app.state, "store", None)
    if not store:
        raise HTTPException(status_code=500, detail="State store unavailable")
    return store


@router.get("", response_model=List[PromptItem])
async def list_prompts(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search query"),
) -> List[PromptItem]:
    """List prompts in catalog with optional category or search filters."""
    store = _get_store(request)
    return store.list_prompts(category=category, search=search)


@router.get("/{prompt_id}", response_model=PromptItem)
async def get_prompt(request: Request, prompt_id: str) -> PromptItem:
    """Retrieve a single prompt by its ID."""
    store = _get_store(request)
    item = store.get_prompt(prompt_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")
    return item


@router.post("", response_model=PromptItem, status_code=status.HTTP_201_CREATED)
async def create_prompt(request: Request, body: PromptCreate) -> PromptItem:
    """Create a new custom prompt in the catalog."""
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if not body.template_text.strip():
        raise HTTPException(status_code=400, detail="Template text cannot be empty")
    store = _get_store(request)
    return store.create_prompt(body)


@router.put("/{prompt_id}", response_model=PromptItem)
async def update_prompt(request: Request, prompt_id: str, body: PromptUpdate) -> PromptItem:
    """Update an existing custom prompt."""
    store = _get_store(request)
    item = store.update_prompt(prompt_id, body)
    if not item:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found or cannot be updated")
    return item


@router.delete("/{prompt_id}")
async def delete_prompt(request: Request, prompt_id: str):
    """Delete a custom prompt from the catalog (built-in prompts cannot be deleted)."""
    store = _get_store(request)
    item = store.get_prompt(prompt_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found")
    if item.is_builtin:
        raise HTTPException(status_code=400, detail="Built-in platform prompts cannot be deleted")
    success = store.delete_prompt(prompt_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete prompt")
    return {"deleted": True, "id": prompt_id}
