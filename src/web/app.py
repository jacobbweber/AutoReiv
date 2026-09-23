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
from src.application.system.backup_scheduler import DataDirBackupScheduler
from src.application.telemetry.collector import TelemetryCollector
from src.application.wiki.service import WikiService
from src.domain.routines.manifests import BUILTIN_ROUTINES
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.data.resolver import bootstrap_data_dir
from src.infrastructure.gateway.factory import GatewayProviderFactory
from src.infrastructure.mcp.client_adapter import MCPClientManager
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.agent_training_factory import router as factory_router
from src.web.routers.agents import router as agents_router
from src.web.routers.artifacts import router as artifacts_router
from src.web.routers.capabilities import router as capabilities_router
from src.web.routers.chat import router as chat_router
from src.web.routers.credentials import router as credentials_router
from src.web.routers.data_dir_migrate import router as data_dir_migrate_router
from src.web.routers.education import router as education_router
from src.web.routers.education_priming import router as education_priming_router
from src.web.routers.gaps import router as gaps_router
from src.web.routers.hitl import router as hitl_router
from src.web.routers.mcp_server import router as mcp_server_router
from src.web.routers.native_tools import router as native_tools_router
from src.web.routers.observability import router as observability_router
from src.web.routers.projects import router as projects_router
from src.web.routers.prompts import router as prompts_router
from src.web.routers.remote_hosts import router as remote_hosts_router
from src.web.routers.routines import router as routines_router
from src.web.routers.settings import router as settings_router
from src.web.routers.skill_authoring import router as skill_authoring_router
from src.web.routers.skills import router as skills_router
from src.web.routers.system import router as system_router
from src.web.routers.tones import router as tones_router
from src.web.routers.tools_authoring import router as tools_authoring_router
from src.web.routers.wiki import router as wiki_router

logger = logging.getLogger(__name__)


