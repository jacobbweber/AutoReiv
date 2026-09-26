"""Skill Studio and Tools Studio routes [CARD-497 D1, D4; ADR-0060].

Moved out of the retired Agent Training Factory router with identical payloads:
``GET /api/tools_studio/capabilities``, ``POST /api/skill_studio/runbook``,
``POST /api/skill_studio/save``, ``GET /api/skill_studio/skills`` and
``GET /api/skill_studio/skills/{id}``. The five old ``/api/agent_training_factory/*``
paths answer 308 to these for one release (CARD-498 removes the redirects).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["Skill Studio"])
legacy_router = APIRouter(prefix="/api/agent_training_factory", include_in_schema=False)


class ScaffoldRunbookRequest(BaseModel):
    agent_id: Optional[str] = None
    skill_id: str
    skill_name: str
    trigger_description: str
    intent_notes: Optional[str] = None
    selected_tools: List[str] = Field(default_factory=list)
    source_context: Optional[str] = None


class SaveScaffoldRequest(BaseModel):
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    role_persona: Optional[str] = None
    model: Optional[str] = None
    skill_id: str
    skill_content: str
    auto_pin: bool = True
    name: Optional[str] = None
    description: Optional[str] = None
    tier: Optional[str] = None
    safety: Optional[Dict[str, Any]] = None
    requires_tools: Optional[List[str]] = None


@router.get("/api/tools_studio/capabilities")
async def get_tools_studio_capabilities(request: Request) -> Dict[str, Any]:
    """List registered tools grouped by namespace/server for live capability inspection."""
    tool_registry = getattr(request.app.state, "tool_registry", None) or getattr(request.app.state, "tool_reg", None)
    tools = tool_registry.list_tools() if tool_registry else []

    from src.application.tools.native_packaging import catalog_origin_label, load_native_tool_names
    from src.infrastructure.agents.legacy_pack_tools import LEGACY_PACK_TOOL_ORIGIN

    store = getattr(request.app.state, "store", None)
    native_names = load_native_tool_names(store)
    namespaces: Dict[str, Dict[str, Any]] = {}

    for tool in tools:
        t_name = tool.name
        t_desc = tool.description or ""
        t_params = tool.parameters or {}
        server_name = ""
        tool_origin = ""
        if tool_registry is not None and hasattr(tool_registry, "get_tool_origin"):
            tool_origin = tool_registry.get_tool_origin(t_name)

        if t_name in native_names:
            ns_id = "native_custom"
            ns_name = "Native custom"
            ns_source = "native_custom"
        elif t_name.startswith("mcp_"):
            parts = t_name.split("_")
            server_key = parts[1] if len(parts) > 1 else "generic"
            server_name = server_key
            ns_id = f"mcp:{server_key}"
            ns_name = f"MCP: {server_key.title()}"
            ns_source = "mcp"
        elif tool_origin == LEGACY_PACK_TOOL_ORIGIN:
            ns_id = "legacy_pack_tool"
            ns_name = "Legacy pack tool"
            ns_source = "legacy_pack_tool"
        else:
            # Shipped callables are one Platform group. Do not split Dynamic or Built-in Primitives [CARD-429].
            ns_id = "platform"
            ns_name = "Platform"
            ns_source = "platform"

        origin_source = "platform" if ns_source == "platform" else ns_source
        if ns_id not in namespaces:
            namespaces[ns_id] = {
                "id": ns_id,
                "name": ns_name,
                "source": ns_source,
                "server_name": server_name,
                "origin_label": catalog_origin_label(origin_source, server_name),
                "tools": [],
            }
        namespaces[ns_id]["tools"].append({
            "name": t_name,
            "description": t_desc,
            "parameters": t_params,
            "is_high_risk": getattr(tool, "is_high_risk", False),
            "origin": origin_source,
            "origin_label": catalog_origin_label(origin_source, server_name),
        })

    return {
        "total_tools": len(tools),
        "namespaces": list(namespaces.values()),
    }


@router.post("/api/skill_studio/runbook")
async def scaffold_skill_runbook(req: ScaffoldRunbookRequest, request: Request) -> Dict[str, Any]:
    """Generate a Matt Pocock compliant SKILL.md runbook grounded in tools and source context."""
    tool_registry = getattr(request.app.state, "tool_registry", None) or getattr(request.app.state, "tool_reg", None)
    tool_definitions = []
    if tool_registry and req.selected_tools:
        for t_name in req.selected_tools:
            defn = tool_registry.get_tool_definition(t_name)
            if defn:
                tool_definitions.append({
                    "name": defn.name,
                    "description": defn.description,
                    "parameters": defn.parameters,
                })

    system_prompt = (
        "You are the AutoReiv Principal Skill Architect. You write production-grade, standard Matt Pocock compliant "
        "SKILL.md runbooks for AI agents.\n"
        "A skill runbook is a procedural SOP (playbook) that teaches an agent:\n"
        "1. When to use this skill (trigger description strictly <= 60 characters).\n"
        "2. The ordered, step-by-step workflow.\n"
        "3. How to use and sequence the required tools (with exact parameters and expected payloads).\n"
        "4. Edge cases, failure modes, and recovery steps.\n"
        "5. Definition of Done and verification checklist.\n\n"
        "You MUST format the runbook with valid YAML frontmatter at the very top:\n"
        "---\n"
        "name: <Skill Name>\n"
        "description: <Trigger description, strictly <= 60 chars>\n"
        "requires_tools:\n"
        "  - <tool_name>\n"
        "---\n"
        "Followed by clear markdown sections:\n"
        "# <Skill Name>\n\n"
        "## Overview & Trigger\n\n"
        "## Prerequisites & Tool Schemas\n\n"
        "## Step-by-Step Procedure\n\n"
        "## Edge Cases & Pitfalls\n\n"
        "## Definition of Done\n\n"
        "CRITICAL: Do NOT write Python classes or synthetic executable code. A skill is a markdown runbook."
    )

    clean_trigger = (req.trigger_description or "").strip()[:60]
    tools_summary = json.dumps(tool_definitions, indent=2) if tool_definitions else "None (Pure knowledge / runbook)"

    user_prompt = (
        f"Skill ID: {req.skill_id}\n"
        f"Skill Name: {req.skill_name}\n"
        f"Trigger Description: {clean_trigger}\n"
        f"Target Agent ID: {req.agent_id or 'general'}\n\n"
        f"Operator Intent & Procedure Notes:\n{req.intent_notes or 'Follow standard best practices.'}\n\n"
        f"Available/Selected Tools:\n{tools_summary}\n\n"
        f"External Source Context / Documentation:\n{req.source_context or 'None provided.'}\n\n"
        "Please generate the complete, production-ready SKILL.md file."
    )

    gateway = getattr(request.app.state, "gateway", None)
    from src.application.skills.studio_llm import phase_llm_text

    if req.selected_tools:
        tools_list = "\n".join(f"  - {t}" for t in req.selected_tools)
        fallback_tools_yaml = f"requires_tools:\n{tools_list}"
    else:
        fallback_tools_yaml = "requires_tools: []"

    tools_line = ", ".join(req.selected_tools) if req.selected_tools else "None (Pure procedural skill)"
    fallback_runbook = f"""---
