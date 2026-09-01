"""
Dynamic Tone Registry Router [CARD-131, REQ-TONE-002].
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.domain.kernel.models import ToneDefinition

router = APIRouter(tags=["Tones"])


class ToneCreatePayload(BaseModel):
    id: str = Field(min_length=1, max_length=64, description="Slug identifier for custom tone")
    name: str = Field(min_length=1, max_length=128, description="Display name for tone")
    description: Optional[str] = Field(default="", description="Short description")
    directive: str = Field(min_length=1, description="Prompt directive to inject")


class ToneUpdatePayload(BaseModel):
    name: str = Field(min_length=1, max_length=128, description="Display name for tone")
    description: Optional[str] = Field(default="", description="Short description")
    directive: str = Field(min_length=1, description="Prompt directive to inject")


@router.get("/api/tones", response_model=List[ToneDefinition])
async def list_tones(request: Request):
    store = request.app.state.store
    return store.list_tones()


@router.get("/api/tones/{tone_id}", response_model=ToneDefinition)
async def get_tone(tone_id: str, request: Request):
    store = request.app.state.store
    tone = store.get_tone(tone_id)
    if not tone:
        raise HTTPException(status_code=404, detail=f"Tone '{tone_id}' not found.")
    return tone


@router.post("/api/tones", response_model=ToneDefinition, status_code=status.HTTP_201_CREATED)
async def create_tone(payload: ToneCreatePayload, request: Request):
    store = request.app.state.store
    tone = ToneDefinition(
        id=payload.id.strip().lower(),
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else "",
        directive=payload.directive.strip(),
        is_builtin=False,
    )
    try:
        return store.create_tone(tone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/api/tones/{tone_id}", response_model=ToneDefinition)
async def update_tone(tone_id: str, payload: ToneUpdatePayload, request: Request):
    store = request.app.state.store
    tone = ToneDefinition(
        id=tone_id.strip().lower(),
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else "",
        directive=payload.directive.strip(),
        is_builtin=False,
    )
    try:
        return store.update_tone(tone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api/tones/{tone_id}")
async def delete_tone(tone_id: str, request: Request):
    store = request.app.state.store
    try:
        deleted = store.delete_tone(tone_id)
        return {"status": "success", "deleted": deleted, "tone_id": tone_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
