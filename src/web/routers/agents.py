"""
Agent Management & Delegation Router [REQ-FORGE-003, REQ-FORGE-006, REQ-A2A-006].
"""

import json
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



def _load_pack_manifest(data_dir, agent_id: str):
    from src.application.agent_packs.schema import AgentPackManifest

    if data_dir is None or not agent_id:
        return None
    path = Path(data_dir) / "packs" / agent_id / "pack.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    try:
        return AgentPackManifest.model_validate(raw)
    except Exception:
        return None


def _pack_skills_payload(manifest, tools_by_name: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    tools_by_name = tools_by_name or {}
    pack_skills = []
    nested: List[str] = []
    if manifest is None:
        return {"pack_skills": [], "ungrouped_pack_tools": []}
    for skill in manifest.skills:
        skill_tools = []
        for name in skill.tools:
            if name not in nested:
                nested.append(name)
            skill_tools.append(
                {
                    "name": name,
                    "description": tools_by_name.get(name, ""),
                }
            )
        pack_skills.append(
            {
                "id": skill.id,
                "name": skill.name or skill.id,
                "description": skill.description or "",
                "tools": skill_tools,
            }
        )
    return {"pack_skills": pack_skills, "ungrouped_pack_tools": []}


def _public_agent(profile, pack_manifest=None, tools_by_name: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    from src.application.agent_packs.schema import is_platform_pack, is_visible_in_chat

    show_in_chat = is_visible_in_chat(profile)
    pack_bits = _pack_skills_payload(pack_manifest, tools_by_name)
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
        "pack_skills": pack_bits["pack_skills"],
        "ungrouped_pack_tools": pack_bits["ungrouped_pack_tools"],
        "show_in_chat": show_in_chat,
        "max_turns": profile.max_turns,
        "history_retention_days": profile.history_retention_days,
        "model": profile.model,
        "is_builtin": profile.is_builtin,
        "is_platform_pack": is_platform_pack(profile.id),
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


def _tools_by_name(request: Request) -> Dict[str, str]:
    tool_reg = request.app.state.tool_reg
    return {t.name: t.description for t in tool_reg.list_tools()}


def _data_dir_root(request: Request) -> Optional[Path]:
    paths = getattr(request.app.state, "data_dir_paths", None)
    if paths is None:
        return None
    return Path(paths.root)


def _pack_owned_skill_ids(data_dir: Optional[Path]) -> set:
    from src.application.agent_packs.schema import AgentPackManifest

    ids: set = set()
    if data_dir is None:
        return ids
    packs = data_dir / "packs"
    if not packs.is_dir():
        return ids
    for pack_dir in packs.iterdir():
        pack_json = pack_dir / "pack.json"
        if not pack_json.is_file():
            continue
        try:
            raw = json.loads(pack_json.read_text(encoding="utf-8"))
            manifest = AgentPackManifest.model_validate(raw)
        except Exception:
            continue
        for skill in manifest.skills:
            if skill.id:
                ids.add(skill.id)
    return ids


@router.get("/api/skills/catalog")
async def get_skills_catalog(request: Request):
    from src.application.agent_packs.schema import (
        PLATFORM_SKILL_IDS,
        PLATFORM_SKILL_METADATA,
        PLATFORM_SKILL_TOOLS,
    )
    from src.application.skills.manifest import TOOL_GROUP_TIERS, get_hierarchical_tool_groups

    tool_reg = request.app.state.tool_reg
    tools_def_list = tool_reg.list_tools()
    tools_by_name = {t.name: t.description for t in tools_def_list}
    tools_list = [{"name": t.name, "description": t.description} for t in tools_def_list]
    skill_packs = get_hierarchical_tool_groups(tools_def_list)

    data_dir = _data_dir_root(request)
    pack_owned = _pack_owned_skill_ids(data_dir)
    seen: set = set()
    platform_skills = []

    def _skill_tools(skill_id: str):
        names = PLATFORM_SKILL_TOOLS.get(skill_id, ())
        return [
            {"name": name, "description": tools_by_name.get(name, "")}
            for name in names
            if name in tools_by_name
        ]

    for sid in PLATFORM_SKILL_IDS:
        if sid in pack_owned:
            continue
        meta = PLATFORM_SKILL_METADATA.get(sid, {})
        name = meta.get("name", sid.replace("-", " ").title())
        desc = meta.get("description", "")
        platform_skills.append(
            {
                "id": sid,
                "name": name,
                "description": desc,
                "tools": _skill_tools(sid),
            }
        )
        seen.add(sid)

    catalog = getattr(request.app.state, "user_skill_catalog", None)
    if catalog is not None:
        for manifest in catalog.list_manifests():
            if manifest.id in pack_owned or manifest.id in seen:
                continue
            platform_skills.append(
                {
                    "id": manifest.id,
                    "name": manifest.name,
                    "description": manifest.description,
                    "tools": _skill_tools(manifest.id),
                }
            )
            seen.add(manifest.id)

    store = getattr(request.app.state, "store", None)
    return {
        "tools": tools_list,
        "tiers": [t.model_dump() for t in TOOL_GROUP_TIERS],
        "skill_packs": skill_packs,
        "platform_skills": platform_skills,
        "pack_owned_skills": sorted(pack_owned),
        "purposes": [p.value for p in ModelPurpose],
        "tones": (
            [t.id for t in store.list_tones()]
            if store and hasattr(store, "list_tones")
            else [t.value for t in AgentTone]
        ),
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
    data_dir = _data_dir_root(request)
    tools_by_name = _tools_by_name(request)
    return [
        _public_agent(p, _load_pack_manifest(data_dir, p.id), tools_by_name)
        for p in profiles
    ]


@router.get("/api/agents/{agent_id}")
async def get_agent_detail(request: Request, agent_id: str):
    registry = request.app.state.registry
    profile = registry.get_agent(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    return _public_agent(
        profile,
        _load_pack_manifest(_data_dir_root(request), profile.id),
        _tools_by_name(request),
    )


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
            tone=profile.tone.value if hasattr(profile.tone, "value") else str(profile.tone),
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
async def delete_agent(request: Request, agent_id: str, purge_history: bool = False):
    registry = request.app.state.registry
    existing = registry.get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    from src.application.agent_packs.schema import is_platform_pack

    if existing.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete built-in baseline agent.")
    if is_platform_pack(agent_id):
        raise HTTPException(status_code=400, detail="Cannot delete a Platform Agent Pack.")

    deleted = registry.delete_custom_agent(agent_id, purge_history=purge_history)
    if not deleted:
        raise HTTPException(status_code=400, detail=f"Failed to delete agent '{agent_id}'.")
    return {"status": "deleted", "id": agent_id, "purged": purge_history}


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


class DashboardActionRequest(BaseModel):
    tool: str
    args: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


@router.get("/api/agent-packs/dashboards")
async def list_agent_pack_dashboards(request: Request):
    """List all available dynamic studio dashboards from installed packs."""
    svc = _pack_service(request)
    dashboards = svc.list_dashboards()
    return [d.model_dump(mode="json") for d in dashboards]


@router.get("/api/agent-packs/{pack_id}/dashboard")
async def get_agent_pack_dashboard(request: Request, pack_id: str):
    """Get dashboard for a specific agent pack."""
    svc = _pack_service(request)
    dash = svc.get_dashboard(pack_id)
    if dash is None:
        raise HTTPException(status_code=404, detail=f"No dashboard found for pack '{pack_id}'.")
    return dash.model_dump(mode="json")


@router.post("/api/agent-packs/{pack_id}/dashboard")
async def save_agent_pack_dashboard(request: Request, pack_id: str, payload: Dict[str, Any]):
    """Create or update dashboard for an agent pack."""
    from src.application.agent_packs.schema import AgentDashboardManifest

    try:
        manifest = AgentDashboardManifest.model_validate({**payload, "pack_id": pack_id})
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    svc = _pack_service(request)
    saved = svc.save_dashboard(pack_id, manifest)
    return saved.model_dump(mode="json")


@router.post("/api/agent-packs/{pack_id}/action")
async def execute_dashboard_action(request: Request, pack_id: str, action_req: DashboardActionRequest):
    """Execute a declared dashboard action tool for the pack's agent."""
    import uuid

    from src.domain.gateway.models import ToolCall

    registry = request.app.state.registry
    tool_reg = request.app.state.tool_reg
    agent = registry.get_agent(pack_id)
    if not agent:
        agent = registry.get_agent("assistant") or registry.get_agent("autoreiv")

    call = ToolCall(
        id=f"dash_{uuid.uuid4().hex[:8]}",
        name=action_req.tool,
        arguments=action_req.args or {},
    )
    result = await tool_reg.execute(call, agent=agent, session_id=action_req.session_id)
    return {
        "success": result.success,
        "tool_name": result.tool_name,
        "output": result.output,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


