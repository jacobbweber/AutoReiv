"""
Agent Training Factory API Router [CARD-171, REQ-FACT-003, REQ-FACT-005, REQ-FACT-012, REQ-FACT-014].

REST endpoints for launching training jobs, retrieving status/eval packets,
and promoting certified agent packs. Prefix: /api/agent_training_factory.
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.application.agent_training_factory.phases.promote import check_tool_collisions
from src.application.agent_training_factory.prompt_registry import (
    get_all_phase_instructions,
    reset_phase_instruction,
    save_phase_instruction,
)
from src.application.orchestration.capability_graph import UserPackFinalizer
from src.application.orchestration.tool_synthesizer import ToolSynthesizer  # noqa: F401
from src.domain.orchestration.factory_packets import FactoryJob, FactoryPacket, WorkPacket
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository

router = APIRouter(prefix="/api/agent_training_factory", tags=["Agent Training Factory"])


class CreateFactoryJobRequest(BaseModel):
    target_agent_id: str = Field(description="Slug for new agent pack")
    seed_intent: str = Field(description="High-level description of agent purpose")
    target_host: Optional[str] = Field(default=None, description="Remote host / IP")
    target_directory: Optional[str] = Field(default=None, description="Target host directory")
    objectives: List[str] = Field(default_factory=list, description="Top starter objectives")
    risk_policy: str = Field(default="ask", description="Approval requirement policy")
    session_id: Optional[str] = Field(default=None, description="Originating chat session ID")
    deliverable_type: Optional[str] = Field(default="auto", description="Deliverable architecture taxonomy (auto, mcp, tool, skill)")
    constraints: Optional[str] = Field(default=None, description="Technical constraints or banned commands")
    prerequisites: Optional[str] = Field(default=None, description="Prerequisite binaries or system modules")
    reference_docs: Optional[str] = Field(default=None, description="API documentation references or guidelines")
    capability_gap_id: Optional[str] = Field(default=None, description="Optional capability gap ID to link and resolve")


class PromoteJobRequest(BaseModel):
    decision: str = Field(default="approved", description="approved | rejected")
    allow_overwrite: bool = Field(default=False, description="Allow overwriting existing tools on collision")


class ScaffoldRunbookRequest(BaseModel):
    agent_id: Optional[str] = None
    skill_id: str
    skill_name: str
    trigger_description: str
    intent_notes: Optional[str] = None
    selected_tools: List[str] = Field(default_factory=list)
    source_context: Optional[str] = None


class SaveScaffoldRequest(BaseModel):
    agent_id: str
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





def _skills_from_files_map(files_map: Dict[str, str]) -> List[Dict[str, Any]]:
    """Derive pack skill entries from authored skills/<id>/SKILL.md paths (CARD-171 multi-skill)."""
    skills: List[Dict[str, Any]] = []
    for rel, content in (files_map or {}).items():
        norm = str(rel).replace("\\", "/")
        if not (norm.startswith("skills/") and norm.endswith("/SKILL.md")):
            continue
        parts = norm.split("/")
        if len(parts) < 3:
            continue
        skill_id = parts[1]
        tools: List[str] = []
        name = skill_id.replace("-", " ").replace("_", " ").title()
        description = f"Capabilities for {skill_id}"
        try:
            body = content or ""
            if body.strip().startswith("---"):
                chunk = body.split("---", 2)
                if len(chunk) >= 3:
                    import yaml
                    meta = yaml.safe_load(chunk[1]) or {}
                    if isinstance(meta, dict):
                        if isinstance(meta.get("name"), str):
                            name = meta["name"]
                        if isinstance(meta.get("description"), str):
                            description = meta["description"]
                        t = meta.get("tools") or meta.get("requires_tools") or []
                        if isinstance(t, list):
                            tools = [str(x) for x in t]
        except Exception:
            tools = []
        if not tools:
            # Infer from sibling tool files mentioning this skill id is unreliable;
            # leave empty and let caller merge tool_names by blueprint.
            tools = []
        skills.append(
            {
                "id": skill_id,
                "name": name,
                "description": description,
                "tools": tools,
            }
        )
    return skills


def _select_pack_files(packets, seed_intent: str = "", objectives: list | None = None) -> Dict[str, str]:
    """Pick pack files for promote.

    Prefers the latest Author files_map to ensure domain-corrected seeds
    and rinsed tools win over stale initial drafts or outdated optimize snapshots.
    """
    author_maps: list[Dict[str, str]] = []
    fallback: Dict[str, str] = {}
    for p in packets:
        payload = getattr(p, "payload", None)
        if payload is None and isinstance(p, dict):
            payload = p.get("payload")
        if not isinstance(payload, dict):
            continue
        files_map = payload.get("files_map")
        if not isinstance(files_map, dict) or not files_map:
            continue
        as_dict = {str(k): str(v) for k, v in files_map.items()}
        fallback = as_dict
        sender = getattr(p, "sender_role", None)
        node = getattr(p, "node_id", None)
        if sender is None and isinstance(p, dict):
            sender = p.get("sender_role")
            node = p.get("node_id")
        if sender == "author" or node == "author":
            author_maps.append(as_dict)
    if author_maps:
        return author_maps[-1]
    return fallback


def extract_job_initial_inputs(job: FactoryJob, packets: List[Any]) -> Dict[str, Any]:
    """Extract preserved starter inputs from FactoryJob and its initial WorkPacket [CARD-182, REQ-LAB-003]."""
    inputs = {
        "target_agent_id": job.target_agent_id,
        "seed_intent": job.seed_intent,
        "objectives": list(job.objectives or []),
        "target_host": job.target_host,
        "target_directory": None,
        "deliverable_type": "auto",
        "risk_policy": "ask",
        "constraints": "",
        "prerequisites": "",
        "reference_docs": "",
    }
    for p in packets:
        payload = getattr(p, "payload", None)
        if isinstance(p, dict):
            payload = p.get("payload")
        sender = getattr(p, "sender_role", None) or (p.get("sender_role") if isinstance(p, dict) else None)
        recipient = getattr(p, "recipient_role", None) or (p.get("recipient_role") if isinstance(p, dict) else None)
        if sender == "orchestrator" and recipient == "intent_distill" and isinstance(payload, dict):
            if payload.get("target_directory"):
                inputs["target_directory"] = payload.get("target_directory")
            constraints = payload.get("constraints") or []
            for c in constraints:
                if isinstance(c, str):
                    if c.startswith("deliverable_type="):
                        inputs["deliverable_type"] = c.split("=", 1)[1]
                    elif c.startswith("risk_policy="):
                        inputs["risk_policy"] = c.split("=", 1)[1]
                    elif c.startswith("constraints="):
                        inputs["constraints"] = c.split("=", 1)[1]
                    elif c.startswith("prerequisites="):
                        inputs["prerequisites"] = c.split("=", 1)[1]
                    elif c.startswith("reference_docs="):
                        inputs["reference_docs"] = c.split("=", 1)[1]
            break
    return inputs


def _repo(request: Request) -> FactoryPacketRepository:
    existing = getattr(request.app.state, "factory_repo", None)
    if existing is not None:
        return existing
    store = getattr(request.app.state, "store", None) or getattr(request.app.state, "state_store", None)
    if store is None:
        raise HTTPException(status_code=500, detail="Database store not available")
    return FactoryPacketRepository(store)


def _gap_repo(request: Request):
    """Optional capability-gap repo for CARD-270 status honesty."""
    repo = getattr(request.app.state, "capability_gap_repo", None)
    if repo is not None:
        return repo
    store = getattr(request.app.state, "store", None) or getattr(request.app.state, "state_store", None)
    if store is None:
        return None
    conn_mgr = getattr(store, "connection_manager", None) or store
    try:
        from src.infrastructure.memory.repositories.capability_gaps import CapabilityGapRepository

        return CapabilityGapRepository(connection_manager=conn_mgr)
    except Exception:
        return None


def _sync_linked_gap_status(request: Request, job, status: str) -> None:
    from src.application.agent_training_factory.gap_link import gap_id_from_job

    gap_id = gap_id_from_job(job)
    if not gap_id:
        return
    gap_repo = _gap_repo(request)
    if gap_repo is None:
        return
    try:
        gap_repo.update_gap_status(gap_id, status)
    except Exception:
        pass


@router.post("/jobs")
async def create_factory_job(payload: CreateFactoryJobRequest, request: Request) -> Dict[str, Any]:
    repo = _repo(request)
    store = getattr(request.app.state, "store", None)
    session_id = payload.session_id

    # Anchor training jobs to the AutoReiv platform supervisor session [REQ-FACT-018]
    if store is not None:
        if session_id:
            existing = store.get_session(session_id)
            if not existing or existing.agent_id != "autoreiv":
                autoreiv_sessions = store.list_sessions(agent_id="autoreiv")
                if autoreiv_sessions:
                    session_id = autoreiv_sessions[0].id
                else:
                    new_sess = store.create_session(agent_id="autoreiv", title="AutoReiv Control Plane")
                    session_id = new_sess.id
        else:
            autoreiv_sessions = store.list_sessions(agent_id="autoreiv")
            if autoreiv_sessions:
                session_id = autoreiv_sessions[0].id
            else:
                new_sess = store.create_session(agent_id="autoreiv", title="AutoReiv Control Plane")
                session_id = new_sess.id

    if not session_id:
        session_id = f"sess_factory_{uuid.uuid4().hex[:8]}"

    objectives = list(payload.objectives or [])
    if payload.capability_gap_id:
        from src.application.agent_training_factory.gap_link import (
            GAP_TRAINING,
            encode_gap_id_objective,
        )

        gap_obj = encode_gap_id_objective(payload.capability_gap_id)
        if gap_obj not in objectives:
            objectives.insert(0, gap_obj)

        gap_repo = _gap_repo(request)
        if gap_repo is not None:
            try:
                gap_repo.update_gap_status(payload.capability_gap_id, GAP_TRAINING)
            except Exception:
                pass

    job_id = f"fjob_{uuid.uuid4().hex[:12]}"
    job = FactoryJob(
        id=job_id,
        target_agent_id=payload.target_agent_id,
        session_id=session_id,
        status="queued",
        seed_intent=payload.seed_intent,
        objectives=objectives,
        target_host=payload.target_host,
        active_graph_id="agent_training_factory_v1",
        current_node_id="intent_distill",
    )
    repo.save_job(job)

    constraints_list = [f"risk_policy={payload.risk_policy}"]
    if payload.deliverable_type and payload.deliverable_type != "auto":
        constraints_list.append(f"deliverable_type={payload.deliverable_type}")
    if payload.constraints:
        constraints_list.append(f"constraints={payload.constraints}")
    if payload.prerequisites:
        constraints_list.append(f"prerequisites={payload.prerequisites}")
    if payload.reference_docs:
        constraints_list.append(f"reference_docs={payload.reference_docs}")

    target_dir = payload.target_directory
    if not target_dir and store is not None:
        try:
            sel_proj_raw = store.get_setting("selected_project")
            if sel_proj_raw:
                sel_proj = json.loads(sel_proj_raw) if isinstance(sel_proj_raw, str) else sel_proj_raw
                if isinstance(sel_proj, dict) and sel_proj.get("path"):
                    target_dir = str(sel_proj["path"])
        except Exception:
            pass

    # Initial WorkPacket
    work_pkt = WorkPacket(
        goal=payload.seed_intent,
        target_agent_id=payload.target_agent_id,
        facts=payload.objectives,
        constraints=constraints_list,
        done_when="Seed objectives verified in sandbox battery",
        target_host=payload.target_host,
        target_directory=target_dir,
    )
    envelope = FactoryPacket(
        id=f"fpkt_{uuid.uuid4().hex[:12]}",
        job_id=job_id,
        packet_type="work",
        sender_role="orchestrator",
        recipient_role="intent_distill",
        node_id="intent_distill",
        payload=work_pkt.model_dump(),
    )
    repo.save_packet(envelope)

    # Immediately trigger runner tick if runner is active [REQ-FACT-016]
    runner = getattr(request.app.state, "factory_orchestrator", None)
    if runner is not None:
        import asyncio

        asyncio.create_task(runner.tick())

    return {
        "success": True,
        "job_id": job.id,
        "status": job.status,
        "current_node_id": job.current_node_id,
        "target_agent_id": job.target_agent_id,
        "session_id": job.session_id,
        "capability_gap_id": payload.capability_gap_id,
    }


@router.get("/gaps")
async def list_factory_gaps(
    request: Request,
    agent_id: Optional[str] = None,
    status: Optional[str] = "pending",
) -> Dict[str, Any]:
    """List queued capability gaps for the factory backlog [REQ-FACT-027]."""
    repo = _gap_repo(request)
    if repo is None:
        return {"success": True, "agent_id": agent_id, "gaps": []}
    gaps = repo.list_gaps(agent_id=agent_id, status=status)
    return {
        "success": True,
        "agent_id": agent_id,
        "gaps": [g.model_dump() for g in gaps],
    }


@router.get("/jobs")
async def list_factory_jobs(request: Request, status: Optional[str] = None) -> Dict[str, Any]:
    repo = _repo(request)
    jobs = repo.list_jobs(status=status)
    out = []
    for j in jobs:
        d = j.model_dump()
        pkts = repo.list_packets(j.id)
        d["packets_count"] = len(pkts)
        d["latest_packet"] = pkts[-1].model_dump() if pkts else None
        out.append(d)
    return {
        "success": True,
        "jobs": out,
    }


@router.post("/jobs/{job_id}/step")
async def step_factory_job(job_id: str, request: Request) -> Dict[str, Any]:
    runner = getattr(request.app.state, "factory_orchestrator", None)
    if not runner:
        raise HTTPException(status_code=500, detail="Agent Training Factory orchestrator not available")
    repo = _repo(request)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    stepped = await runner.step_job(job_id)
    job = repo.get_job(job_id)
    return {
        "success": True,
        "stepped": stepped,
        "job": job.model_dump() if job else None,
    }


@router.delete("/jobs/{job_id}")
async def delete_factory_job(job_id: str, request: Request) -> Dict[str, Any]:
    repo = _repo(request)
    deleted = repo.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Factory job {job_id} not found")
    return {"success": True, "job_id": job_id, "deleted": True}


@router.get("/jobs/{job_id}")
async def get_factory_job(job_id: str, request: Request) -> Dict[str, Any]:
    repo = _repo(request)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Factory job {job_id} not found")

    packets = repo.list_packets(job_id)
    eval_runs = repo.list_eval_runs(job_id)
    inputs = extract_job_initial_inputs(job, packets)

    return {
        "success": True,
        "job": job.model_dump(),
        "packets": [p.model_dump() for p in packets],
        "eval_runs": [e.model_dump() for e in eval_runs],
        "inputs": inputs,
    }


@router.post("/jobs/{job_id}/promote")
async def promote_factory_job(job_id: str, request: Request, payload: Optional[PromoteJobRequest] = None) -> Dict[str, Any]:
    repo = _repo(request)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Factory job {job_id} not found")

    decision = payload.decision if payload else "approved"
    if decision != "approved":
        from src.application.agent_training_factory.gap_link import GAP_FAILED

        repo.update_job_status(job_id, "failed", current_node_id="rejected")
        _sync_linked_gap_status(request, job, GAP_FAILED)
        return {"success": True, "job_id": job_id, "status": "failed", "gap_status": GAP_FAILED}

    # Finalize pack
    data_paths = getattr(request.app.state, "data_dir_paths", None)
    if data_paths:
        data_dir = str(data_paths.root)
    else:
        from src.infrastructure.data.resolver import DataDirResolver

        data_dir = str(DataDirResolver().resolve().root)
    finalizer = UserPackFinalizer(data_dir=data_dir)

    clean_slug = job.target_agent_id.replace("-", "_").lower()

    packets = repo.list_packets(job_id)
    files_to_write: Dict[str, str] = _select_pack_files(packets, seed_intent=job.seed_intent or "", objectives=list(job.objectives or []))
    tool_names = []

    for p in packets:
        if p.payload and "tool_name" in p.payload:
            tool_names.append(p.payload["tool_name"])
        if p.payload and isinstance(p.payload.get("tool_names"), list):
            tool_names.extend([str(x) for x in p.payload.get("tool_names") or []])
    # Infer tool names from files_map keys
    for rel in files_to_write:
        norm = str(rel).replace("\\", "/")
        if norm.startswith("tools/") and norm.endswith(".py"):
            tool_names.append(Path(norm).stem)

    if not files_to_write:
        # CARD-270: refuse invent-theatre at HITL gate — sandbox must have produced pack files
        from src.application.agent_training_factory.gap_link import GAP_CANT

        repo.update_job_status(job_id, "failed", current_node_id="promote_cant")
        _sync_linked_gap_status(request, job, GAP_CANT)
        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Cannot promote: no sandbox-verified pack files on this factory job. "
                    "Honest can't — Approve will not invent a tool at the gate."
                ),
                "gap_status": GAP_CANT,
                "job_id": job_id,
            },
        )

    unique_tools = list(dict.fromkeys(tool_names))

    data_dir_obj = getattr(request.app.state, "data_dir_paths", None)
    if data_dir_obj:
        data_dir = data_dir_obj.root
    else:
        from src.infrastructure.data.resolver import DataDirResolver

        data_dir = DataDirResolver().resolve().root

    # Tool name collision guard [REQ-FACT-054]
    collisions = check_tool_collisions(
        target_agent_id=job.target_agent_id,
        proposed_tools=unique_tools,
        data_dir=data_dir,
    )
    if collisions.get("has_collision") and not (payload and payload.allow_overwrite):
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"Tool name collision detected for agent '{job.target_agent_id}': {collisions.get('conflicts')}. Set allow_overwrite=true to replace.",
                "conflicts": collisions.get("conflicts"),
                "duplicate_declarations": collisions.get("duplicate_declarations"),
                "target_pack_conflicts": collisions.get("target_pack_conflicts"),
                "cross_pack_conflicts": collisions.get("cross_pack_conflicts"),
            },
        )

    registry = getattr(request.app.state, "registry", None)
    existing_profile = registry.get_agent(job.target_agent_id) if registry else None


    existing_pack_file = Path(data_dir) / "packs" / job.target_agent_id / "pack.json"
    existing_pack_data: Dict[str, Any] = {}
    if existing_pack_file.is_file():
        try:
            existing_pack_data = json.loads(existing_pack_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Merge tool names
    existing_tools = list(existing_pack_data.get("pack_tool_names") or [])
    if existing_profile and existing_profile.allowed_tool_names:
        existing_tools.extend(existing_profile.allowed_tool_names)
    merged_tools = list(dict.fromkeys(existing_tools + unique_tools))

    # Merge skills (multi-skill: prefer skills/<id>/SKILL.md from files_map)
    existing_skills = list(existing_pack_data.get("skills") or [])
    authored_skills = _skills_from_files_map(files_to_write)
    # Also accept blueprint_skills from latest author packet
    for p in packets:
        payload = getattr(p, "payload", None) or {}
        for sk in payload.get("blueprint_skills") or []:
            if isinstance(sk, dict) and sk.get("id"):
                authored_skills.append(sk)
    # Deduplicate authored by id (last wins)
    authored_by_id = {str(s.get("id")): s for s in authored_skills if s.get("id")}
    if authored_by_id:
        by_id = {str(s.get("id")): dict(s) for s in existing_skills if s.get("id")}
        for sid, sk in authored_by_id.items():
            if sid in by_id:
                merged_t = list(dict.fromkeys(list(by_id[sid].get("tools") or []) + list(sk.get("tools") or [])))
                by_id[sid].update({k: v for k, v in sk.items() if v})
                by_id[sid]["tools"] = merged_t or by_id[sid].get("tools") or []
            else:
                by_id[sid] = dict(sk)
                by_id[sid]["tools"] = list(dict.fromkeys(list(sk.get("tools") or [])))
        # Ensure tools from unique_tools land on matching skills when skill tools empty
        for sid, sk in by_id.items():
            if not sk.get("tools"):
                # assign tools whose names appear in skill id tokens
                guessed = [t for t in unique_tools if sid.replace("-", "_") in t or sid.split("-")[-1] in t]
                sk["tools"] = guessed or list(unique_tools)
        existing_skills = list(by_id.values())
    else:
        skill_found = False
        for sk in existing_skills:
            if sk.get("id") == clean_slug:
                sk["tools"] = list(dict.fromkeys(list(sk.get("tools") or []) + unique_tools))
                skill_found = True
                break
        if not skill_found:
            existing_skills.append({
                "id": clean_slug,
                "name": f"{job.target_agent_id.replace('-', ' ').title()} Skill",
                "description": f"Capabilities for {job.target_agent_id}",
                "tools": unique_tools,
            })

    allowed_skills = list(
        dict.fromkeys(
            list(existing_pack_data.get("allowed_skill") or [])
            + [clean_slug]
            + [str(s.get("id")) for s in existing_skills if s.get("id")]
        )
    )
    if existing_profile and existing_profile.allowed_skill:
        allowed_skills = list(dict.fromkeys(allowed_skills + existing_profile.allowed_skill))

    manifest_data = {
        "id": job.target_agent_id,
        "name": (existing_profile.name if existing_profile else None) or existing_pack_data.get("name") or job.target_agent_id.replace("-", " ").title(),
        "description": (existing_profile.description if existing_profile else None) or existing_pack_data.get("description") or job.seed_intent,
        "system_prompt": (existing_profile.system_prompt if existing_profile else None) or existing_pack_data.get("system_prompt") or f"You are a specialist agent trained for: {job.seed_intent}",
        "avatar_icon": (existing_profile.avatar_icon if existing_profile else None) or existing_pack_data.get("avatar_icon") or "bot",
        "tone": (existing_profile.tone.value if existing_profile and hasattr(existing_profile.tone, "value") else str(getattr(existing_profile, "tone", "concise"))) if existing_profile else existing_pack_data.get("tone", "concise"),
        "show_in_chat": True,
        "pack_tool_names": merged_tools,
        "allowed_tool_names": merged_tools,
        "allowed_skill": allowed_skills,
        "skills": existing_skills,
    }

    has_mcp_deliverable = "mcp/server.py" in files_to_write or existing_pack_data.get("mcp_server") or existing_pack_data.get("mcp_servers")
    if has_mcp_deliverable:
        mcp_cfg = existing_pack_data.get("mcp_server") or {
            "enabled": True,
            "entrypoint": "mcp/server.py",
            "transport": "sse",
            "url": "http://localhost:8080/sse",
        }
        manifest_data["mcp_server"] = mcp_cfg

        existing_mcp_list = existing_pack_data.get("mcp_servers") or []
        if not existing_mcp_list:
            existing_mcp_list = [
                {
                    "name": f"{clean_slug}_server",
                    "transport": "sse",
                    "url": "http://localhost:8080/sse",
                    "command": [],
                    "env": {},
                    "headers": {},
                    "enabled": True,
                }
            ]
        manifest_data["mcp_servers"] = existing_mcp_list

        # Strict deliverable constraint: Purge loose tools from files_to_write [CARD-184]
        files_to_write = {
            k: v
            for k, v in files_to_write.items()
            if not k.startswith("tools/") and "/tools/" not in k.replace("\\", "/")
        }

    pack_dir = finalizer.finalize_pack(
        agent_id=job.target_agent_id,
        manifest_data=manifest_data,
        files=files_to_write,
    )

    # Mount pack MCP server into MCPClientManager if active
    mcp_mgr = getattr(request.app.state, "mcp_manager", None) or getattr(request.app.state, "mcp_client_manager", None)
    if mcp_mgr is not None and has_mcp_deliverable:
        for s_dict in manifest_data.get("mcp_servers", []):
            if s_dict.get("enabled", True) and s_dict.get("name"):
                try:
                    await mcp_mgr.mount_server(
                        name=s_dict["name"],
                        command=s_dict.get("command"),
                        env=s_dict.get("env"),
                        transport=s_dict.get("transport", "stdio"),
                        url=s_dict.get("url"),
                        headers=s_dict.get("headers"),
                    )
                except Exception:
                    pass

    # Dynamically register newly finalized tool handlers in master tool registry for non-MCP deliverables
    tool_reg = getattr(request.app.state, "tool_reg", None) or getattr(request.app.state, "tool_registry", None)

    if not has_mcp_deliverable:
        for t_name in merged_tools:
            loaded_handler = None
            tool_py_path = Path(pack_dir) / f"tools/{t_name}.py"
            if tool_py_path.is_file():
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(f"live_pack_{t_name}", str(tool_py_path))
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        if hasattr(mod, t_name):
                            loaded_handler = getattr(mod, t_name)
                except Exception:
                    pass

            def _make_handler(tool_id: str, agent_id: str):
                def _handler(action: str = "status", **kwargs):
                    return {"success": True, "action": action, "agent": agent_id, "tool": tool_id, "details": kwargs}
                return _handler

            handler = loaded_handler or _make_handler(t_name, job.target_agent_id)
            if tool_reg:
                tool_reg.register_tool(
                    name=t_name,
                    description=f"Automated capability tool for {job.target_agent_id}.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "description": "Action to perform (e.g. status, list, create)"},
                        },
                    },
                    handler=handler,
                )
            if registry and getattr(registry, "master_tool_registry", None):
                registry.master_tool_registry.register_tool(
                    name=t_name,
                    description=f"Automated capability tool for {job.target_agent_id}.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "description": "Action to perform (e.g. status, list, create)"},
                        },
                    },
                    handler=handler,
                )

    # Pack skills stay under packs/<id>/skills/ only. Copying into $DATA_DIR/skills
    # polluted Agent Studio "Platform Skills" after ATF promote (CARD-171 cleanup).
    catalog = getattr(request.app.state, "user_skill_catalog", None)
    if catalog and hasattr(catalog, "list_manifests"):
        try:
            catalog.list_manifests()
        except Exception:
            pass

    # Immediately import the promoted pack into the live agent registry and state store
    store = getattr(request.app.state, "store", None) or getattr(request.app.state, "state_store", None)
    if registry is not None and store is not None:
        from src.application.agent_packs.service import AgentPackService

        available = None
        if tool_reg and hasattr(tool_reg, "list_tools"):
            available = {t.name for t in tool_reg.list_tools()}
        service = AgentPackService(
            data_dir=Path(data_dir),
            agent_registry=registry,
            store=store,
            available_tools=available,
        )
        try:
            service.import_path(pack_dir)
        except Exception:
            pass

        # Update in-memory and persisted profile directly
        agent_profile = registry.get_agent(job.target_agent_id)
        if agent_profile:
            agent_profile.allowed_tool_names = list(merged_tools)
            if hasattr(agent_profile, "pack_tool_names"):
                agent_profile.pack_tool_names = list(merged_tools)
            agent_profile.allowed_skill = list(allowed_skills)
            if "mcp_servers" in manifest_data:
                from src.domain.settings.models import MCPServerConfig

                agent_profile.mcp_servers = [
                    MCPServerConfig.model_validate(s) if not isinstance(s, MCPServerConfig) else s
                    for s in manifest_data["mcp_servers"]
                ]
            registry.register_custom_agent(agent_profile)

    # CARD-270: mark linked gap trained only after successful promote write
    from src.application.agent_training_factory.gap_link import GAP_TRAINED

    _sync_linked_gap_status(request, job, GAP_TRAINED)
    repo.update_job_status(job_id, "done", current_node_id="done")

    return {
        "success": True,
        "job_id": job_id,
        "agent_id": job.target_agent_id,
        "status": "done",
        "gap_status": GAP_TRAINED,
        "pack_dir": pack_dir,
        "container_build_cmd": (
            f"docker build -t autoreiv-{job.target_agent_id}-mcp:latest packs/{job.target_agent_id}/mcp"
            if has_mcp_deliverable
            else None
        ),
    }


class UpdatePhaseInstructionRequest(BaseModel):
    prompt: str = Field(description="Custom prompt instructions for the phase")


def _factory_db_path(request: Request) -> Optional[str]:
    paths = getattr(request.app.state, "data_dir_paths", None)
    if paths and hasattr(paths, "db_path") and paths.db_path:
        return str(paths.db_path)
    store = getattr(request.app.state, "store", None) or getattr(request.app.state, "state_store", None)
    if store and hasattr(store, "db_path") and store.db_path:
        return str(store.db_path)
    return None


@router.get("/phases/instructions")
def list_phase_instructions(request: Request) -> Dict[str, Any]:
    db_path = _factory_db_path(request)
    phases = get_all_phase_instructions(db_path)
    return {"phases": phases}


@router.put("/phases/{phase_id}/instructions")
def update_phase_instruction(phase_id: str, payload: UpdatePhaseInstructionRequest, request: Request) -> Dict[str, Any]:
    db_path = _factory_db_path(request)
    if not db_path:
        raise HTTPException(status_code=500, detail="Database path not initialized.")
    try:
        updated = save_phase_instruction(phase_id, payload.prompt, db_path)
        return {"success": True, "phase": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/phases/{phase_id}/instructions")
def delete_phase_instruction(phase_id: str, request: Request) -> Dict[str, Any]:
    db_path = _factory_db_path(request)
    if not db_path:
        raise HTTPException(status_code=500, detail="Database path not initialized.")
    try:
        reset_result = reset_phase_instruction(phase_id, db_path)
        return {"success": True, "phase": reset_result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== CARD-386: 3-Column Scaffolder Endpoints ====================

@router.get("/capabilities")
async def get_factory_capabilities(request: Request) -> Dict[str, Any]:
    """List registered tools grouped by namespace/server for live capability inspection."""
    tool_registry = getattr(request.app.state, "tool_registry", None) or getattr(request.app.state, "tool_reg", None)
    tools = tool_registry.list_tools() if tool_registry else []

    from src.application.agent_packs.schema import DYNAMIC_SKILL_TOOLS, PLATFORM_SKILL_TOOLS

    namespaces: Dict[str, Dict[str, Any]] = {}

    for tool in tools:
        t_name = tool.name
        t_desc = tool.description or ""
        t_params = tool.parameters or {}

        if t_name.startswith("mcp_"):
            parts = t_name.split("_")
            server_key = parts[1] if len(parts) > 1 else "generic"
            ns_id = f"mcp:{server_key}"
            ns_name = f"MCP: {server_key.title()}"
            ns_source = "mcp"
        elif any(t_name in t_list for t_list in PLATFORM_SKILL_TOOLS.values()):
            matched_skill = next((s for s, t_list in PLATFORM_SKILL_TOOLS.items() if t_name in t_list), "platform")
            ns_id = f"platform:{matched_skill}"
            ns_name = f"Platform: {matched_skill.title()}"
            ns_source = "platform"
        elif any(t_name in t_list for t_list in DYNAMIC_SKILL_TOOLS.values()):
            matched_skill = next((s for s, t_list in DYNAMIC_SKILL_TOOLS.items() if t_name in t_list), "dynamic")
            ns_id = f"dynamic:{matched_skill}"
            ns_name = f"Dynamic: {matched_skill.title()}"
            ns_source = "dynamic"
        else:
            ns_id = "builtin"
            ns_name = "Built-in Primitives"
            ns_source = "builtin"

        if ns_id not in namespaces:
            namespaces[ns_id] = {
                "id": ns_id,
                "name": ns_name,
                "source": ns_source,
                "tools": [],
            }
        namespaces[ns_id]["tools"].append({
            "name": t_name,
            "description": t_desc,
            "parameters": t_params,
            "is_high_risk": getattr(tool, "is_high_risk", False),
        })

    return {
        "total_tools": len(tools),
        "namespaces": list(namespaces.values()),
    }


@router.post("/scaffold/runbook")
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
    from src.application.agent_training_factory.llm import phase_llm_text

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


@router.post("/scaffold/save")
async def save_scaffolded_skill(req: SaveScaffoldRequest, request: Request) -> Dict[str, Any]:
    """Persist authored SKILL.md and auto-pin it to target agent pack manifest."""
    import re
    if not req.agent_id or not req.skill_id:
        raise HTTPException(status_code=400, detail="agent_id and skill_id are required")

    clean_agent_id = re.sub(r"[^a-zA-Z0-9_\-]", "", req.agent_id.lower().strip())
    clean_skill_id = re.sub(r"[^a-zA-Z0-9_\-]", "", req.skill_id.lower().strip())

    if not clean_agent_id or not clean_skill_id:
        raise HTTPException(status_code=400, detail="Invalid agent_id or skill_id format")

    from src.infrastructure.data.resolver import DataDirResolver
    resolver = DataDirResolver()
    data_root = resolver.resolve().root
    packs_dir = data_root / "packs"
    agent_dir = packs_dir / clean_agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)

    from src.application.skills.runbook_frontmatter import InvalidSkillTierError, UnknownCatalogToolError
    from src.application.skills.workshop import catalog_tool_ids, persist_workshop_skill

    tool_registry = getattr(request.app.state, "tool_registry", None) or getattr(request.app.state, "tool_reg", None)
    store = getattr(request.app.state, "store", None)
    db_path = getattr(store, "db_path", None)
    try:
        persisted = persist_workshop_skill(
            data_root=data_root,
            agent_id=clean_agent_id,
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

    skill_file = Path(persisted["pack_skill_path"])
    display_name = (persisted.get("frontmatter") or {}).get("name") or clean_skill_id.replace("-", " ").replace("_", " ").title()

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
                registry.state_store.save_agent_profile(prof)
                if req.auto_pin and hasattr(registry.state_store, "mark_agent_user_modified"):
                    registry.state_store.mark_agent_user_modified(clean_agent_id, modified=True)

    return {
        "success": True,
        "agent_id": clean_agent_id,
        "skill_id": clean_skill_id,
        "skill_path": str(skill_file),
        "skill_store_path": persisted["skill_store_path"],
        "pinned": req.auto_pin,
        "requires_tools": persisted["requires_tools"],
        "tier": persisted["tier"],
        "safety": persisted["safety"],
        "binding_store": "sqlite",
        "markdown_content": persisted["markdown"],
    }


@router.get("/skills")
async def list_workshop_skills_route(request: Request) -> Dict[str, Any]:
    """Skills the Factory picker can open. Every id resolves through the workshop loader [CARD-411]."""
    from src.application.skills.workshop import list_workshop_skills

    return {"skills": list_workshop_skills(_workshop_data_root(request))}


@router.get("/skills/{skill_id:path}")
async def get_workshop_skill(skill_id: str, request: Request, agent_id: Optional[str] = None) -> Dict[str, Any]:
    """Load one skill into the Factory workshop (frontmatter + SQLite bindings) [CARD-411]."""
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


