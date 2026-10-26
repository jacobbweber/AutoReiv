"""
Application Ecosystem Bootstrapper [REQ-AGENTS-001, CARD-713].

Wires platform skills, tool groups, and the master ScopedToolRegistry into
BuiltinAgentRegistry inside the application layer so src/infrastructure/ does
not import upward into src/application/skills/*.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple, Type, Union

from src.application.agent_skills.tool_attachment import make_skill_write_guard
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.memory.agent_memory_tools import AgentMemoryTools
from src.application.orchestration.directory_service import AgentDirectoryService
from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.sdlc.paths import default_scratch_root
from src.application.sdlc.projects_service import ProjectsService
from src.application.skills.agent_builder_tools import AgentBuilderTools
from src.application.skills.agent_inspect_tools import AgentInspectTools
from src.application.skills.agent_storage_tools import AgentStorageTools
from src.application.skills.agora_loader import mount_all_enabled_skill_tools
from src.application.skills.card_handoff_tools import CardHandoffTools
from src.application.skills.card_review_tools import CardReviewTools
from src.application.skills.card_tools import CardTools
from src.application.skills.document_tools import DocumentTools
from src.application.skills.education_tools import EducationTools
from src.application.skills.git_tools import GitTools
from src.application.skills.github_issue_tools import GitHubIssueTools
from src.application.skills.journey_qa_tools import JourneyQaTools
from src.application.skills.mcp_engineering_tools import MCPEngineeringTools
from src.application.skills.native_tool_engineering import NativeToolEngineeringTools
from src.application.skills.orchestration_tools import OrchestrationTools
from src.application.skills.planning_tools import PlanningTools
from src.application.skills.platform_primitives import PlatformPrimitiveTools
from src.application.skills.project_dev_tools import ProjectDevTools
from src.application.skills.project_file_tools import ProjectFileTools
from src.application.skills.remote_tools import RemoteTools
from src.application.skills.repo_tools import RepoCheckoutTools
from src.application.skills.sandbox_tools import SandboxExecutionTools
from src.application.skills.sysadmin_tools import SysadminTools
from src.application.skills.system_agent_tools import SystemAgentTools
from src.application.skills.user_catalog import UserSkillCatalog
from src.application.skills.verification_tools import VerificationTools
from src.application.skills.web_tools import WebTools
from src.application.skills.wiki_tools import WikiTools
from src.application.skills.worker_tools import BatchWorkerTools
from src.domain.agents.profiles import BUILTIN_PROFILES
from src.infrastructure.content.store import configure, set_skill_write_guard, set_tool_registry
from src.infrastructure.data.resolver import LEGACY_WIKI_STRINGS, DataDirResolver

if TYPE_CHECKING:
    from src.application.telemetry.collector import TelemetryCollector
    from src.infrastructure.agents.registry import BuiltinAgentRegistry
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)


def bootstrap_ecosystem(
    store: "SQLiteStateStore",
    telemetry: "TelemetryCollector",
    wiki_root: Optional[Union[str, Path]] = None,
    skills_dir: Optional[str] = None,
    registry_cls: Optional[Type["BuiltinAgentRegistry"]] = None,
) -> Tuple["BuiltinAgentRegistry", ScopedToolRegistry]:
    """
    Bootstrap the agent ecosystem: platform skills, tool groups, and the master ScopedToolRegistry.
    Does not register agent-builder [CARD-429]. Builder HITL tools stay on the master registry
    for Developer.
    """
    if registry_cls is None:
        from src.infrastructure.agents.registry import BuiltinAgentRegistry as _RegistryCls

        registry_cls = _RegistryCls

    if wiki_root is None or str(wiki_root).strip() in LEGACY_WIKI_STRINGS:
        resolved_wiki_root = str(DataDirResolver().resolve().wiki_path)
    else:
        resolved_wiki_root = str(Path(wiki_root).resolve())
    tool_registry = ScopedToolRegistry()
    agent_registry = registry_cls(
        profiles=BUILTIN_PROFILES,
        state_store=store,
        master_tool_registry=tool_registry,
    )

    # CARD-570: agents and skills are files (platform/ in the repo, user copies in the data dir)
    data_root = Path(skills_dir).parent if skills_dir else None
    agent_registry._content = configure(data_root)

    # 0. Lean Platform Primitives (CARD-339, ADR-0052)
    platform_primitives = PlatformPrimitiveTools(state_store=store)
    platform_primitives.register_tools(tool_registry)

    # 1. Universal Wiki Tools -> Assistant, AutoReiv, Custom Agents
    wiki_tools = WikiTools(wiki_root=resolved_wiki_root)
    wiki_tools.register_tools(tool_registry)

    # 1b. Education Learning OS tools -> Tutor quiz/flashcard turns [CARD-438]
    education_tools = EducationTools(
        data_dir=data_root,
        wiki_root=resolved_wiki_root,
        default_agent_id="tutor",
    )
    education_tools.register_tools(tool_registry)

    # Spec-driven SDLC projects service for root resolution
    projects_service = ProjectsService(store=store)
    projects_service.register_tools(tool_registry)

    # 3. Linux Sysadmin Tools -> AutoReiv
    # CARD-558 D1 / CARD-562: no project selected -> OS-temp scratch folder, never the checkout.
    sysadmin_tools = SysadminTools(root_resolver=projects_service.selected_or_scratch)
    sysadmin_tools.register_tools(tool_registry)

    # 3b. Remote SSH Platform Tools -> AutoReiv
    remote_tools = RemoteTools(store=store)
    remote_tools.register_tools(tool_registry)

    # 4. Platform Diagnostics Tools -> AutoReiv
    system_tools = SystemAgentTools(store=store, telemetry=telemetry)
    system_tools.register_tools(tool_registry)

    # 5. Programmatic Verification Tools
    verify_tools = VerificationTools(store=store)
    verify_tools.register_tools(tool_registry)

    # 6. Goal & Planning Engine Tools
    planning_tools = PlanningTools()
    planning_tools.register_tools(tool_registry)

    # 7. Agent Builder Tools
    builder_tools = AgentBuilderTools(agent_registry=agent_registry, tool_registry=tool_registry, store=store)
    builder_tools.register_tools(tool_registry)

    # 7b. Read-only inspect_agent for the agent-authoring skill [CARD-569]
    AgentInspectTools(agent_registry=agent_registry).register_tools(tool_registry)

    # 8. Orchestration & Subagent Handoff Tools
    directory_service = AgentDirectoryService(agent_registry=agent_registry, state_store=store)
    handoff_engine = HandoffIsolationEngine(agent_registry=agent_registry, state_store=store)
    orch_tools = OrchestrationTools(
        directory_service=directory_service,
        handoff_engine=handoff_engine,
        store=store,
        orchestrator=JobPhaseOrchestrator(store),
    )
    orch_tools.register_tools(tool_registry)
    agent_registry.handoff_engine = handoff_engine
    agent_registry.orchestration_tools = orch_tools

    # 9. Batch Worker & Map-Reduce Tools
    worker_tools = BatchWorkerTools(state_store=store, wiki_tools=wiki_tools)
    worker_tools.register_tools(tool_registry)

    # 10. Sandbox Execution Tools (Coding skill ticks execute_code)
    sandbox_tools = SandboxExecutionTools()
    sandbox_tools.register_tools(tool_registry)

    # 10b. Document Reading & Extraction Tools [CARD-145]
    def _document_roots():
        # CARD-552: attachments/data folder, wiki vault, selected project, scratch - never the whole disk
        data_dir = data_root
        if data_dir is None:
            try:
                data_dir = DataDirResolver().resolve().root
            except Exception:
                data_dir = None
        try:
            project = projects_service.selected_root()
        except Exception:
            project = None
        return [data_dir, wiki_tools.wiki_root, project, default_scratch_root()]

    document_tools = DocumentTools(root_provider=_document_roots)
    document_tools.register_tools(tool_registry)

    # 11. Spec-driven SDLC cards / specs / steering
    card_tools = CardTools(root_resolver=projects_service.selected_or_refuse)  # CARD-562: no silent checkout
    card_tools.register_tools(tool_registry)

    # 12. Project-scoped file tools (jailed)
    # CARD-556 D1: no project selected -> <data root>/scratch, never the checkout.
    project_file_tools = ProjectFileTools(
        root_resolver=projects_service.selected_or_refuse,
        project_resolver=projects_service.selected_root,
    )  # CARD-562: scratch is <OS temp>/autoreiv-scratch
    project_file_tools.register_tools(tool_registry)

    # 12a. Checkout-jailed read-only repo tools [CARD-262]
    repo_tools = RepoCheckoutTools()
    repo_tools.register_tools(tool_registry)
    git_tools = GitTools(root_resolver=projects_service.selected_or_refuse)
    git_tools.register_tools(tool_registry)
    github_tools = GitHubIssueTools(
        root_resolver=projects_service.selected_or_refuse,
        card_tools=card_tools,
    )
    github_tools.register_tools(tool_registry)
    project_dev_tools = ProjectDevTools(
        root_resolver=projects_service.selected_or_refuse,
        card_tools=card_tools,
        selected_info=projects_service.get_selected,
    )
    project_dev_tools.register_tools(tool_registry)
    JourneyQaTools().register_tools(tool_registry)  # CARD-632: read CARD-532 journey reports
    agent_registry.projects_service = projects_service
    CardHandoffTools(  # CARD-563: Architect hands a Ready card to Developer
        root_resolver=projects_service.selected_or_refuse,
        card_tools=card_tools,
        handoff_engine=handoff_engine,
        agent_registry=agent_registry,
    ).register_tools(tool_registry)
    CardReviewTools(  # CARD-564: Architect reviews In Review cards (Done / Returned)
        root_resolver=projects_service.selected_or_refuse,
        card_tools=card_tools,
        dev_tools=project_dev_tools,
    ).register_tools(tool_registry)

    # 12b. Agent Private Storage Tools [CARD-148, REQ-STORAGE-003]
    storage_tools = AgentStorageTools(data_dir=data_root)
    storage_tools.register_tools(tool_registry)

    # 12b. Dedicated Cognitive Memory Brain Tools [CARD-116, CARD-405]
    memory_tools = AgentMemoryTools(data_dir=data_root)
    memory_tools.register_tools(tool_registry)

    # 12c. Enterprise MCP Engineering Tools [CARD-394, CARD-745]
    mcp_engineering_tools = MCPEngineeringTools(
        state_store=store,
        tool_registry=tool_registry,
        data_dir=data_root,
        root_resolver=projects_service.selected_root,
    )
    mcp_engineering_tools.register_tools(tool_registry)
    agent_registry.mcp_engineering_tools = mcp_engineering_tools

    native_tool_engineering = NativeToolEngineeringTools(
        state_store=store,
        tool_registry=tool_registry,
        agent_registry=agent_registry,
    )
    native_tool_engineering.register_tools(tool_registry)
    agent_registry.native_tool_engineering = native_tool_engineering

    # 12d. Web Search & Direct URL Fetch Tools [CARD-719]
    web_tools = WebTools(state_store=store)
    web_tools.register_tools(tool_registry)
    agent_registry.web_tools = web_tools

    # 13. User agentskills.io skills (CARD-104) [REQ-DATA-009 - REQ-DATA-011]
    catalog = UserSkillCatalog(skills_dir=skills_dir, tool_registry=tool_registry)
    catalog.agent_lookup = agent_registry.get_agent
    catalog.mount_at_bootstrap()
    agent_registry.user_skill_catalog = catalog

    # 13b. Mount enabled colocated Agora skill tools (skills/<id>/tools/*.py) [CARD-687, ADR-0065]
    mount_all_enabled_skill_tools(agent_registry._content, tool_registry)

    # 14. Validate skill tools: an unknown tool id is a warning and grants nothing [CARD-570]
    known = {t.name for t in tool_registry.list_tools()}
    set_tool_registry(tool_registry)
    set_skill_write_guard(make_skill_write_guard(store))  # agents cannot grant tools [CARD-570]
    agent_registry.skill_tool_warnings = agent_registry._content.validate_tools(known)
    for sid, names in agent_registry.skill_tool_warnings.items():
        logger.warning("Skill %s names unknown tools %s; they grant nothing.", sid, names)

    return agent_registry, tool_registry
