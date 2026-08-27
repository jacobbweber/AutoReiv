"""
AutoReiv Control Plane - Unified FastAPI Application Factory [REQ-WEB-001 - REQ-WEB-006].
"""

import asyncio
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.hitl.approval_manager import ApprovalManager
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.plan_engine import PlanAndExecuteEngine
from src.application.kernel.reflexion_engine import ReflexionLoopEngine
from src.application.kernel.supervisor_orchestrator import SupervisorOrchestrator
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.observability.dashboard_service import ObservabilityDashboardService
from src.application.observability.log_buffer import setup_system_logging
from src.application.routines.executor import RoutineExecutor
from src.application.routines.scheduler import RoutineScheduler
from src.application.settings.hardware_calculator import HardwareFitCalculator
from src.application.settings.settings_service import SettingsService
from src.application.skills.delegate_skill import DelegateSubtaskSkill
from src.application.telemetry.collector import TelemetryCollector
from src.application.wiki.service import WikiService
from src.domain.routines.manifests import BUILTIN_ROUTINES
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.gateway.factory import GatewayProviderFactory
from src.infrastructure.mcp.client_adapter import MCPClientManager
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.agents import router as agents_router
from src.web.routers.artifacts import router as artifacts_router
from src.web.routers.chat import router as chat_router
from src.web.routers.hitl import router as hitl_router
from src.web.routers.observability import router as observability_router
from src.web.routers.routines import router as routines_router
from src.web.routers.settings import router as settings_router
from src.web.routers.system import router as system_router
from src.web.routers.wiki import router as wiki_router

logger = logging.getLogger(__name__)


def create_app(
    state_store: Optional[SQLiteStateStore] = None,
    agent_registry: Optional[BuiltinAgentRegistry] = None,
    tool_registry: Optional[ScopedToolRegistry] = None,
    gateway_instance: Optional[MultiProviderGateway] = None,
    wiki_path: str = "./data/wiki",
) -> FastAPI:
    """Factory creating and configuring the AutoReiv FastAPI application."""
    # 1. State & Telemetry
    store = state_store or SQLiteStateStore()
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)
    log_buffer = setup_system_logging()

    # 2. Agent & Tool Registries
    if agent_registry and tool_registry:
        registry = agent_registry
        tool_reg = tool_registry
    else:
        registry, tool_reg = BuiltinAgentRegistry.bootstrap(
            store=store,
            telemetry=telemetry,
            wiki_root=wiki_path,
        )

    # 3. LLM Gateway & Provider Resolution
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

    # 4. Core Services & Orchestrators
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

    orchestrator = SupervisorOrchestrator(
        agent_registry=registry,
        agent_kernel=kernel,
        telemetry=telemetry,
    )
    delegate_skill = DelegateSubtaskSkill(
        current_agent_id="assistant",
        session_id="default_session",
        orchestrator=orchestrator,
    )
    delegate_skill.register_tools(tool_reg)

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

    reflexion_engine = ReflexionLoopEngine(kernel=kernel, tool_registry=tool_reg)
    plan_engine = PlanAndExecuteEngine(kernel=kernel)
    wiki_service = WikiService(wiki_root=wiki_path)
    approval_manager = ApprovalManager()
    mcp_manager = MCPClientManager(tool_registry=tool_reg)

    # 5. Lifespan Manager
    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        scheduler_task = asyncio.create_task(scheduler.start())

        # Auto-mount configured and enabled MCP servers [REQ-MCP-005]
        stored_mcp = store.get_setting("mcp_servers")
        if isinstance(stored_mcp, list):
            for s in stored_mcp:
                if s.get("enabled", True) and s.get("name") and s.get("command"):
                    try:
                        await mcp_manager.mount_server(
                            name=s["name"],
                            command=s["command"],
                            env=s.get("env"),
                        )
                    except Exception as e:
                        logger.warning(f"Failed to auto-mount MCP server '{s.get('name')}': {e}")

        try:
            yield
        finally:
            await mcp_manager.shutdown_all()
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

    # 6. Initialize FastAPI Application
    app = FastAPI(
        title="AutoReiv Control Plane",
        description="Local-First Hybrid AI Agent Control Plane & Assistant Platform",
        version="0.14.0",
        lifespan=lifespan,
    )

    # 7. Attach Core Singletons to app.state
    app.state.store = store
    app.state.telemetry = telemetry
    app.state.log_buffer = log_buffer
    app.state.registry = registry
    app.state.tool_reg = tool_reg
    app.state.mcp_manager = mcp_manager
    app.state.gateway = gateway
    app.state.hw_calc = hw_calc
    app.state.settings_service = settings_service
    app.state.obs_service = obs_service
    app.state.kernel = kernel
    app.state.orchestrator = orchestrator
    app.state.routine_executor = routine_executor
    app.state.scheduler = scheduler
    app.state.reflexion_engine = reflexion_engine
    app.state.plan_engine = plan_engine
    app.state.wiki_service = wiki_service
    app.state.wiki_path = wiki_path
    app.state.approval_manager = approval_manager

    # 8. Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_cache_control_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # 9. Seed Default Routines if empty
    for r in BUILTIN_ROUTINES:
        if not store.get_routine(r.id):
            store.save_routine(r)

    # 10. Mount Modular Domain Routers
    app.include_router(chat_router)
    app.include_router(agents_router)
    app.include_router(artifacts_router)
    app.include_router(wiki_router)
    app.include_router(settings_router)
    app.include_router(routines_router)
    app.include_router(observability_router)
    app.include_router(hitl_router)
    app.include_router(system_router)

    # 11. Static Files & Root Template View
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

    return app


app = create_app()
