"""
Agent Management & Delegation Router [REQ-FORGE-003, REQ-FORGE-006, REQ-A2A-006].
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.domain.kernel.models import DEFAULT_AGENT_MAX_TURNS, AgentTone
from src.domain.orchestration.models import HandoffEnvelope
from src.domain.settings.models import MCPServerConfig, ModelPurpose
from src.web.mcp_mount_reconcile import mcp_save_http_body, mount_errors, reconcile_saved_mcp_server

logger = logging.getLogger(__name__)


class AgentProfilePayload(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    system_prompt: str
    provider: Optional[str] = "default"
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    context_window: Optional[int] = None
    purpose: Optional[str] = "general"
    tone: Optional[str] = "default"
    avatar_icon: Optional[str] = "bot"
    model: Optional[str] = "default"
    allowed_skill: Optional[List[str]] = None
    show_in_chat: Optional[bool] = True
    max_turns: Optional[int] = DEFAULT_AGENT_MAX_TURNS
    history_retention_days: Optional[int] = 30
    always_auto_run: Optional[bool] = None  # CARD-573: None keeps the saved value
    storage_enabled: Optional[bool] = False
    storage_type: Optional[str] = "sqlite"
    memory_enabled: Optional[bool] = True
    memory_retention_days: Optional[int] = 30
    pinned_memory: Optional[str] = ""
    allowed_credentials: Optional[List[str]] = None
    mcp_servers: Optional[List[Dict[str, Any]]] = None
    template_folder: Optional[str] = None  # CARD-603: None keeps the saved value, "" clears it
    expected_skills_version: Optional[str] = None  # CARD-539 D10 stale-save check


def _public_agent(
    profile, skill_manifest=None, tools_by_name: Optional[Dict[str, str]] = None, data_dir: Optional[Path] = None,
    registry=None,
) -> Dict[str, Any]:
    from src.application.agent_skills.allowed_tools import resolve_allowed_tools, skills_version
    from src.application.agent_skills.schema import is_platform_skill, is_visible_in_chat
    from src.domain.kernel.models import AgentOrigin
    from src.infrastructure.content.store import get_store

    show_in_chat = is_visible_in_chat(profile)
    content = registry.content if registry is not None else get_store()
    loaded = content.agents.load(profile.id, include_hidden=True)
    file_status = loaded.status() if loaded else {"source": "memory", "shipped": False, "edited": False}

    allowed = resolve_allowed_tools(profile)
    derived_tools = allowed.ordered + allowed.patterns  # wildcard MCP bindings shown as mcp_<server>_*
    if profile.is_builtin or profile.id == "agent-builder":
        origin_val = AgentOrigin.SYSTEM.value
    else:
        origin_val = AgentOrigin.FILE.value

    return {
        "id": profile.id,
        "name": profile.name,
        "description": profile.description,
        "system_prompt": profile.system_prompt,
        "origin": origin_val,
        "provider": getattr(profile, "provider", "default") or "default",
        "api_base_url": getattr(profile, "api_base_url", None),
        "api_key": getattr(profile, "api_key", None),
        "context_window": getattr(profile, "context_window", None),
        "purpose": (profile.purpose.value if hasattr(profile.purpose, "value") else str(profile.purpose))
        if profile.purpose
        else "general",
        "tone": profile.tone.value if hasattr(profile.tone, "value") else str(profile.tone),
        "avatar_icon": profile.avatar_icon,
        # CARD-539: tools are derived from ticked skills (read-only); skills_version guards stale saves.
        "allowed_tools": list(derived_tools),
        "allowed_skill": profile.allowed_skill or [],
        "skills_version": skills_version(profile),
        "own_skills": [],
        "file_status": file_status,  # CARD-570: shipped / edited / shipped_changed
        "skill_tool_warnings": {
            sid: names
            for sid, names in (getattr(registry, "skill_tool_warnings", None) or {}).items()
            if sid in (profile.allowed_skill or [])
        },
        "show_in_chat": show_in_chat,
        "visibility": getattr(profile, "visibility", None) or ("internal" if not show_in_chat else "public"),
        "fleet": getattr(profile, "fleet", None),
        "max_turns": profile.max_turns,
        "history_retention_days": profile.history_retention_days,
        "always_auto_run": bool(getattr(profile, "always_auto_run", False)),
        "storage_enabled": getattr(profile, "storage_enabled", False),
        "storage_type": getattr(profile, "storage_type", "sqlite") or "sqlite",
        "memory_enabled": getattr(profile, "memory_enabled", True),
        "memory_retention_days": getattr(profile, "memory_retention_days", 30),
        "pinned_memory": getattr(profile, "pinned_memory", "") or "",
        "model": profile.model,
        "is_builtin": profile.is_builtin,
        "is_platform_skill": is_platform_skill(profile.id),
        "allowed_credentials": getattr(profile, "allowed_credentials", []) or [],
        "mcp_servers": [
            s.model_dump() if hasattr(s, "model_dump") else s for s in (getattr(profile, "mcp_servers", None) or [])
        ],
        "template_folder": getattr(profile, "template_folder", None) or "",
    }


router = APIRouter(tags=["Agents"])


def _tools_by_name(request: Request) -> Dict[str, str]:
    tool_reg = request.app.state.tool_reg
    return {t.name: t.description for t in tool_reg.list_tools()}


def _data_dir_root(request: Request) -> Optional[Path]:
    paths = getattr(request.app.state, "data_dir_paths", None) or getattr(request.app.state, "data_paths", None)
    if paths is not None:
        raw = getattr(paths, "root", None) or getattr(paths, "data_dir", None) or paths
        return Path(raw)
    from src.infrastructure.data.resolver import DataDirResolver

    try:
        resolved = DataDirResolver().resolve()
        return Path(getattr(resolved, "root", None) or getattr(resolved, "data_dir", None) or resolved)
    except Exception:
        return None


@router.get("/api/skills/catalog")
async def get_skills_catalog(request: Request):
    from src.application.agent_skills.allowed_tools import skill_tools
    from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS
    from src.application.skills.manifest import TOOL_GROUP_TIERS, get_hierarchical_tool_groups
    from src.application.skills.workshop import operator_store_skills

    tool_reg = request.app.state.tool_reg
    tools_def_list = tool_reg.list_tools()
    tools_by_name = {t.name: t.description for t in tools_def_list}
    tools_list = [{"name": t.name, "description": t.description} for t in tools_def_list]
    skill_rows = get_hierarchical_tool_groups(tools_def_list)

    data_dir = _data_dir_root(request)
    fleet_skills: dict[str, list[dict[str, Any]]] = {}
    seen: set = set()
    platform_skills = []

    def _skill_tools(skill_id: str):
        names = skill_tools([skill_id]).get(skill_id, [])
        return [
            {
                "name": name,
                "description": tools_by_name.get(name, ""),
                "tier": "required_platform" if name in REQUIRED_PLATFORM_TOOLS else "optional_platform",
            }
            for name in names
            if name in tools_by_name
        ]

    from src.infrastructure.content.store import get_store

    for item in get_store().skills.list():
        if not item.shipped:
            continue  # user-created skills are listed under operator_skills
        tools = _skill_tools(item.id)
        platform_skills.append(
            {
                "id": item.id,
                "name": str(item.meta.get("name") or item.id),
                "description": str(item.meta.get("description") or ""),
                "has_required_tools": any(t.get("tier") == "required_platform" for t in tools),
                "tools": tools,
                "status": item.status(),
            }
        )
        seen.add(item.id)

    baseline_tools = [
        {
            "name": name,
            "description": tools_by_name.get(name, ""),
            "tier": "required_platform",
        }
        for name in REQUIRED_PLATFORM_TOOLS
        if name in tools_by_name
    ]

    store = getattr(request.app.state, "store", None)
    operator_skills = operator_store_skills(data_dir) if data_dir is not None else []
    return {
        "tools": tools_list,
        "tiers": [t.model_dump() for t in TOOL_GROUP_TIERS],
        "skill_rows": skill_rows,
        "baseline_tools": baseline_tools,
        "platform_skills": platform_skills,
        "operator_skills": operator_skills,
        "fleet_skills": fleet_skills,
        "owned_skills": [],
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
    return [_public_agent(p, None, tools_by_name, data_dir, registry) for p in profiles]


@router.get("/api/agents/{agent_id}")
async def get_agent_detail(request: Request, agent_id: str):
    registry = request.app.state.registry
    profile = registry.get_agent(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    data_dir = _data_dir_root(request)
    return _public_agent(profile, None, _tools_by_name(request), data_dir, registry)


@router.post("/api/agents")
async def create_agent(request: Request, payload: AgentProfilePayload):
    from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError

    registry = request.app.state.registry
    tool_reg = request.app.state.tool_reg

    agent_id = payload.id.strip() if payload.id else re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")
    available_tools = {t.name for t in tool_reg.list_tools()}
    data = payload.model_dump(exclude={"expected_skills_version"})
    data["id"] = agent_id
    data["origin"] = "custom"

    try:
        profile = AgentProfileGuardrail.validate(data, available_tools=available_tools)
    except AgentValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    from src.infrastructure.content.store import InvalidIdError, ReservedIdError

    try:
        profile = registry.save_agent(profile, create=True)  # CARD-570: shipped ids are reserved
    except ReservedIdError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except InvalidIdError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if profile.storage_enabled:
        from src.infrastructure.data.resolver import get_agent_storage_connection

        data_dir = _data_dir_root(request)
        try:
            conn = get_agent_storage_connection(profile.id, data_dir=data_dir)
            conn.close()
        except Exception:
            pass
    if profile.memory_enabled:
        from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

        data_dir = _data_dir_root(request)
        try:
            repo = AgentMemoryRepository(agent_id=profile.id, data_dir=data_dir)
            repo.initialize_schema()
            if profile.pinned_memory:
                repo.add_pinned_memory(profile.pinned_memory)
        except Exception:
            pass
    return {"status": "created", "agent": _public_agent(profile, tools_by_name=_tools_by_name(request))}


@router.put("/api/agents/{agent_id}")
async def update_agent(request: Request, agent_id: str, payload: AgentProfilePayload):
    from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError

    registry = request.app.state.registry
    tool_reg = request.app.state.tool_reg
    store = request.app.state.store

    existing = registry.get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    from src.application.agent_skills.allowed_tools import skills_version

    expected = (payload.expected_skills_version or "").strip()
    if expected and expected != skills_version(existing):
        raise HTTPException(
            status_code=409,
            detail="This agent's skills changed since this page loaded (for example an accepted proposal). "
            "Reload Agent Studio and save again.",
        )

    available_tools = {t.name for t in tool_reg.list_tools()}
    data = payload.model_dump(exclude={"expected_skills_version"})
    data["id"] = agent_id
    if not data.get("name"):
        data["name"] = existing.name
    if not data.get("system_prompt"):
        data["system_prompt"] = existing.system_prompt
    if not data.get("purpose"):
        data["purpose"] = existing.purpose.value if hasattr(existing.purpose, "value") else str(existing.purpose)
    if data.get("allowed_skill") is None:
        data["allowed_skill"] = existing.allowed_skill or []
    if data.get("show_in_chat") is None:
        data["show_in_chat"] = existing.show_in_chat is not False
    if data.get("always_auto_run") is None:
        data["always_auto_run"] = bool(getattr(existing, "always_auto_run", False))
    data.pop("allow_wiki_access", None)  # CARD-540: retired field, ignored if an old client sends it
    if data.get("allowed_credentials") is None:
        data["allowed_credentials"] = getattr(existing, "allowed_credentials", []) or []
    if data.get("mcp_servers") is None:
        data["mcp_servers"] = getattr(existing, "mcp_servers", []) or []
    if data.get("template_folder") is None:
        data["template_folder"] = getattr(existing, "template_folder", None)
    data["is_builtin"] = existing.is_builtin

    try:
        profile = AgentProfileGuardrail.validate(data, available_tools=available_tools)
    except AgentValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # CARD-502: one save path shared with Teach > Adopt
    from src.application.agent_skills.skill_list import persist_agent_profile

    persist_agent_profile(store, registry, existing, profile, agent_id=agent_id, data_dir=_data_dir_root(request))

    if profile.storage_enabled:
        from src.infrastructure.data.resolver import get_agent_storage_connection

        data_dir = _data_dir_root(request)
        try:
            conn = get_agent_storage_connection(profile.id, data_dir=data_dir)
            conn.close()
        except Exception:
            pass
    if profile.memory_enabled:
        from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

        data_dir = _data_dir_root(request)
        try:
            repo = AgentMemoryRepository(agent_id=profile.id, data_dir=data_dir)
            repo.initialize_schema()
            if profile.pinned_memory:
                repo.add_pinned_memory(profile.pinned_memory)
        except Exception:
            pass

    # Dormant auto-training fields are not part of the API [CARD-497 D9].
    body = profile.model_dump(exclude={"allow_autonomous_training", "max_training_retries"})
    body["skills_version"] = skills_version(profile)
    return {"status": "updated", "agent": body}


@router.delete("/api/agents/{agent_id}")
async def delete_agent(request: Request, agent_id: str, purge_history: bool = False):
    registry = request.app.state.registry
    existing = registry.get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    if agent_id in ("agent-builder", "autoreiv"):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete core system agent.",
        )
    # CARD-570: a shipped agent is hidden (persisted); a user-created agent's file is removed.
    shipped = registry.content.agents.shipped_path(agent_id).is_file()
    deleted = registry.delete_custom_agent(agent_id, purge_history=purge_history)
    if not deleted:
        raise HTTPException(status_code=400, detail=f"Failed to delete agent '{agent_id}'.")
    return {"status": "hidden" if shipped else "deleted", "id": agent_id, "purged": purge_history}


@router.post("/api/agents/delegate")
async def delegate_agent_task(request: Request, req: HandoffEnvelope):
    orchestrator = request.app.state.orchestrator
    result = await orchestrator.dispatch_handoff(req)
    return result


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


@router.get("/api/agents/{agent_id}/memory")
async def get_agent_memory(
    request: Request,
    agent_id: str,
    query: Optional[str] = None,
):
    registry = request.app.state.registry
    profile = registry.get_agent(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

    data_dir = _data_dir_root(request)
    repo = AgentMemoryRepository(agent_id=agent_id, data_dir=data_dir)
    repo.initialize_schema()

    pinned = repo.list_pinned_memories()
    summaries = repo.list_session_summaries(limit=10)
    if query and query.strip():
        facts = repo.search_facts(query.strip(), limit=50)
    else:
        facts = repo.list_semantic_facts(active_only=True, limit=50)

    enriched_facts = []
    for f in facts:
        item = dict(f)
        item["fact_text"] = f"{item.get('entity', '')}.{item.get('attribute', '')}: {item.get('value', '')}"
        enriched_facts.append(item)

    enriched_summaries = []
    for s in summaries:
        item = dict(s)
        item["summary_text"] = item.get("summary", "")
        enriched_summaries.append(item)

    return {
        "status": "ok",
        "agent_id": agent_id,
        "memory_enabled": getattr(profile, "memory_enabled", True),
        "retention_days": getattr(profile, "memory_retention_days", 30),
        "pinned_memory": getattr(profile, "pinned_memory", ""),
        "pinned": pinned,
        "summaries": enriched_summaries,
        "session_summaries": enriched_summaries,
        "facts": enriched_facts,
        "semantic_facts": enriched_facts,
    }


@router.delete("/api/agents/{agent_id}/memory/facts/{fact_id}")
async def delete_agent_memory_fact(
    request: Request,
    agent_id: str,
    fact_id: str,
):
    registry = request.app.state.registry
    profile = registry.get_agent(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

    data_dir = _data_dir_root(request)
    repo = AgentMemoryRepository(agent_id=agent_id, data_dir=data_dir)
    repo.initialize_schema()
    success = repo.delete_semantic_fact(fact_id=fact_id, permanent=True)
    return {"status": "ok", "deleted_fact_id": fact_id, "success": success}


@router.delete("/api/agents/{agent_id}/memory")
@router.post("/api/agents/{agent_id}/memory/purge")
async def purge_agent_memory(
    request: Request,
    agent_id: str,
):
    registry = request.app.state.registry
    profile = registry.get_agent(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

    data_dir = _data_dir_root(request)
    repo = AgentMemoryRepository(agent_id=agent_id, data_dir=data_dir)
    repo.initialize_schema()
    repo.purge_all()
    return {"status": "ok", "agent_id": agent_id, "purged": True}


@router.get("/api/agents/{agent_id}/mcp")
async def list_agent_mcp_servers(request: Request, agent_id: str):
    """List configured MCP servers for this agent with live mounted status [REQ-MCP-AGENT-003]."""
    registry = request.app.state.registry
    profile = registry.get_agent(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    mcp_manager = getattr(request.app.state, "mcp_manager", None)
    active_map = mcp_manager.get_mounted_servers() if mcp_manager else {}
    errors = mount_errors(mcp_manager)

    servers = [s.model_dump() if hasattr(s, "model_dump") else s for s in getattr(profile, "mcp_servers", []) or []]
    result = []
    for s in servers:
        name = s.get("name")
        active_info = (
            active_map.get(name)
        )
        result.append(
            {
                **s,
                "is_mounted": active_info is not None,
                "tool_count": active_info.get("tool_count", 0) if active_info else 0,
                "tools": active_info.get("tools", []) if active_info else [],
                "last_error": None if active_info else errors.get(name),  # CARD-516
            }
        )
    return result


@router.post("/api/agents/{agent_id}/mcp")
async def save_agent_mcp_server(request: Request, agent_id: str, req: MCPServerConfig):
    """Save an agent MCP server. Mount when enabled, unmount when disabled [REQ-MCP-AGENT-003, CARD-424]."""
    registry = request.app.state.registry
    profile = registry.get_agent(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    existing_servers = [
        s.model_dump() if hasattr(s, "model_dump") else s for s in getattr(profile, "mcp_servers", []) or []
    ]
    idx = next((i for i, s in enumerate(existing_servers) if s.get("name") == req.name), None)
    req_dict = req.model_dump()
    if idx is not None:
        existing_servers[idx] = req_dict
    else:
        existing_servers.append(req_dict)

    profile.mcp_servers = [MCPServerConfig.model_validate(s) for s in existing_servers]
    registry.save_agent(profile)  # CARD-570: full user copy of the agent file

    mcp_manager = getattr(request.app.state, "mcp_manager", None)
    outcome = await reconcile_saved_mcp_server(mcp_manager, req)
    return mcp_save_http_body(
        req.name,
        outcome,
        mount_error="Configuration saved, but mounting failed",
    )


@router.delete("/api/agents/{agent_id}/mcp/{server_name}")
async def delete_agent_mcp_server(request: Request, agent_id: str, server_name: str):
    """Remove an MCP server from an agent profile and unmount it [REQ-MCP-AGENT-003]."""
    registry = request.app.state.registry
    profile = registry.get_agent(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    existing_servers = [
        s.model_dump() if hasattr(s, "model_dump") else s for s in getattr(profile, "mcp_servers", []) or []
    ]
    filtered = [s for s in existing_servers if s.get("name") != server_name]
    profile.mcp_servers = [MCPServerConfig.model_validate(s) for s in filtered]

    registry.save_agent(profile)  # CARD-570: full user copy of the agent file

    mcp_manager = getattr(request.app.state, "mcp_manager", None)
    if mcp_manager:
        await mcp_manager.unmount_server(server_name)

    return {"status": "deleted", "name": server_name}


@router.post("/api/agents/{agent_id}/mcp/{server_name}/mount")
async def mount_agent_mcp_server(request: Request, agent_id: str, server_name: str):
    """Mount or re-mount an already configured MCP server for an agent [REQ-MCP-AGENT-003]."""
    registry = request.app.state.registry
    profile = registry.get_agent(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    servers = [s.model_dump() if hasattr(s, "model_dump") else s for s in getattr(profile, "mcp_servers", []) or []]
    target_server = next((s for s in servers if s.get("name") == server_name), None)
    if not target_server:
        raise HTTPException(status_code=404, detail=f"MCP server '{server_name}' not found for agent '{agent_id}'.")

    mcp_manager = getattr(request.app.state, "mcp_manager", None)
    if not mcp_manager:
        raise HTTPException(status_code=500, detail="MCP manager not initialized.")

    try:
        tools = await mcp_manager.mount_server(
            name=target_server["name"],
            command=target_server.get("command"),
            env=target_server.get("env"),
            transport=target_server.get("transport", "sse"),
            url=target_server.get("url"),
            headers=target_server.get("headers"),
        )
        return {
            "status": "mounted",
            "server_name": server_name,
            "tools_count": len(tools),
            "tools": [t.name for t in tools],
        }
    except Exception as exc:
        return {
            "status": "error",
            "server_name": server_name,
            "error": f"Failed to mount: {exc}",
        }


@router.post("/api/agents/{agent_id}/mcp/test")
async def test_agent_mcp_server(request: Request, agent_id: str, req: MCPServerConfig):
    """Test connection to an MCP server without persisting [REQ-MCP-AGENT-003]."""
    import time

    from src.infrastructure.mcp.client_adapter import MCPClientAdapter, MCPMountError, adapter_start_error

    start_time = time.perf_counter()
    adapter = MCPClientAdapter(
        server_name=req.name or "test-probe",
        command=req.command,
        env=req.env,
        transport=req.transport,
        url=req.url,
        headers=req.headers,
        timeout_seconds=10.0,
    )
    try:
        tools = await adapter.list_tools()
        start_error = adapter_start_error(adapter)
        if start_error:
            raise MCPMountError(start_error)  # CARD-516: not "ok, 0 tools"
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "status": "ok",
            "server_name": req.name,
            "transport": req.transport,
            "latency_ms": round(latency_ms, 2),
            "tools_count": len(tools),
            "tools": [t.name for t in tools],
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "status": "error",
            "server_name": req.name,
            "latency_ms": round(latency_ms, 2),
            "error": str(exc),
        }


# --- CARD-570: agent files (user copy wins; Use shipped version; hide) ---


@router.post("/api/agents/{agent_id}/use-shipped")
async def use_shipped_version(request: Request, agent_id: str):
    """Delete the user copy of a shipped agent. Model/provider settings are kept."""
    registry = request.app.state.registry
    if not registry.content.agents.shipped_path(agent_id).is_file():
        raise HTTPException(status_code=400, detail=f"'{agent_id}' is not a shipped agent.")
    removed = registry.use_shipped_version(agent_id)
    profile = registry.get_agent(agent_id)
    return {
        "agent_id": agent_id,
        "removed_copy": removed,
        "agent": _public_agent(profile, tools_by_name=_tools_by_name(request)) if profile else None,
    }


@router.post("/api/agents/{agent_id}/unhide")
async def unhide_agent(request: Request, agent_id: str):
    registry = request.app.state.registry
    if not registry.unhide_agent(agent_id):
        raise HTTPException(status_code=404, detail=f"'{agent_id}' is not hidden.")
    return {"agent_id": agent_id, "hidden": False}


@router.get("/api/agents-hidden")
async def list_hidden_agents(request: Request):
    registry = request.app.state.registry
    return {"hidden": sorted(registry.content.agents.hidden())}
