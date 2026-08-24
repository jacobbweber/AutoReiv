"""
AutoReiv Control Plane - Unified FastAPI Application [REQ-WEB-001 - REQ-WEB-006].
"""

import asyncio
import json
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.supervisor_orchestrator import SupervisorOrchestrator
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.observability.dashboard_service import ObservabilityDashboardService
from src.application.orchestration.directory_service import AgentDirectoryService
from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.application.routines.executor import RoutineExecutor
from src.application.routines.scheduler import RoutineScheduler
from src.application.settings.hardware_calculator import HardwareFitCalculator
from src.application.settings.settings_service import SettingsService
from src.application.skills.orchestration_skill import OrchestrationSkill
from src.application.telemetry.collector import TelemetryCollector
from src.domain.kernel.models import AgentTone, KernelEventType
from src.domain.observability.models import TelemetryFilter
from src.domain.orchestration.models import HandoffEnvelope
from src.domain.routines.manifests import BUILTIN_ROUTINES
from src.domain.settings.models import AgentCustomization, HardwareSpecs, MCPServerConfig, ModelPurposeMatrix
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.gateway.factory import GatewayProviderFactory
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class CreateSessionRequest(BaseModel):
    agent_id: str
    title: str = "New Chat"


class ChatStreamRequest(BaseModel):
    agent_id: str
    session_id: str
    content: str


class WikiExportRequest(BaseModel):
    title: str
    content: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    agent_id: str = "general-assistant"
    session_id: Optional[str] = None
    category: str = "03_Resources"
    tags: Optional[List[str]] = None


class HardwareFitQueryRequest(BaseModel):
    custom_ram_gb: Optional[float] = None
    custom_vram_gb: Optional[float] = None


class ProviderSettingsRequest(BaseModel):
    ollama_host: Optional[str] = "http://127.0.0.1:11434"
    openai_base_url: Optional[str] = "https://api.openai.com/v1"
    openai_api_key: Optional[str] = None
    default_provider_id: Optional[str] = "ollama"
    default_model_id: Optional[str] = "default"


class DecisionRequest(BaseModel):
    decision: str  # "APPROVED" or "REJECTED"
    reason: Optional[str] = None


class VerifiedChatRequest(BaseModel):
    agent_id: str
    session_id: str
    content: str
    verifier_tool: Optional[str] = None
    verifier_args: Optional[Dict[str, Any]] = None
    max_refinements: int = 3


class AuditAgentRequest(BaseModel):
    agent_id: str = "auditor-critic"
    session_id: str
    target_content: str


class GoalChatRequest(BaseModel):
    agent_id: str
    session_id: str
    goal: str