name: {req.skill_name}
description: {clean_trigger}
{fallback_tools_yaml}
---

# {req.skill_name}

## Overview & Trigger
{clean_trigger}

## Prerequisites & Tools
- Required tools: {tools_line}

## Step-by-Step Procedure
1. Initialize task context based on operator intent: {req.intent_notes or 'Execute procedure.'}
2. Validate required arguments and parameters before invoking tools.
3. Execute sequential tool operations and record intermediate outcomes.
4. Verify results against operator expectations.

## Edge Cases & Pitfalls
- Verify all tool inputs conform to parameter schemas.
- If a tool fails, capture error message and inspect diagnostics before retrying.

## Definition of Done
- Task objectives completed with observable success criteria.
- Clean status reported back to caller.
"""

    generated = await phase_llm_text(
        gateway,
        system=system_prompt,
        user=user_prompt,
        fallback=fallback_runbook,
        timeout=60.0,
    )

    if not generated or not generated.strip().startswith("---"):
        generated = fallback_runbook

    return {
        "skill_id": req.skill_id,
        "skill_name": req.skill_name,
        "trigger_description": clean_trigger,
        "requires_tools": req.selected_tools,
        "markdown_content": generated.strip(),
    }


@router.post("/api/skill_studio/save")
async def save_scaffolded_skill(req: SaveScaffoldRequest, request: Request) -> Dict[str, Any]:
    """Persist authored SKILL.md to the skill store and SQLite bindings.

    When agent_id is present, also pin the skill on that agent pack. Skill Studio
    can save without an agent brief [CARD-418]. pack.json is not the binding writer.
    """
    import re
    if not req.skill_id:
        raise HTTPException(status_code=400, detail="skill_id is required")

    clean_agent_id = ""
    if req.agent_id and str(req.agent_id).strip():
        clean_agent_id = re.sub(r"[^a-zA-Z0-9_\-]", "", req.agent_id.lower().strip())
        if not clean_agent_id:
            raise HTTPException(status_code=400, detail="Invalid agent_id format")
    clean_skill_id = re.sub(r"[^a-zA-Z0-9_\-]", "", req.skill_id.lower().strip())

    if not clean_skill_id:
        raise HTTPException(status_code=400, detail="Invalid skill_id format")

    data_root = _workshop_data_root(request)  # app data dir, not the env [CARD-497 D11]

    from src.application.skills.runbook_frontmatter import InvalidSkillTierError, UnknownCatalogToolError
    from src.application.skills.workshop import catalog_tool_ids, persist_workshop_skill

    tool_registry = getattr(request.app.state, "tool_registry", None) or getattr(request.app.state, "tool_reg", None)
    store = getattr(request.app.state, "store", None)
    db_path = getattr(store, "db_path", None)
    try:
        persisted = persist_workshop_skill(
            data_root=data_root,
            agent_id=clean_agent_id or None,
            skill_id=clean_skill_id,
            skill_content=req.skill_content,
            catalog_ids=catalog_tool_ids(tool_registry),
            name=req.name,
            description=req.description,
            tier=req.tier,
            safety=req.safety,
            requires_tools=req.requires_tools,
            db_path=str(db_path) if db_path else None,
        )
    except UnknownCatalogToolError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidSkillTierError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    skill_file = Path(persisted["pack_skill_path"] or persisted["skill_store_path"])
    display_name = (persisted.get("frontmatter") or {}).get("name") or clean_skill_id.replace("-", " ").replace("_", " ").title()

    if clean_agent_id:
        _pin_saved_skill_on_agent(
            request,
            agent_dir=data_root / "packs" / clean_agent_id,
            clean_agent_id=clean_agent_id,
            clean_skill_id=clean_skill_id,
            display_name=display_name,
            req=req,
        )

    return {
        "success": True,
        "agent_id": clean_agent_id or None,
        "skill_id": clean_skill_id,
        "skill_path": str(skill_file),
        "skill_store_path": persisted["skill_store_path"],
        "pinned": bool(clean_agent_id and req.auto_pin),
        "requires_tools": persisted["requires_tools"],
        "tier": persisted["tier"],
        "safety": persisted["safety"],
        "binding_store": "sqlite",
        "markdown_content": persisted["markdown"],
    }


def _pin_saved_skill_on_agent(
    request: Request,
    *,
    agent_dir: Path,
    clean_agent_id: str,
    clean_skill_id: str,
    display_name: str,
    req: SaveScaffoldRequest,
) -> None:
    """Pin a saved skill on one agent pack. Does not write tool bindings into pack.json."""
    agent_dir.mkdir(parents=True, exist_ok=True)
    pack_json_file = agent_dir / "pack.json"
    if pack_json_file.is_file():
        try:
            pack_data = json.loads(pack_json_file.read_text(encoding="utf-8"))
        except Exception:
            pack_data = {}
    else:
        pack_data = {}

    if not isinstance(pack_data, dict):
        pack_data = {}

    pack_data.setdefault("schema_version", "1.0")
    pack_data.setdefault("id", clean_agent_id)
    if req.agent_name:
        pack_data["name"] = req.agent_name
    elif "name" not in pack_data:
        pack_data["name"] = clean_agent_id.replace("-", " ").replace("_", " ").title()

    if req.role_persona:
        pack_data["system_prompt"] = req.role_persona
        pack_data["description"] = req.role_persona[:120]
    elif "description" not in pack_data:
        pack_data["description"] = f"Specialist agent {clean_agent_id}"

    if req.model:
        pack_data["model"] = req.model

    allowed_skills = list(pack_data.get("allowed_skill") or [])
    if req.auto_pin and clean_skill_id not in allowed_skills:
        allowed_skills.append(clean_skill_id)
    pack_data["allowed_skill"] = allowed_skills

    skills_list = list(pack_data.get("skills") or [])
    existing_skill_entry = next((s for s in skills_list if isinstance(s, dict) and s.get("id") == clean_skill_id), None)
    # Identity only. Tool bindings are operational SQLite, not pack.json [CARD-411].
    if existing_skill_entry:
        existing_skill_entry.pop("tools", None)
        existing_skill_entry["name"] = display_name
    else:
        skills_list.append({
            "id": clean_skill_id,
            "name": display_name,
        })
    pack_data["skills"] = skills_list

    pack_json_file.write_text(json.dumps(pack_data, indent=2), encoding="utf-8")

    registry = getattr(request.app.state, "registry", None)
    if registry:
        prof = registry.get_agent(clean_agent_id)
        if prof:
            cur_skills = list(prof.allowed_skill or [])
            if req.auto_pin and clean_skill_id not in cur_skills:
                prof.allowed_skill = cur_skills + [clean_skill_id]
            if req.agent_name:
                prof.name = req.agent_name
            if req.role_persona:
                prof.system_prompt = req.role_persona
            if req.model:
                prof.model = req.model
            if registry.state_store:
                # auto_pin does not set the pack content lock [CARD-449].
                registry.state_store.save_agent_profile(prof)


@router.get("/api/skill_studio/skills")
async def list_workshop_skills_route(request: Request) -> Dict[str, Any]:
    """Skills the Skill Studio picker can open. Every id resolves through the workshop loader [CARD-411]."""
    from src.application.skills.workshop import list_workshop_skills

    return {"skills": list_workshop_skills(_workshop_data_root(request))}


@router.get("/api/skill_studio/skills/{skill_id:path}")
async def get_workshop_skill(skill_id: str, request: Request, agent_id: Optional[str] = None) -> Dict[str, Any]:
    """Load one skill into Skill Studio (frontmatter + SQLite bindings) [CARD-411]."""
    from src.application.skills.workshop import accept_skill_id, load_workshop_skill

    clean_skill_id = accept_skill_id(skill_id or "")
    if not clean_skill_id:
        raise HTTPException(status_code=400, detail="Invalid skill_id")
    clean_agent = accept_skill_id(agent_id or "") if agent_id else None
    if clean_agent and "/" in clean_agent:
        clean_agent = None
    store = getattr(request.app.state, "store", None)
    db_path = getattr(store, "db_path", None)
    loaded = load_workshop_skill(
        _workshop_data_root(request),
        clean_skill_id,
        agent_id=clean_agent,
        db_path=str(db_path) if db_path else None,
    )
    if loaded is None:
        raise HTTPException(status_code=404, detail=f"Skill '{clean_skill_id}' not found")
    return loaded


def _workshop_data_root(request: Request):
    paths = getattr(request.app.state, "data_dir_paths", None)
    root = getattr(paths, "root", None) if paths is not None else None
    if root:
        return Path(root)
    from src.infrastructure.data.resolver import DataDirResolver

    return DataDirResolver().resolve().root


def _permanent_redirect(request: Request, new_path: str) -> RedirectResponse:
    """308 keeps the method, body and query string [CARD-497 D1]."""
    query = request.url.query
    return RedirectResponse(f"{new_path}?{query}" if query else new_path, status_code=308)


@legacy_router.get("/capabilities")
async def legacy_capabilities(request: Request) -> RedirectResponse:
    return _permanent_redirect(request, "/api/tools_studio/capabilities")


@legacy_router.post("/scaffold/runbook")
async def legacy_runbook(request: Request) -> RedirectResponse:
    return _permanent_redirect(request, "/api/skill_studio/runbook")


@legacy_router.post("/scaffold/save")
async def legacy_save(request: Request) -> RedirectResponse:
    return _permanent_redirect(request, "/api/skill_studio/save")


@legacy_router.get("/skills")
async def legacy_skills(request: Request) -> RedirectResponse:
    return _permanent_redirect(request, "/api/skill_studio/skills")


@legacy_router.get("/skills/{skill_id:path}")
async def legacy_skill(skill_id: str, request: Request) -> RedirectResponse:
    return _permanent_redirect(request, f"/api/skill_studio/skills/{quote(skill_id, safe='/')}")
