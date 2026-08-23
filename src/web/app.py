"""
AutoReiv Control Plane - Unified FastAPI Application [REQ-WEB-001 - REQ-WEB-006].
"""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.observability.dashboard_service import ObservabilityDashboardService
from src.application.routines.executor import RoutineExecutor
from src.application.routines.scheduler import RoutineScheduler
from src.application.settings.hardware_calculator import HardwareFitCalculator
from src.application.settings.settings_service import SettingsService
from src.application.telemetry.collector import TelemetryCollector
from src.application.web.wiki_export_service import WikiExportService
from src.domain.kernel.models import KernelEventType
from src.domain.observability.models import TelemetryFilter
from src.domain.routines.manifests import BUILTIN_ROUTINES
from src.domain.settings.models import AgentCustomization, HardwareSpecs, ModelPurposeMatrix
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

    if agent_registry and tool_registry:
        registry = agent_registry
        tool_reg = tool_registry
    else:
        registry, tool_reg = BuiltinAgentRegistry.bootstrap(
            store=store,
            telemetry=telemetry,
            wiki_root=wiki_path,
        )

    wiki_service = WikiExportService(base_wiki_path=wiki_path)
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
            scheduler.stop()
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
            return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>AutoReiv Control Plane</h1><p>UI loading...</p>")

    # -------------------------------------------------------------
    # Agent & Session Endpoints [REQ-WEB-002]
    # -------------------------------------------------------------

    @app.get("/api/agents")
    async def list_agents():
        profiles = registry.list_profiles()
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "tone": p.tone.value,
                "allowed_tools": p.allowed_tool_names,
                "max_turns": p.max_turns,
                "model": p.model,
            }
            for p in profiles
        ]

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
    # One-Click Wiki Export [REQ-WEB-003]
    # -------------------------------------------------------------

    @app.post("/api/export/wiki")
    async def export_to_wiki(req: WikiExportRequest):
        if req.messages:
            res = wiki_service.export_session(
                title=req.title,
                messages=req.messages,
                agent_id=req.agent_id,
                session_id=req.session_id,
                category=req.category,
                tags=req.tags,
            )
        else:
            res = wiki_service.export_message(
                title=req.title,
                content=req.content or "",
                agent_id=req.agent_id,
                session_id=req.session_id,
                category=req.category,
                tags=req.tags,
            )
        return res

    # -------------------------------------------------------------
    # Settings Studio Endpoints [REQ-WEB-004]
    # -------------------------------------------------------------

    @app.get("/api/settings")
    async def get_settings():
        matrix = settings_service.get_purpose_matrix()
        hw = hw_calc.get_hardware_specs()
        overrides = store.list_agent_overrides()
        return {
            "matrix": matrix.model_dump(),
            "hardware": hw.model_dump(),
            "customizations": [c.model_dump() for c in overrides],
        }

    @app.post("/api/settings/matrix")
    async def update_purpose_matrix(data: Dict[str, Optional[str]]):
        matrix = ModelPurposeMatrix(**data)
        settings_service.save_purpose_matrix(matrix)
        return {"status": "updated", "matrix": matrix.model_dump()}

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

    # -------------------------------------------------------------
    # Routine Engine & Trigger Endpoints [REQ-WEB-006]
    # -------------------------------------------------------------

    @app.get("/api/routines")
    async def list_routines():
        routines = store.list_routines()
        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "agent_id": r.agent_id,
                "schedule_type": r.schedule_type.value,
                "interval_seconds": r.interval_seconds,
                "cron_expression": r.cron_expression,
                "enabled": r.enabled,
                "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
                "next_run_at": r.next_run_at.isoformat() if r.next_run_at else None,
                "last_status": r.last_status.value,
            }
            for r in routines
        ]

    @app.post("/api/routines/{routine_id}/trigger")
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

    return app