def create_app(
    state_store: Optional[SQLiteStateStore] = None,
    agent_registry: Optional[BuiltinAgentRegistry] = None,
    tool_registry: Optional[ScopedToolRegistry] = None,
    gateway_instance: Optional[MultiProviderGateway] = None,
    wiki_path: str = "./data/wiki",
) -> FastAPI:
    """Factory creating and configuring the AutoReiv FastAPI application."""
    # Initialize State & Telemetry
    store = state_store or SQLiteStateStore()
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)

    from src.application.observability.log_buffer import setup_system_logging
    log_buffer = setup_system_logging()

    if agent_registry and tool_registry:
        registry = agent_registry
        tool_reg = tool_registry
    else:
        registry, tool_reg = BuiltinAgentRegistry.bootstrap(
            store=store,
            telemetry=telemetry,
            wiki_root=wiki_path,
        )

    stored_providers = store.get_setting("provider_settings")
    if stored_providers and isinstance(stored_providers, dict) and not gateway_instance:
        cfg = dict(os.environ)
        if stored_providers.get("ollama_host"):
            cfg["OLLAMA_HOST"] = stored_providers["ollama_host"]
        if stored_providers.get("openai_base_url"):
            cfg["OPENAI_BASE_URL"] = stored_providers["openai_base_url"]
        if stored_providers.get("openai_api_key"):
            cfg["OPENAI_API_KEY"] = stored_providers["openai_api_key"]
        gateway = GatewayProviderFactory.create_gateway(config=cfg)
        if stored_providers.get("default_provider_id"):
            gateway.default_provider_id = stored_providers["default_provider_id"]
    else:
        gateway = gateway_instance or GatewayProviderFactory.from_env()
    hw_calc = HardwareFitCalculator()
    settings_service = SettingsService(
        state_store=store,
        gateway=gateway,
        agent_registry=registry,
        hardware_calc=hw_calc,
    )
    obs_service = ObservabilityDashboardService(state_store=store)

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=tool_reg,
        state_store=store,
        telemetry=telemetry,
    )
    directory_service = AgentDirectoryService(agent_registry=registry, state_store=store)
    handoff_engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=kernel,
    )
    orchestration_skill = OrchestrationSkill(
        directory_service=directory_service,
        handoff_engine=handoff_engine,
    )
    orchestration_skill.register_tools(tool_reg)

    orchestrator = SupervisorOrchestrator(
        agent_registry=registry,
        agent_kernel=kernel,
        telemetry=telemetry,
    )
    routine_executor = RoutineExecutor(
        agent_registry=registry,
        kernel=kernel,
        state_store=store,
        telemetry=telemetry,
    )

    scheduler = RoutineScheduler(
        executor=routine_executor,
        state_store=store,
        tick_interval_seconds=10.0,
    )

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        scheduler_task = asyncio.create_task(scheduler.start())
        try:
            yield
        finally:
            if hasattr(scheduler.stop, "__await__") or asyncio.iscoroutinefunction(scheduler.stop):
                await scheduler.stop()
            else:
                res = scheduler.stop()
                if asyncio.iscoroutine(res):
                    await res
            scheduler_task.cancel()
            try:
                await scheduler_task
            except (asyncio.CancelledError, Exception):
                pass

    app = FastAPI(
        title="AutoReiv Control Plane",
        description="Local-First Hybrid AI Agent Control Plane & Assistant Platform",
        version="0.8.0",
        lifespan=lifespan,
    )

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Seed default routines if empty
    for r in BUILTIN_ROUTINES:
        if not store.get_routine(r.id):
            store.save_routine(r)

    # Cache-Control headers for development and real-time updates
    @app.middleware("http")
    async def add_cache_control_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # Static Files and Templates setup
    base_web_dir = Path(__file__).parent
    static_dir = base_web_dir / "static"
    template_dir = base_web_dir / "templates"
    static_dir.mkdir(parents=True, exist_ok=True)
    template_dir.mkdir(parents=True, exist_ok=True)

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index_view():
        index_file = template_dir / "index.html"
        if index_file.exists():
            html_text = index_file.read_text(encoding="utf-8")
            timestamp = str(int(time.time()))
            html_text = re.sub(r"/static/app\.js(\?v=[^\"']*)?", f"/static/app.js?v={timestamp}", html_text)
            return HTMLResponse(
                content=html_text,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
        return HTMLResponse(content="<h1>AutoReiv Control Plane</h1><p>UI loading...</p>")

    # -------------------------------------------------------------
    # Agent Forge & Skill Catalog Endpoints [REQ-FORGE-003, REQ-FORGE-006]
    # -------------------------------------------------------------

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
        max_turns: Optional[int] = 10

    @app.get("/api/skills/catalog")
    async def get_skills_catalog():
        from src.application.skills.manifest import get_hierarchical_skills_catalog
        from src.domain.settings.models import ModelPurpose

        tools_def_list = tool_reg.list_tools()
        tools_list = [{"name": t.name, "description": t.description} for t in tools_def_list]
        skill_packs = get_hierarchical_skills_catalog(tools_def_list)

        return {
            "tools": tools_list,
            "skill_packs": skill_packs,
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

    @app.get("/api/agents")
    async def list_agents():
        profiles = registry.list_agents()
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "system_prompt": p.system_prompt,
                "purpose": p.purpose.value if hasattr(p.purpose, "value") else str(p.purpose),
                "tone": p.tone.value if hasattr(p.tone, "value") else str(p.tone),
                "avatar_icon": p.avatar_icon,
                "allowed_tools": p.allowed_tool_names,
                "allowed_tool_names": p.allowed_tool_names,
                "max_turns": p.max_turns,
                "model": p.model,
                "is_builtin": p.is_builtin,
            }
            for p in profiles
        ]

    @app.get("/api/agents/{agent_id}")
    async def get_agent_detail(agent_id: str):
        profile = registry.get_agent(agent_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
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
            "max_turns": profile.max_turns,
            "model": profile.model,
            "is_builtin": profile.is_builtin,
        }

    @app.post("/api/agents")
    async def create_agent(payload: AgentProfilePayload):
        import re

        from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError

        agent_id = (
            payload.id.strip()
            if payload.id
            else re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")
        )

        available_tools = {t.name for t in tool_reg.list_tools()}
        data = payload.model_dump()
        data["id"] = agent_id

        try:
            profile = AgentProfileGuardrail.validate(data, available_tools=available_tools)
        except AgentValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))

        registry.register_custom_agent(profile)
        return {"status": "created", "agent": profile.model_dump()}

    @app.put("/api/agents/{agent_id}")
    async def update_agent(agent_id: str, payload: AgentProfilePayload):
        from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError

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
        data["is_builtin"] = existing.is_builtin

        try:
            profile = AgentProfileGuardrail.validate(data, available_tools=available_tools)
        except AgentValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))

        if existing.is_builtin:
            from src.domain.settings.models import AgentCustomization

            customization = AgentCustomization(
                agent_id=agent_id,
                tone=profile.tone.value,
                system_prompt=profile.system_prompt,
                model=profile.model,
                allowed_tool_names=profile.allowed_tool_names,
                max_turns=profile.max_turns,
            )
            store.save_agent_override(customization)
        else:
            registry.register_custom_agent(profile)

        return {"status": "updated", "agent": profile.model_dump()}

    @app.delete("/api/agents/{agent_id}")
    async def delete_agent(agent_id: str):
        existing = registry.get_agent(agent_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
        if existing.is_builtin:
            raise HTTPException(status_code=400, detail="Cannot delete built-in baseline agent.")

        deleted = registry.delete_custom_agent(agent_id)
        if not deleted:
            raise HTTPException(status_code=400, detail=f"Failed to delete agent '{agent_id}'.")
        return {"status": "deleted", "id": agent_id}

    @app.get("/api/sessions")
    async def list_sessions(agent_id: Optional[str] = None):
        sessions = store.list_sessions(agent_id=agent_id)
        return [
            {
                "id": s.id,
                "agent_id": s.agent_id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sessions
        ]

    @app.post("/api/sessions")
    async def create_session(req: CreateSessionRequest):
        sess = store.create_session(agent_id=req.agent_id, title=req.title)
        return {
            "id": sess.id,
            "agent_id": sess.agent_id,
            "title": sess.title,
            "created_at": sess.created_at.isoformat(),
            "updated_at": sess.updated_at.isoformat(),
        }

    @app.get("/api/sessions/{session_id}/messages")
    async def get_session_messages(session_id: str):
        msgs = store.get_messages(session_id=session_id)
        return [
            {
                "role": m.role.value,
                "content": m.content,
                "name": m.name,
                "tool_calls": [tc.model_dump() for tc in m.tool_calls] if m.tool_calls else None,
                "tool_call_id": m.tool_call_id,
            }
            for m in msgs
        ]

    # -------------------------------------------------------------
    # Interactive Streaming Chat [REQ-WEB-001]
    # -------------------------------------------------------------

    @app.post("/api/chat/stream")
    async def chat_stream(req: ChatStreamRequest):
        profile = registry.get_profile(req.agent_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                async for event in kernel.stream_turn(profile, req.session_id, req.content):
                    if event.event_type == KernelEventType.TOKEN:
                        if event.reasoning_content:
                            data = json.dumps({"text": event.reasoning_content})
                            yield f"event: reasoning\ndata: {data}\n\n"
                        if event.content:
                            data = json.dumps({"text": event.content})
                            yield f"event: token\ndata: {data}\n\n"
                    elif event.event_type == KernelEventType.TOOL_START:
                        call_info = event.tool_call or {}
                        data = json.dumps(
                            {
                                "tool_name": call_info.get("name", ""),
                                "arguments": call_info.get("arguments", {}),
                            }
                        )
                        yield f"event: tool_start\ndata: {data}\n\n"
                    elif event.event_type == KernelEventType.TOOL_END:
                        out_text = event.tool_result.output if event.tool_result else ""
                        data = json.dumps(
                            {
                                "result": out_text,
                            }
                        )
                        yield f"event: tool_output\ndata: {data}\n\n"
                    elif event.event_type == KernelEventType.TURN_END:
                        data = json.dumps(
                            {
                                "content": event.content,
                            }
                        )
                        yield f"event: turn_done\ndata: {data}\n\n"
                    elif event.event_type == KernelEventType.ERROR:
                        data = json.dumps({"error": event.content})
                        yield f"event: error\ndata: {data}\n\n"
            except Exception as e:
                err_data = json.dumps({"error": str(e)})
                yield f"event: error\ndata: {err_data}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # -------------------------------------------------------------
    # One-Click Wiki Export [REQ-WEB-003, REQ-WIKI-008]
    # -------------------------------------------------------------

    @app.post("/api/export/wiki")
    async def export_to_wiki(req: WikiExportRequest):
        service = get_wiki_service()

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
        # Always default chat exports to inbox staging
        target_category = "inbox" if (not req.category or req.category in ("03_Resources", "01_Projects", "02_Areas", "inbox")) else req.category

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

    # -------------------------------------------------------------
    # Settings Studio Endpoints [REQ-WEB-004, REQ-SET-001, REQ-SET-006]
    # -------------------------------------------------------------

    @app.get("/api/settings/presets")
    async def get_settings_presets():
        from src.application.settings.presets import PROVIDER_PRESETS

        return {"presets": PROVIDER_PRESETS}

    @app.get("/api/settings")
    async def get_settings():
        matrix = settings_service.get_purpose_matrix()
        hw = hw_calc.get_hardware_specs()
        overrides = store.list_agent_overrides()
        providers_cfg = store.get_setting("provider_settings") or {
            "ollama_host": os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
            "openai_base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
            "default_provider_id": getattr(gateway, "default_provider_id", "ollama") or "ollama",
            "default_model_id": getattr(gateway, "default_model_id", "default") or "default",
        }
        return {
            "matrix": matrix.model_dump(),
            "hardware": hw.model_dump(),
            "providers": providers_cfg,
            "customizations": [c.model_dump() for c in overrides],
        }

    @app.post("/api/settings/providers")
    async def update_provider_settings(req: ProviderSettingsRequest):
        existing_cfg = store.get_setting("provider_settings") or {}
        merged_cfg = {**existing_cfg, **req.model_dump(exclude_unset=True)}
        store.set_setting("provider_settings", merged_cfg)

        from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
        from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter

        if req.ollama_host:
            gateway.register_provider(OllamaProviderAdapter(base_url=req.ollama_host, provider_id="ollama"))

        if req.openai_api_key or req.openai_base_url or (req.default_provider_id and req.default_provider_id != "ollama"):
            pid = req.default_provider_id if req.default_provider_id != "ollama" else "openai"
            gateway.register_provider(
                OpenAIProviderAdapter(
                    api_key=req.openai_api_key or "",
                    base_url=req.openai_base_url or "https://api.openai.com/v1",
                    provider_id=pid,
                )
            )

        if req.default_provider_id:
            gateway.default_provider_id = req.default_provider_id

        if req.default_model_id:
            gateway.default_model_id = req.default_model_id

        return {"status": "saved", "providers": merged_cfg}

    @app.post("/api/settings/matrix")
    async def update_purpose_matrix(data: Dict[str, Optional[str]]):
        matrix = ModelPurposeMatrix(**data)
        settings_service.save_purpose_matrix(matrix)
        return {"status": "updated", "matrix": matrix.model_dump()}

    @app.get("/api/models/discover")
    async def discover_models(
        provider_id: Optional[str] = None,
        host_url: Optional[str] = None,
        api_key: Optional[str] = None,
        available_ram_gib: Optional[float] = None,
    ):
        from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
        from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter

        gw = getattr(app.state, "gateway", gateway)
        pid = provider_id or getattr(gw, "default_provider_id", "ollama") or "ollama"

        if host_url:
            clean_host = host_url.strip()
            if pid == "ollama" or ":11434" in clean_host:
                adapter = OllamaProviderAdapter(base_url=clean_host, provider_id=pid)
                gw.register_provider(adapter)
            else:
                adapter = OpenAIProviderAdapter(base_url=clean_host, api_key=api_key or "", provider_id=pid)
                gw.register_provider(adapter)

        models = await gw.list_models(provider_id=pid)

        specs = None
        if available_ram_gib is not None:
            specs = HardwareSpecs(
                total_ram_gb=available_ram_gib,
                available_ram_gb=available_ram_gib,
            )

        discovered = []
        for m in models:
            if m.param_size_b:
                report = hw_calc.evaluate_fit(
                    param_size_b=m.param_size_b,
                    quantization=m.quantization or "Q4_K_M",
                    specs=specs,
                    model_id=m.id,
                )
                fit_status = report.fit_status.value
                est_ram = report.required_ram_gb
                notes = report.notes
            else:
                fit_status = "cloud" if m.provider != "ollama" else "runnable"
                est_ram = 0.0
                notes = "Cloud hosted model" if m.provider != "ollama" else "Local model"

            discovered.append(
                {
                    "id": m.id,
                    "name": m.name,
                    "provider": m.provider,
                    "param_size_b": m.param_size_b,
                    "quantization": m.quantization,
                    "family": m.family,
                    "estimated_ram_gb": est_ram,
                    "fit_status": fit_status,
                    "notes": notes,
                }
            )

        return {"models": discovered}

    @app.post("/api/settings/models/refresh")
    async def refresh_models(req: Optional[HardwareFitQueryRequest] = None):
        hw = None
        if req and (req.custom_ram_gb or req.custom_vram_gb):
            hw = HardwareSpecs(
                total_ram_gb=req.custom_ram_gb or 16.0,
                total_vram_gb=req.custom_vram_gb or 0.0,
                is_unified_memory=(req.custom_ram_gb is not None and req.custom_ram_gb >= 64.0),
            )
        reports = await settings_service.get_model_recommendations(specs_override=hw)
        return [r.model_dump() for r in reports]

    @app.post("/api/settings/agents/{agent_id}")
    async def customize_agent(agent_id: str, custom: AgentCustomization):
        custom.agent_id = agent_id
        store.save_agent_override(custom)
        return {"status": "saved", "customization": custom.model_dump()}

    # -------------------------------------------------------------
    # Observability & KPI Endpoints [REQ-WEB-005]
    # -------------------------------------------------------------

    @app.get("/api/observability/kpi")
    async def get_observability_kpis():
        overview = obs_service.get_overview_kpis()
        agents = obs_service.get_agent_breakdown()
        tools = obs_service.get_tool_reliability()
        timeline = obs_service.get_timeline(limit=24)
        return {
            "overview": overview.model_dump(),
            "agents": [a.model_dump() for a in agents],
            "tools": [t.model_dump() for t in tools],
            "timeline": [t.model_dump() for t in timeline],
        }

    @app.get("/api/observability/traces")
    async def get_observability_traces(
        agent_id: Optional[str] = None,
        has_error: Optional[bool] = None,
        limit: int = 50,
    ):
        flt = TelemetryFilter(agent_id=agent_id, has_error=has_error)
        spans = obs_service.get_traces(filter=flt, limit=limit)
        return [s.model_dump(mode="json") for s in spans]

    @app.get("/api/observability/logs")
    async def get_observability_logs(
        limit: int = 100,
        level: Optional[str] = None,
        query: Optional[str] = None,
    ):
        return log_buffer.get_logs(limit=limit, level=level, query=query)

    @app.post("/api/observability/logs/clear")
    async def clear_observability_logs():
        log_buffer.clear()
        return {"status": "success", "cleared": True}

    # -------------------------------------------------------------
    # Routine Engine & Trigger Endpoints [REQ-WEB-006, REQ-ROUT-001 - REQ-ROUT-003]
    # -------------------------------------------------------------

    class RoutinePayload(BaseModel):
        id: Optional[str] = None
        name: str
        description: Optional[str] = ""
        agent_id: str
        schedule_type: Optional[str] = "cron"
        cron_expr: Optional[str] = "0 * * * *"
        interval_seconds: Optional[int] = 3600
        prompt_template: str
        enabled: Optional[bool] = True

    @app.get("/api/routines")
    async def list_routines(agent_id: Optional[str] = None):
        from src.application.routines.humanizer import compute_next_run_eta, cron_to_human

        routines = store.list_routines(agent_id=agent_id)
        result = []
        for r in routines:
            if r.cron_expression:
                human_sched = cron_to_human(r.cron_expression)
                _, next_eta = compute_next_run_eta(r.cron_expression)
            else:
                human_sched = f"Every {r.interval_seconds}s"
                next_eta = f"in {r.interval_seconds // 60}m" if r.interval_seconds else "hourly"

            result.append(
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "agent_id": r.agent_id,
                    "prompt": r.prompt,
                    "schedule_type": r.schedule_type.value if hasattr(r.schedule_type, "value") else str(r.schedule_type),
                    "interval_seconds": r.interval_seconds,
                    "cron_expression": r.cron_expression,
                    "human_schedule": human_sched,
                    "next_run_eta": next_eta,
                    "enabled": r.enabled,
                    "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
                    "next_run_at": r.next_run_at.isoformat() if r.next_run_at else None,
                    "last_status": r.last_status.value if hasattr(r.last_status, "value") else str(r.last_status),
                }
            )
        return result

    @app.post("/api/routines")
    async def create_routine(payload: RoutinePayload):
        import re

        from src.domain.routines.models import Routine, RoutineStatus, ScheduleType

        routine_id = (
            payload.id.strip()
            if payload.id
            else re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")
        )

        sched_type = (
            ScheduleType(payload.schedule_type)
            if payload.schedule_type in [s.value for s in ScheduleType]
            else ScheduleType.CRON
        )

        routine = Routine(
            id=routine_id,
            name=payload.name,
            description=payload.description or "",
            agent_id=payload.agent_id,
            prompt=payload.prompt_template,
            schedule_type=sched_type,
            interval_seconds=payload.interval_seconds or 3600,
            cron_expression=payload.cron_expr or "0 * * * *",
            enabled=payload.enabled if payload.enabled is not None else True,
            last_status=RoutineStatus.IDLE,
        )

        store.save_routine(routine)
        return {"status": "created", "routine": routine.model_dump(mode="json")}

    @app.put("/api/routines/{routine_id}")
    async def update_routine(routine_id: str, payload: RoutinePayload):
        from src.domain.routines.models import Routine, ScheduleType

        existing = store.get_routine(routine_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Routine '{routine_id}' not found")

        sched_type = (
            ScheduleType(payload.schedule_type)
            if payload.schedule_type in [s.value for s in ScheduleType]
            else existing.schedule_type
        )

        routine = Routine(
            id=routine_id,
            name=payload.name or existing.name,
            description=payload.description if payload.description is not None else existing.description,
            agent_id=payload.agent_id or existing.agent_id,
            prompt=payload.prompt_template or existing.prompt,
            schedule_type=sched_type,
            interval_seconds=payload.interval_seconds or existing.interval_seconds,
            cron_expression=payload.cron_expr or existing.cron_expression,
            enabled=payload.enabled if payload.enabled is not None else existing.enabled,
            last_run_at=existing.last_run_at,
            next_run_at=existing.next_run_at,
            last_status=existing.last_status,
        )

        store.save_routine(routine)
        return {"status": "updated", "routine": routine.model_dump(mode="json")}

    @app.post("/api/routines/{routine_id}/toggle")
    async def toggle_routine(routine_id: str):
        new_state = store.toggle_routine(routine_id)
        if new_state is None:
            raise HTTPException(status_code=404, detail=f"Routine '{routine_id}' not found")
        return {"status": "toggled", "id": routine_id, "enabled": new_state}

    @app.delete("/api/routines/{routine_id}")
    async def delete_routine(routine_id: str):
        deleted = store.delete_routine(routine_id)
        if not deleted:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete routine '{routine_id}' (protected or not found).",
            )
        return {"status": "deleted", "id": routine_id}

    @app.post("/api/routines/{routine_id}/trigger")
    @app.post("/api/routines/{routine_id}/run")
    async def trigger_routine(routine_id: str):
        routine = store.get_routine(routine_id)
        if not routine:
            raise HTTPException(status_code=404, detail=f"Routine '{routine_id}' not found")
        run = await routine_executor.execute_routine(routine)
        return {
            "id": run.id,
            "routine_id": run.routine_id,
            "status": run.status.value,
            "output": run.output,
            "error_message": run.error_message,
            "duration_ms": run.duration_ms,
            "created_at": run.created_at.isoformat(),
        }

    # -------------------------------------------------------------
    # HITL Approvals & Stream Abort [REQ-SAFE-005, REQ-SAFE-006]
    # -------------------------------------------------------------

    @app.get("/api/approvals/pending")
    async def get_pending_approvals():
        return store.get_pending_approvals()

    @app.post("/api/approvals/{approval_id}/decision")
    async def resolve_approval_endpoint(approval_id: str, req: DecisionRequest):
        resolved = store.resolve_approval(
            approval_id=approval_id,
            decision=req.decision,
            reason=req.reason,
        )
        if not resolved:
            raise HTTPException(status_code=404, detail="Approval not found or already resolved")
        return {"status": req.decision.lower(), "approval_id": approval_id}

    @app.post("/api/chat/stream/{session_id}/abort")
    async def abort_stream_endpoint(session_id: str):
        # Record abort in telemetry
        telemetry.record_turn_span(
            agent_id="system",
            session_id=session_id,
            model="streaming",
            success=False,
            error_message="Stream aborted by user",
        )
        return {"status": "aborted", "session_id": session_id}

    # -------------------------------------------------------------
    # Multi-Agent Delegation [REQ-A2A-006]
    # -------------------------------------------------------------

    @app.post("/api/agents/delegate")
    async def delegate_agent_task(req: HandoffEnvelope):
        result = await orchestrator.dispatch_handoff(req)
        return result

    # -------------------------------------------------------------
    # MCP Server Configuration [REQ-MCP-006]
    # -------------------------------------------------------------

    @app.get("/api/mcp/servers")
    async def list_mcp_servers():
        servers = store.get_setting("mcp_servers")
        return servers if isinstance(servers, list) else []

    @app.post("/api/mcp/servers")
    async def save_mcp_server(req: MCPServerConfig):
        servers = store.get_setting("mcp_servers")
        if not isinstance(servers, list):
            servers = []
        existing_idx = next((i for i, s in enumerate(servers) if s.get("name") == req.name), None)
        server_dict = req.model_dump()
        if existing_idx is not None:
            servers[existing_idx] = server_dict
        else:
            servers.append(server_dict)
        store.set_setting("mcp_servers", servers)
        return {"status": "saved", "name": req.name}

    # -------------------------------------------------------------
    # Reflexive Verification & SRE Audit Endpoints [REQ-VERIFY-006]
    # -------------------------------------------------------------

    from src.application.kernel.plan_engine import PlanAndExecuteEngine
    from src.application.kernel.reflexion_engine import ReflexionLoopEngine

    reflexion_engine = ReflexionLoopEngine(kernel=kernel, tool_registry=tool_reg)
    plan_engine = PlanAndExecuteEngine(kernel=kernel)

    app.state.kernel = kernel
    app.state.gateway = gateway
    app.state.reflexion_engine = reflexion_engine
    app.state.plan_engine = plan_engine

    @app.post("/api/chat/verified")
    async def chat_verified(req: VerifiedChatRequest):
        profile = registry.get_profile(req.agent_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

        res = await app.state.reflexion_engine.run_reflexion_turn(
            agent=profile,
            session_id=req.session_id,
            user_content=req.content,
            verifier_tool_name=req.verifier_tool,
            verifier_args=req.verifier_args,
            max_refinements=req.max_refinements,
        )
        return res

    @app.post("/api/agents/audit")
    async def audit_agent_action(req: AuditAgentRequest):
        critic = registry.get_profile(req.agent_id or "auditor-critic")
        if not critic:
            raise HTTPException(status_code=404, detail=f"Auditor '{req.agent_id}' not found")

        audit_prompt = (
            "You are AutoReiv's Auditor Critic. Conduct a rigorous, adversarial review of the following proposed action or output:\n\n"
            f"{req.target_content}\n\n"
            "Provide: 1) Risk Score (1-10), 2) Challenged Assumptions, 3) Recommended Safety Guards."
        )

        reply = await app.state.kernel.run_turn(
            agent=critic,
            session_id=req.session_id,
            user_content=audit_prompt,
        )

        return {
            "status": "audited",
            "agent_id": critic.id,
            "session_id": req.session_id,
            "audit_report": reply.content,
        }

    # -------------------------------------------------------------
    # Plan-and-Execute Goal Mode Endpoint [REQ-PLAN-006]
    # -------------------------------------------------------------

    @app.post("/api/chat/goal")
    async def chat_goal(req: GoalChatRequest):
        profile = registry.get_profile(req.agent_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

        plan = await app.state.plan_engine.formulate_plan(
            agent=profile,
            goal=req.goal,
            session_id=req.session_id,
        )

        completed_plan, final_output = await app.state.plan_engine.execute_plan(
            plan=plan,
            agent=profile,
        )

        return {
            "status": "completed" if completed_plan.is_completed else "failed",
            "goal": req.goal,
            "plan": completed_plan.model_dump(),
            "output": final_output,
        }

    # -------------------------------------------------------------
    # System Information & Architecture Hub Endpoints [REQ-SYST-001]
    # -------------------------------------------------------------

    from src.application.web.system_info_service import SystemInfoService

    system_info_service = SystemInfoService()

    @app.get("/api/system-info/topics")
    async def get_system_info_topics():
        return {"categories": system_info_service.get_topics_index()}

    @app.get("/api/system-info/topic/{topic_id}")
    async def get_system_info_topic_content(topic_id: str):
        doc = system_info_service.get_topic_content(topic_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")
        return doc

    # -------------------------------------------------------------
    # Wiki Document Management Endpoints [REQ-WIKI-006]
    # -------------------------------------------------------------

    from src.application.wiki.service import WikiService

    def get_wiki_service() -> WikiService:
        if hasattr(app.state, "wiki_service"):
            return app.state.wiki_service
        return WikiService()

    @app.get("/api/wiki/tree")
    async def get_wiki_tree():
        service = get_wiki_service()
        return service.get_tree()

    @app.get("/api/wiki/note")
    async def get_wiki_note(path: str):
        service = get_wiki_service()
        res = service.get_note(path)
        if not res.get("success"):
            raise HTTPException(status_code=404, detail=res.get("error", f"Note '{path}' not found"))
        return res

    @app.post("/api/wiki/note")
    async def create_wiki_note(payload: Dict[str, Any]):
        service = get_wiki_service()
        res = service.create_note(**payload)
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res.get("error", "Failed to create note"))
        return res

    @app.put("/api/wiki/note")
    async def update_wiki_note(payload: Dict[str, Any]):
        service = get_wiki_service()
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

    @app.delete("/api/wiki/note")
    async def delete_wiki_note(path: str):
        service = get_wiki_service()
        deleted = service.delete_note(path)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Note '{path}' not found")
        return {"success": True, "path": path}

    @app.get("/api/wiki/search")
    async def search_wiki_notes(q: str, limit: int = 5):
        service = get_wiki_service()
        hits = service.search(query=q, limit=limit)
        return {"hits": hits, "query": q}

    @app.get("/api/wiki/graph")
    async def get_wiki_graph():
        service = get_wiki_service()
        return service.get_graph()

    @app.get("/api/wiki/mindmap")
    async def get_wiki_mindmap(
        include_tags: bool = True, include_taxonomy: bool = True
    ):
        service = get_wiki_service()
        return service.get_mindmap(
            include_tags=include_tags, include_taxonomy=include_taxonomy
        )

    @app.get("/api/wiki/overview")
    async def get_wiki_overview():
        service = get_wiki_service()
        return {"overview": service.get_overview()}

    @app.get("/api/wiki/stats")
    async def get_wiki_stats():
        service = get_wiki_service()
        return service.get_stats()

    # -------------------------------------------------------------
    # System Documentation & Specs Endpoints [REQ-SKIL-004]
    # -------------------------------------------------------------

    from src.application.web.system_docs_service import SystemDocumentationService

    docs_service = SystemDocumentationService()

    @app.get("/api/docs/nav")
    async def get_docs_navigation():
        return docs_service.get_navigation_tree()

    @app.get("/api/docs/content")
    async def get_doc_content(path: str):
        try:
            return docs_service.get_doc_content(path)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Document '{path}' not found")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return app
