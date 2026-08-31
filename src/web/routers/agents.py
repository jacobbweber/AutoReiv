"""
Agent Management & Delegation Router [REQ-FORGE-003, REQ-FORGE-006, REQ-A2A-006].
"""

import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.domain.kernel.models import AgentTone
from src.domain.orchestration.models import HandoffEnvelope
from src.domain.settings.models import AgentCustomization, ModelPurpose


class AgentProfilePayload(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    system_prompt: str
    purpose: Optional[str] = "general"
    tone: Optional[str] = "default"
    avatar_icon: Optional[str] = "bot"
    model: Optional[str] = "default"
    allowed_tool_names: Optional[List[str]] = None
    allowed_skill: Optional[List[str]] = None
    pack_tool_names: Optional[List[str]] = None
    show_in_chat: Optional[bool] = True
    max_turns: Optional[int] = 10
    history_retention_days: Optional[int] = 30



def _public_agent(profile) -> Dict[str, Any]:
    from src.application.agent_packs.schema import is_visible_in_chat

    show_in_chat = is_visible_in_chat(profile)
    return {
        "id": profile.id,
        "name": profile.name,
        "description": profile.description,
        "system_prompt": profile.system_prompt,
        "purpose": profile.purpose.value if hasattr(profile.purpose, "value") else str(profile.purpose),
        "tone": profile.tone.value if hasattr(profile.tone, "value") else str(profile.tone),
        "avatar_icon": profile.avatar_icon,
        "allowed_tools": profile.allowed_tool_names,
        "allowed_tool_names": profile.allowed_tool_names,
        "allowed_skill": profile.allowed_skill or [],
        "pack_tool_names": profile.pack_tool_names or [],
        "show_in_chat": show_in_chat,
        "max_turns": profile.max_turns,
        "history_retention_days": profile.history_retention_days,
        "model": profile.model,
        "is_builtin": profile.is_builtin,
    }


def _pack_service(request: Request):
    from src.application.agent_packs.service import AgentPackService

    paths = getattr(request.app.state, "data_dir_paths", None)
    if paths is None:
        raise HTTPException(status_code=500, detail="Data directory is not configured.")
    tool_reg = request.app.state.tool_reg
    return AgentPackService(
        data_dir=paths.root,
        agent_registry=request.app.state.registry,
        store=request.app.state.store,
        available_tools={t.name for t in tool_reg.list_tools()},
    )


router = APIRouter(tags=["Agents"])


@router.get("/api/skills/catalog")
async def get_skills_catalog(request: Request):
    from src.application.skills.manifest import TOOL_GROUP_TIERS, get_hierarchical_tool_groups

    tool_reg = request.app.state.tool_reg
    tools_def_list = tool_reg.list_tools()
    tools_list = [{"name": t.name, "description": t.description} for t in tools_def_list]
    skill_packs = get_hierarchical_tool_groups(tools_def_list)

    platform_skills = []
    catalog = getattr(request.app.state, "user_skill_catalog", None)
    if catalog is not None:
        for manifest in catalog.list_manifests():
            platform_skills.append(
                {
                    "id": manifest.id,
                    "name": manifest.name,
                    "description": manifest.description,
                }
            )

    return {
        "tools": tools_list,
        "tiers": [t.model_dump() for t in TOOL_GROUP_TIERS],
        "skill_packs": skill_packs,
        "platform_skills": platform_skills,
        "pack_owned_skills": [],
        "purposes": [p.value for p in ModelPurpose],
        "tones": [t.value for t in AgentTone],
        "avatars": [
            "bot",
            "terminal",
            "shield",
            "shield-alert",
            "book-open",
            "cpu",
            "database",
            "code",
            "check-circle",
            "sparkles",
        ],
    }


@router.get("/api/agents")
async def list_agents(request: Request):
    registry = request.app.state.registry
    profiles = registry.list_agents()
    return [_public_agent(p) for p in profiles]


@router.get("/api/agents/{agent_id}")
async def get_agent_detail(request: Request, agent_id: str):
    registry = request.app.state.registry
    profile = registry.get_agent(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    return _public_agent(profile)


@router.post("/api/agents")
async def create_agent(request: Request, payload: AgentProfilePayload):
    from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError

    registry = request.app.state.registry
    tool_reg = request.app.state.tool_reg

    agent_id = payload.id.strip() if payload.id else re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")
    available_tools = {t.name for t in tool_reg.list_tools()}
    data = payload.model_dump()
    data["id"] = agent_id

    try:
        profile = AgentProfileGuardrail.validate(data, available_tools=available_tools)
    except AgentValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    registry.register_custom_agent(profile)
    return {"status": "created", "agent": profile.model_dump()}


@router.put("/api/agents/{agent_id}")
async def update_agent(request: Request, agent_id: str, payload: AgentProfilePayload):
    from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError

    registry = request.app.state.registry
    tool_reg = request.app.state.tool_reg
    store = request.app.state.store

    existing = registry.get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    available_tools = {t.name for t in tool_reg.list_tools()}
    data = payload.model_dump()
    data["id"] = agent_id
    if not data.get("name"):
        data["name"] = existing.name
    if not data.get("system_prompt"):
        data["system_prompt"] = existing.system_prompt
    if not data.get("purpose"):
        data["purpose"] = existing.purpose.value if hasattr(existing.purpose, "value") else str(existing.purpose)
    if data.get("allowed_tool_names") is None:
        data["allowed_tool_names"] = existing.allowed_tool_names
    if data.get("allowed_skill") is None:
        data["allowed_skill"] = existing.allowed_skill or []
    if data.get("pack_tool_names") is None:
        data["pack_tool_names"] = existing.pack_tool_names or []
    if data.get("show_in_chat") is None:
        data["show_in_chat"] = existing.show_in_chat is not False
    data["is_builtin"] = existing.is_builtin

    try:
        profile = AgentProfileGuardrail.validate(data, available_tools=available_tools)
    except AgentValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if existing.is_builtin:
        customization = AgentCustomization(
            agent_id=agent_id,
            tone=profile.tone.value,
            system_prompt=profile.system_prompt,
            model=profile.model,
            purpose=profile.purpose.value if hasattr(profile.purpose, "value") else str(profile.purpose),
            allowed_tool_names=profile.allowed_tool_names,
            allowed_skill=profile.allowed_skill,
            pack_tool_names=profile.pack_tool_names,
            show_in_chat=profile.show_in_chat,
            max_turns=profile.max_turns,
            history_retention_days=profile.history_retention_days,
        )
        store.save_agent_override(customization)
    else:
        registry.register_custom_agent(profile)

    return {"status": "updated", "agent": profile.model_dump()}


@router.delete("/api/agents/{agent_id}")
async def delete_agent(request: Request, agent_id: str):
    registry = request.app.state.registry
    existing = registry.get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    if existing.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete built-in baseline agent.")

    deleted = registry.delete_custom_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=400, detail=f"Failed to delete agent '{agent_id}'.")
    return {"status": "deleted", "id": agent_id}


@router.post("/api/agents/delegate")
async def delegate_agent_task(request: Request, req: HandoffEnvelope):
    orchestrator = request.app.state.orchestrator
    result = await orchestrator.dispatch_handoff(req)
    return result




@router.get("/api/agents/{agent_id}/pack.zip")
async def export_agent_pack_zip(request: Request, agent_id: str):
    registry = request.app.state.registry
    if not registry.get_agent(agent_id):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    try:
        zip_path = _pack_service(request).export_zip(agent_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return FileResponse(
        path=str(zip_path),
        filename=f"{agent_id}.zip",
        media_type="application/zip",
    )


@router.post("/api/agents/import-pack")
async def import_agent_pack(request: Request, file: UploadFile = File(...)):
    suffix = Path(file.filename or "pack.zip").suffix or ".zip"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_path = Path(tmp.name)
    try:
        tmp.write(await file.read())
        tmp.close()
        profile = _pack_service(request).import_path(tmp_path)
    except (KeyError, ValueError, FileNotFoundError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
    return {"status": "imported", "agent": _public_agent(profile)}

@router.post("/api/agents/{agent_id}/history/prune")
async def prune_agent_history(request: Request, agent_id: str, exclude_session_id: Optional[str] = None):
    registry = request.app.state.registry
    store = request.app.state.store
    profile = registry.get_agent(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    days = profile.history_retention_days if profile.history_retention_days is not None else 30
    deleted = store.prune_expired_sessions(
        agent_id=agent_id,
        max_age_days=days,
        exclude_session_id=exclude_session_id,
    )
    return {"status": "pruned", "agent_id": agent_id, "deleted": deleted, "retention_days": days}

