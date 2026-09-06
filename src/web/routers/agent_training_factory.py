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

from src.application.orchestration.capability_graph import UserPackFinalizer
from src.application.orchestration.tool_synthesizer import ToolSynthesizer
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


class PromoteJobRequest(BaseModel):
    decision: str = Field(default="approved", description="approved | rejected")




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
                        t = meta.get("tools") or []
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


def _select_pack_files(packets) -> Dict[str, str]:
    """Pick pack files for promote.

    Prefer the latest Author files_map so a stale Optimize snapshot cannot
    clobber a later rinse/domain-corrected Author seed (CARD-171).
    """
    merged: Dict[str, str] = {}
    latest_author: Dict[str, str] = {}
    for p in packets:
        payload = getattr(p, "payload", None)
        if payload is None and isinstance(p, dict):
            payload = p.get("payload")
        if not isinstance(payload, dict):
            continue
        files_map = payload.get("files_map")
        if not isinstance(files_map, dict) or not files_map:
            continue
        merged.update({str(k): str(v) for k, v in files_map.items()})
        sender = getattr(p, "sender_role", None)
        node = getattr(p, "node_id", None)
        if sender is None and isinstance(p, dict):
            sender = p.get("sender_role")
            node = p.get("node_id")
        if sender == "author" or node == "author":
            latest_author = {str(k): str(v) for k, v in files_map.items()}
    if latest_author:
        merged.update(latest_author)
    return merged


def _repo(request: Request) -> FactoryPacketRepository:
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(status_code=500, detail="Database store not available")
    return FactoryPacketRepository(store)


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

    job_id = f"fjob_{uuid.uuid4().hex[:12]}"
    job = FactoryJob(
        id=job_id,
        target_agent_id=payload.target_agent_id,
        session_id=session_id,
        status="queued",
        seed_intent=payload.seed_intent,
        objectives=list(payload.objectives or []),
        target_host=payload.target_host,
        active_graph_id="agent_training_factory_v1",
        current_node_id="ground",
    )
    repo.save_job(job)

    # Initial WorkPacket
    work_pkt = WorkPacket(
        goal=payload.seed_intent,
        target_agent_id=payload.target_agent_id,
        facts=payload.objectives,
        constraints=[f"risk_policy={payload.risk_policy}"],
        done_when="Seed objectives verified in sandbox battery",
        target_host=payload.target_host,
        target_directory=payload.target_directory,
    )
    envelope = FactoryPacket(
        id=f"fpkt_{uuid.uuid4().hex[:12]}",
        job_id=job_id,
        packet_type="work",
        sender_role="orchestrator",
        recipient_role="ground",
        node_id="ground",
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
    stepped = await runner.step_job(job_id)
    repo = _repo(request)
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

    return {
        "success": True,
        "job": job.model_dump(),
        "packets": [p.model_dump() for p in packets],
        "eval_runs": [e.model_dump() for e in eval_runs],
    }


@router.post("/jobs/{job_id}/promote")
async def promote_factory_job(job_id: str, request: Request, payload: Optional[PromoteJobRequest] = None) -> Dict[str, Any]:
    repo = _repo(request)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Factory job {job_id} not found")

    decision = payload.decision if payload else "approved"
    if decision != "approved":
        repo.update_job_status(job_id, "failed", current_node_id="rejected")
        return {"success": True, "job_id": job_id, "status": "failed"}

    # Finalize pack
    data_paths = getattr(request.app.state, "data_dir_paths", None)
    data_dir = str(data_paths.root) if data_paths else "./data"
    finalizer = UserPackFinalizer(data_dir=data_dir)

    clean_slug = job.target_agent_id.replace("-", "_").lower()
    default_tool_name = f"manage_{clean_slug}"

    packets = repo.list_packets(job_id)
    files_to_write: Dict[str, str] = _select_pack_files(packets)
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
        synthesized_map = ToolSynthesizer.synthesize_tool(
            agent_id=job.target_agent_id,
            seed_intent=job.seed_intent,
            objectives=getattr(job, "objectives", []) or [],
            tool_name=default_tool_name,
        )
        files_to_write.update(synthesized_map)
        tool_names.append(default_tool_name)

    unique_tools = list(dict.fromkeys(tool_names))

    data_dir = getattr(request.app.state, "data_dir_paths", None)
    data_dir = data_dir.root if data_dir else "./data"
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

    pack_dir = finalizer.finalize_pack(
        agent_id=job.target_agent_id,
        manifest_data=manifest_data,
        files=files_to_write,
    )

    # Dynamically register newly finalized tool handlers in master tool registry
    tool_reg = getattr(request.app.state, "tool_reg", None) or getattr(request.app.state, "tool_registry", None)

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
            if hasattr(store, "save_custom_agent_profile"):
                try:
                    store.save_custom_agent_profile(agent_profile)
                except Exception:
                    pass

    repo.update_job_status(job_id, "done", current_node_id="done")

    return {
        "success": True,
        "job_id": job_id,
        "agent_id": job.target_agent_id,
        "status": "done",
        "pack_dir": pack_dir,
    }
