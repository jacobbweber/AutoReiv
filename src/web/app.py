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
from src.application.gateway.generation_semaphore import configure_process_generation_limit
from src.application.hitl.approval_manager import ApprovalManager
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.plan_engine import PlanAndExecuteEngine
from src.application.kernel.reflexion_engine import ReflexionLoopEngine
from src.application.kernel.supervisor_orchestrator import SupervisorOrchestrator
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.observability.dashboard_service import ObservabilityDashboardService
from src.application.observability.log_buffer import setup_system_logging
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.routines.executor import RoutineExecutor
from src.application.routines.scheduler import RoutineScheduler
from src.application.sdlc.projects_service import ProjectsService
from src.application.settings.hardware_calculator import HardwareFitCalculator
from src.application.settings.settings_service import SettingsService
from src.application.telemetry.collector import TelemetryCollector
from src.application.wiki.service import WikiService
from src.domain.routines.manifests import BUILTIN_ROUTINES
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.data.resolver import bootstrap_data_dir
from src.infrastructure.gateway.factory import GatewayProviderFactory
from src.infrastructure.mcp.client_adapter import MCPClientManager
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.agents import router as agents_router
from src.web.routers.artifacts import router as artifacts_router
from src.web.routers.chat import router as chat_router
from src.web.routers.factory import router as factory_router
from src.web.routers.gaps import router as gaps_router
from src.web.routers.hitl import router as hitl_router
from src.web.routers.observability import router as observability_router
from src.web.routers.projects import router as projects_router
from src.web.routers.prompts import router as prompts_router
from src.web.routers.routines import router as routines_router
from src.web.routers.settings import router as settings_router
from src.web.routers.skills import router as skills_router
from src.web.routers.system import router as system_router
from src.web.routers.tones import router as tones_router
from src.web.routers.wiki import router as wiki_router
from src.web.routers.workflows import router as workflows_router

logger = logging.getLogger(__name__)


def create_app(
    state_store: Optional[SQLiteStateStore] = None,
    agent_registry: Optional[BuiltinAgentRegistry] = None,
    tool_registry: Optional[ScopedToolRegistry] = None,
    gateway_instance: Optional[MultiProviderGateway] = None,
    wiki_path: str = "./data/wiki",
) -> FastAPI:
    """Factory creating and configuring the AutoReiv FastAPI application."""
    # 1. State & Telemetry [REQ-DATA-001 - REQ-DATA-004]
    data_paths = bootstrap_data_dir(migrate=state_store is None)
    resolved_db_path = str(data_paths.db_path)
    legacy_wiki = {"./data/wiki", "data/wiki"}
    if wiki_path and wiki_path.replace("\\", "/") not in legacy_wiki:
        resolved_wiki_path = wiki_path
    else:
        resolved_wiki_path = str(data_paths.wiki_path)
    os.environ["AUTOREIV_DB_PATH"] = resolved_db_path
    os.environ["AUTOREIV_WIKI_PATH"] = resolved_wiki_path
    store = state_store or SQLiteStateStore(db_path=resolved_db_path)
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
            wiki_root=resolved_wiki_path,
            skills_dir=str(data_paths.skills_path),
        )

    # 3. LLM Gateway & Provider Resolution
    stored_providers = store.get_setting("provider_settings")
    if stored_providers and isinstance(stored_providers, dict) and not gateway_instance:
        cfg = dict(os.environ)
        for k, v in stored_providers.items():
            if v:
                cfg[k] = v
                cfg[k.upper()] = v
        gateway = GatewayProviderFactory.create_gateway(config=cfg)
        if stored_providers.get("default_provider_id"):
            gateway.default_provider_id = stored_providers["default_provider_id"]
        if stored_providers.get("default_model_id"):
            gateway.default_model_id = stored_providers["default_model_id"]
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
    try:
        _gen_cap = settings_service.get_purpose_matrix().max_concurrent_generations
        gateway.set_max_concurrent_generations(_gen_cap)
        configure_process_generation_limit(_gen_cap)
    except Exception:
        gateway.set_max_concurrent_generations(1)
        configure_process_generation_limit(1)
    obs_service = ObservabilityDashboardService(state_store=store)

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=tool_reg,
        state_store=store,
        telemetry=telemetry,
        hitl_engine=HITLApprovalEngine(store=store),
        data_dir=str(data_paths.root),
        user_skill_catalog=getattr(registry, "user_skill_catalog", None),
    )

    orchestrator = SupervisorOrchestrator(
        agent_registry=registry,
        agent_kernel=kernel,
        telemetry=telemetry,
    )
    if getattr(registry, "handoff_engine", None) is not None:
        registry.handoff_engine.kernel = kernel

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
    job_orchestrator = JobPhaseOrchestrator(store)
    wiki_service = WikiService(wiki_root=resolved_wiki_path)
    approval_manager = ApprovalManager()
    mcp_manager = MCPClientManager(tool_registry=tool_reg)

    # 4b. Factory Capability Loop Background Runner [REQ-FACT-016]
    from src.application.orchestration.capability_graph import CapabilityGraphEngine
    from src.application.orchestration.factory_runner import FactoryRunner
    from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository

    factory_repo = FactoryPacketRepository(store)
    factory_engine = CapabilityGraphEngine(factory_repo)
    factory_runner = FactoryRunner(
        repo=factory_repo,
        engine=factory_engine,
        store=store,
        data_dir=data_paths.root,
        poll_interval=2.0,
    )

    # 5. Lifespan Manager
    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        scheduler_task = asyncio.create_task(scheduler.start())
        factory_task = asyncio.create_task(factory_runner.start())
        try:
            for profile in registry.list_agents():
                days = profile.history_retention_days if profile.history_retention_days is not None else 30
                store.prune_expired_sessions(agent_id=profile.id, max_age_days=days)
        except Exception:
            logger.exception("Startup session retention prune failed")

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
            await factory_runner.stop()
            factory_task.cancel()
            try:
                await factory_task
            except (asyncio.CancelledError, Exception):
                pass
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
        version="0.15.0",
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
    app.state.job_orchestrator = job_orchestrator
    app.state.wiki_service = wiki_service
    app.state.wiki_path = resolved_wiki_path
    app.state.data_dir_paths = data_paths
    app.state.user_skill_catalog = getattr(registry, "user_skill_catalog", None)
    app.state.approval_manager = approval_manager
    projects_service = getattr(registry, "projects_service", None) or ProjectsService(store=store)
    app.state.projects_service = projects_service
    app.state.factory_runner = factory_runner
    app.state.factory_repo = factory_repo
    from src.infrastructure.memory.repositories.capability_gaps import CapabilityGapRepository
    app.state.capability_gap_repo = CapabilityGapRepository(store)

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
    app.include_router(factory_router)
    app.include_router(gaps_router)
    app.include_router(agents_router)
    app.include_router(workflows_router)
    app.include_router(skills_router)
    app.include_router(artifacts_router)
    app.include_router(wiki_router)
    app.include_router(projects_router)
    app.include_router(settings_router)
    app.include_router(routines_router)
    app.include_router(observability_router)
    app.include_router(hitl_router)
    app.include_router(system_router)
    app.include_router(tones_router)
    app.include_router(prompts_router)

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