def create_app(
    state_store: Optional[SQLiteStateStore] = None,
    agent_registry: Optional[BuiltinAgentRegistry] = None,
    tool_registry: Optional[ScopedToolRegistry] = None,
    gateway_instance: Optional[MultiProviderGateway] = None,
    wiki_path: Optional[str] = None,
) -> FastAPI:
    """Factory creating and configuring the AutoReiv FastAPI application."""
    from src.application.orchestration.phase_llm_resilience import load_repo_dotenv

    load_repo_dotenv()

    # 1. State & Telemetry [REQ-DATA-001 - REQ-DATA-004]
    data_paths = bootstrap_data_dir(migrate=state_store is None)
    resolved_db_path = str(data_paths.db_path)
    from src.infrastructure.data.resolver import LEGACY_WIKI_STRINGS, wiki_is_explicitly_configured
    from src.infrastructure.data.wiki_gate import (
        WikiPathConfigurationError,
        enforce_wiki_path_for_boot,
        resolve_deploy_mode,
    )

    # Prefer caller wiki_path (tests), else env/durable setting.
    # Local + unset: adopt data_root/wiki (single folder); Docker/daemon still hard-fails.
    caller_wiki = bool(
        wiki_path and wiki_path.replace("\\", "/").strip() not in LEGACY_WIKI_STRINGS
    )
    env_wiki_before = (os.environ.get("AUTOREIV_WIKI_PATH") or "").strip() or None
    if caller_wiki:
        resolved_wiki_path = wiki_path
        os.environ["AUTOREIV_WIKI_PATH"] = resolved_wiki_path
    elif wiki_is_explicitly_configured():
        resolved_wiki_path = str(data_paths.wiki_path)
        os.environ["AUTOREIV_WIKI_PATH"] = resolved_wiki_path
    else:
        resolved_wiki_path = str(data_paths.wiki_path)
        # Leave unset until local adoption or docker hard-fail below.
        os.environ.pop("AUTOREIV_WIKI_PATH", None)

    os.environ["AUTOREIV_DB_PATH"] = resolved_db_path
    store = state_store or SQLiteStateStore(db_path=resolved_db_path)
    store.initialize_db()

    # ADR-0056 / CARD-414: Docker/daemon hard-fail if wiki missing; local may auto-adopt.
    setting_wiki = None
    try:
        raw_wiki_setting = store.get_setting("wiki_path")
        if isinstance(raw_wiki_setting, str) and raw_wiki_setting.strip():
            setting_wiki = raw_wiki_setting.strip()
            if not os.environ.get("AUTOREIV_WIKI_PATH"):
                os.environ["AUTOREIV_WIKI_PATH"] = setting_wiki
                resolved_wiki_path = setting_wiki
    except Exception:
        pass

    deploy_mode = resolve_deploy_mode()
    if (
        deploy_mode == "local"
        and not caller_wiki
        and not setting_wiki
        and not env_wiki_before
    ):
        adopted = str(data_paths.wiki_path)
        resolved_wiki_path = adopted
        os.environ["AUTOREIV_WIKI_PATH"] = adopted
        try:
            store.set_setting("wiki_path", adopted)
            setting_wiki = adopted
        except Exception:
            logger.warning("Could not persist local default wiki_path setting", exc_info=True)
        try:
            from src.infrastructure.data.resolver import DataDirResolver

            DataDirResolver().ensure_layout(data_paths, scaffold_wiki=True)
        except Exception:
            logger.warning("ensure_layout for local default wiki soft-failed", exc_info=True)
        try:
            from src.domain.wiki.store import WikiStore

            WikiStore(root_dir=adopted, auto_seed=False).scaffold(
                seed_starter=False, auto_migrate=False
            )
        except Exception:
            logger.warning("Local default wiki scaffold soft-failed", exc_info=True)

    try:
        wiki_status = enforce_wiki_path_for_boot(setting_wiki_path=setting_wiki)
    except WikiPathConfigurationError as exc:
        logger.error("Wiki path hard-fail (%s): %s", resolve_deploy_mode(), exc)
        raise

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

    # 3. LLM Gateway & Provider Resolution [CARD-211]
    stored_providers = store.get_setting("provider_settings")
    if stored_providers and isinstance(stored_providers, dict) and not gateway_instance:
        cfg = dict(os.environ)
        for k, v in stored_providers.items():
            if v and isinstance(v, (str, int, float, bool)):
                cfg[k] = v
                cfg[k.upper()] = v

        default_pid = stored_providers.get("default_provider_id", "ollama")

        # Automatic boot migration: legacy plaintext key into encrypted Credential Vault
        legacy_key = str(stored_providers.get("openai_api_key", "")).strip()
        if legacy_key and not legacy_key.startswith("••"):
            existing_cred = store.get_credential(f"llm-provider-{default_pid}")
            if not existing_cred or not existing_cred.secret:
                try:
                    from src.domain.security.vault import Credential

                    store.save_credential(
                        Credential(
                            id=f"llm-provider-{default_pid}",
                            name=f"LLM Provider: {default_pid}",
                            type="api_key",
                            secret=legacy_key,
                            description=f"Auto-migrated boot credential for {default_pid}",
                        )
                    )
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Boot vault migration failed: {e}")

        # Inject decrypted secrets from Credential Vault for all configured providers
        prov_map = stored_providers.get("providers") or {}
        p_ids = set(prov_map.keys()) | {default_pid}
        for p_id in p_ids:
            saved = prov_map.get(p_id) or {}
            target_cred_id = saved.get("vault_cred_id") or f"llm-provider-{p_id}"
            cred = store.get_credential(target_cred_id)
            if cred and cred.secret:
                cfg[f"{p_id.upper()}_API_KEY"] = cred.secret
                if p_id == default_pid:
                    cfg["OPENAI_API_KEY"] = cred.secret

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

    reflexion_engine = ReflexionLoopEngine(kernel=kernel, tool_registry=tool_reg)
    plan_engine = PlanAndExecuteEngine(kernel=kernel)
    from src.application.capabilities.resolver import CapabilityCatalogResolver
    from src.infrastructure.memory.repositories.capability_catalog import (
        CapabilityCatalogRepository,
    )
    from src.infrastructure.memory.repositories.capability_gaps import (
        CapabilityGapRepository,
    )
    capability_catalog_repo = CapabilityCatalogRepository(store)
    from src.application.capabilities.seeder import seed_builtin_capabilities

    seed_builtin_capabilities(
        repo=capability_catalog_repo,
        tool_registry=tool_reg,
        agent_registry=registry,
        user_skill_catalog=getattr(registry, "user_skill_catalog", None),
    )
    capability_catalog = CapabilityCatalogResolver(capability_catalog_repo)
    capability_gap_repo = CapabilityGapRepository(store)
    # Standing C runtime [CARD-220/222]: Chat + Routines multi-step use catalog resolve.
    # CARD-228: progressive SKILL.md — catalog resolve metadata-only; body on phase bind.
    _early_skill_catalog = getattr(registry, "user_skill_catalog", None)
    job_orchestrator = JobPhaseOrchestrator(
        store,
        capability_resolver=capability_catalog,
        data_dir=str(data_paths.root),
        skill_catalog=_early_skill_catalog,
    )
    # CARD-224: A2A handoff inherits standing path via linked child_job_id.
    if getattr(registry, "handoff_engine", None) is not None:
        registry.handoff_engine.job_orchestrator = job_orchestrator

    # CARD-222: Routines join standing Job/Phase path (cron remains trigger-only).
    routine_executor = RoutineExecutor(
        agent_registry=registry,
        kernel=kernel,
        state_store=store,
        telemetry=telemetry,
        job_orchestrator=job_orchestrator,
    )

    scheduler = RoutineScheduler(
        executor=routine_executor,
        state_store=store,
        tick_interval_seconds=10.0,
    )
    wiki_service = WikiService(wiki_root=resolved_wiki_path)
    approval_manager = ApprovalManager()
    mcp_manager = MCPClientManager(tool_registry=tool_reg)
    if hasattr(registry, "mcp_engineering_tools"):
        registry.mcp_engineering_tools.mcp_manager = mcp_manager

    from src.application.tools.native_packaging import NativeCustomToolService

    native_custom_tools = NativeCustomToolService(
        store=store,
        tool_registry=tool_reg,
        agent_registry=registry,
        policy_gate=kernel.tool_policy_gate,
        hitl_engine=kernel.hitl_engine,
        kernel=kernel,
    )
    if hasattr(registry, "native_tool_engineering"):
        registry.native_tool_engineering.service = native_custom_tools

    # 4b. Agent Training Factory Orchestrator [CARD-171, REQ-FACT-016]
    from src.application.agent_training_factory import FactoryOrchestrator
    from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository

    factory_repo = FactoryPacketRepository(store)
    factory_orchestrator = FactoryOrchestrator(
        repo=factory_repo,
        store=store,
        data_dir=data_paths.root,
        poll_interval=2.0,
        gateway=gateway,
        wiki=wiki_service,
    )

    backup_scheduler = DataDirBackupScheduler(
        paths=data_paths,
        store=store,
        interval_seconds=60.0,
    )

    # 5. Lifespan Manager
    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        scheduler_task = asyncio.create_task(scheduler.start())
        factory_task = asyncio.create_task(factory_orchestrator.start())
        backup_task = asyncio.create_task(backup_scheduler.start())
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

        # Auto-mount per-agent configured and enabled MCP servers [CARD-183, CARD-184]
        try:
            for profile in registry.list_agents():
                for srv in getattr(profile, "mcp_servers", []) or []:
                    s_dict = srv.model_dump() if hasattr(srv, "model_dump") else (srv if isinstance(srv, dict) else {})
                    if s_dict.get("enabled", True) and s_dict.get("name"):
                        try:
                            await mcp_manager.mount_server(
                                name=s_dict["name"],
                                command=s_dict.get("command"),
                                env=s_dict.get("env"),
                                transport=s_dict.get("transport", "stdio"),
                                url=s_dict.get("url"),
                                headers=s_dict.get("headers"),
                            )
                        except Exception as e:
                            logger.warning(f"Failed to auto-mount agent '{profile.id}' MCP server '{s_dict.get('name')}': {e}")
        except Exception as e:
            logger.warning(f"Per-agent MCP server auto-mount scan failed: {e}")

        try:
            native_custom_tools.mount_persisted()
        except Exception:
            logger.exception("Native custom tool remount failed")

        try:
            yield
        finally:
            await backup_scheduler.stop()
            backup_task.cancel()
            try:
                await backup_task
            except (asyncio.CancelledError, Exception):
                pass
            await mcp_manager.shutdown_all()
            await factory_orchestrator.stop()
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
        version="0.36.0",
        lifespan=lifespan,
    )

    # 7. Attach Core Singletons to app.state
    app.state.store = store
    app.state.telemetry = telemetry
    app.state.log_buffer = log_buffer
    app.state.registry = registry
    app.state.tool_reg = tool_reg
    app.state.tool_registry = tool_reg
    app.state.mcp_manager = mcp_manager
    app.state.native_custom_tools = native_custom_tools
    app.state.gateway = gateway
    app.state.hw_calc = hw_calc
    app.state.settings_service = settings_service
    app.state.obs_service = obs_service
    app.state.kernel = kernel
    app.state.orchestrator = orchestrator
    app.state.routine_executor = routine_executor
    app.state.scheduler = scheduler
    app.state.backup_scheduler = backup_scheduler
    app.state.reflexion_engine = reflexion_engine
    app.state.plan_engine = plan_engine
    app.state.job_orchestrator = job_orchestrator
    app.state.wiki_service = wiki_service
    app.state.wiki_path = resolved_wiki_path
    try:
        app.state.wiki_status = wiki_status
        app.state.deploy_mode = resolve_deploy_mode()
    except NameError:
        app.state.wiki_status = None
        app.state.deploy_mode = "local"
    app.state.data_dir_paths = data_paths
    app.state.user_skill_catalog = getattr(registry, "user_skill_catalog", None)
    app.state.approval_manager = approval_manager
    projects_service = getattr(registry, "projects_service", None) or ProjectsService(store=store)
    app.state.projects_service = projects_service
    app.state.factory_orchestrator = factory_orchestrator
    app.state.factory_repo = factory_repo
    app.state.capability_gap_repo = capability_gap_repo
    app.state.capability_catalog_repo = capability_catalog_repo
    app.state.capability_catalog = capability_catalog

    if not store.get_setting("tool_policy"):
        store.set_setting(
            "tool_policy",
            {
                "block_tools": [],
                "require_confirm_tools": [],
                "safe_tools": [],
            },
        )

    from pathlib import Path as _Path

    from src.application.capabilities.scaffold_spine import SelfScaffoldSpine
    from src.application.skills.user_catalog import UserSkillCatalog
    from src.infrastructure.memory.repositories.scaffold_spine import ScaffoldSpineRepository
    _data_dir = getattr(app.state, "data_dir", None)
    if _data_dir is None:
        _settings = getattr(app.state, "settings", None)
        _data_dir = getattr(_settings, "data_dir", None) if _settings else None
    if _data_dir:
        _skills = _Path(_data_dir) / "skills"
    else:
        from src.infrastructure.data.resolver import DataDirResolver as _DDR

        _skills = _Path(_DDR().resolve().root) / "skills"
    _catalog = getattr(app.state, "user_skill_catalog", None) or UserSkillCatalog(skills_dir=_skills)
    app.state.user_skill_catalog = _catalog
    try:
        job_orchestrator._skill_catalog = _catalog
    except NameError:
        orch_state = getattr(app.state, "job_orchestrator", None)
        if orch_state is not None:
            orch_state._skill_catalog = _catalog
    app.state.scaffold_spine = SelfScaffoldSpine(
        spine_repo=ScaffoldSpineRepository(store),
        capability_repo=app.state.capability_catalog_repo,
        catalog=_catalog,
    )

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

    # 9. Seed / Sync Default Routines
    from src.application.routines.matcher import ScheduleMatcher

    for r in BUILTIN_ROUTINES:
        existing_r = store.get_routine(r.id)
        if not existing_r:
            if r.next_run_at is None:
                r.next_run_at = ScheduleMatcher.compute_next_run(r)
            store.save_routine(r)
        else:
            updated = False
            if existing_r.agent_id in ("assistant", "wiki"):
                existing_r.agent_id = r.agent_id
                updated = True
            if existing_r.next_run_at is None and existing_r.last_run_at is None:
                existing_r.next_run_at = ScheduleMatcher.compute_next_run(existing_r)
                updated = True
            if updated:
                store.save_routine(existing_r)
    store.set_setting("day1_routines_seeded", True)

    # 10. Mount Modular Domain Routers
    app.include_router(chat_router)
    app.include_router(factory_router)
    app.include_router(gaps_router)
    app.include_router(agents_router)
    app.include_router(skills_router)
    app.include_router(skill_authoring_router)
    app.include_router(tools_authoring_router)
    app.include_router(native_tools_router)
    app.include_router(artifacts_router)
    app.include_router(wiki_router)
    app.include_router(education_router)
    app.include_router(education_priming_router)
    app.include_router(projects_router)
    app.include_router(settings_router)
    app.include_router(data_dir_migrate_router)  # CARD-313 honest migrate
    app.include_router(routines_router)
    app.include_router(observability_router)
    app.include_router(capabilities_router)
    app.include_router(hitl_router)
    app.include_router(system_router)
    app.include_router(tones_router)
    app.include_router(prompts_router)
    app.include_router(credentials_router)
    app.include_router(remote_hosts_router)
    app.include_router(mcp_server_router)

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

