"""
Built-in Agent Registry & Bootstrapper [REQ-AGENTS-001].
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.education_tools import EducationTools
from src.application.skills.sysadmin_tools import SysadminTools
from src.application.skills.system_agent_tools import SystemAgentTools
from src.application.skills.wiki_tools import WikiTools
from src.application.telemetry.collector import TelemetryCollector
from src.domain.agents.profiles import (
    BUILTIN_PROFILES,
    RETIRED_LIVE_AGENT_IDS,
    canonical_agent_id,
    get_builtin_profile,
)
from src.domain.kernel.models import AgentProfile
from src.infrastructure.agents.agent_files import (
    MODEL_FIELDS,
    MODEL_SETTINGS_KEY,
    meta_from_profile,
    model_settings_from_profile,
    profile_from_file,
)
from src.infrastructure.content.store import ContentStore, get_store
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)


class BuiltinAgentRegistry:
    """
    Registry of agent profiles. Agents are files [CARD-570]: shipped ``platform/agents/<id>.md``
    read in place, user copies in data ``agents/<id>.md`` win by id. Per-agent model/provider are
    separate settings. In-memory profiles (tests, BUILTIN_PROFILES) are a fallback only.
    agent-builder is retired [CARD-429] and is never registered.
    """

    def __init__(
        self,
        profiles: Optional[List[AgentProfile]] = None,
        state_store: Optional[SQLiteStateStore] = None,
        master_tool_registry: Optional[ScopedToolRegistry] = None,
        content_store: Optional[ContentStore] = None,
    ):
        self._profiles: Dict[str, AgentProfile] = {}
        self.state_store = state_store
        self.master_tool_registry = master_tool_registry or ScopedToolRegistry()
        self._content = content_store

        source = BUILTIN_PROFILES if profiles is None else profiles
        for p in source:
            self.register_profile(p)

    @property
    def content(self) -> ContentStore:
        return self._content if self._content is not None else get_store()

    # model settings ----------------------------------------------------------------------------
    def model_settings(self, agent_id: str) -> dict:
        if not self.state_store or not hasattr(self.state_store, "get_setting"):
            return {}
        raw = self.state_store.get_setting(MODEL_SETTINGS_KEY) or {}
        entry = raw.get(agent_id) if isinstance(raw, dict) else None
        return dict(entry) if isinstance(entry, dict) else {}

    def save_model_settings(self, agent_id: str, values: dict) -> None:
        if not self.state_store or not hasattr(self.state_store, "set_setting"):
            return
        raw = self.state_store.get_setting(MODEL_SETTINGS_KEY) or {}
        raw = dict(raw) if isinstance(raw, dict) else {}
        clean = {k: v for k, v in (values or {}).items() if k in MODEL_FIELDS and v not in (None, "")}
        if clean:
            raw[agent_id] = clean
        else:
            raw.pop(agent_id, None)
        self.state_store.set_setting(MODEL_SETTINGS_KEY, raw)

    # writes ------------------------------------------------------------------------------------
    def register_profile(self, profile: AgentProfile) -> None:
        if profile.id in RETIRED_LIVE_AGENT_IDS:
            return
        self._profiles[profile.id] = profile

    def register_custom_agent(self, profile: AgentProfile) -> None:
        """Save the full agent file (user copy) and its model settings. No field merging."""
        self.save_agent(profile)

    def save_agent(self, profile: AgentProfile, *, create: bool = False) -> AgentProfile:
        """Write data ``agents/<id>.md``. ``create`` refuses shipped (reserved) and existing ids."""
        if profile.id in RETIRED_LIVE_AGENT_IDS:
            raise ValueError(f"'{profile.id}' is retired.")
        meta, body = meta_from_profile(profile)
        if self.content.data_root is None:
            self._profiles[profile.id] = profile  # no data dir (unit tests): memory only
        else:
            self.content.agents.save(profile.id, meta, body, create=create)
        self.save_model_settings(profile.id, model_settings_from_profile(profile))
        return self.get_agent(profile.id) or profile

    def apply_customization(self, custom) -> AgentProfile:
        """Apply the set fields of an AgentCustomization and save (full copy; model fields to settings)."""
        existing = self.get_agent(custom.agent_id)
        if existing is None:
            raise LookupError(custom.agent_id)
        update = {
            k: v
            for k, v in custom.model_dump(exclude={"agent_id", "user_modified"}).items()
            if v is not None and k in AgentProfile.model_fields
        }
        profile = AgentProfile.model_validate({**existing.model_dump(), **update})
        return self.save_agent(profile)

    def use_shipped_version(self, agent_id: str) -> bool:
        """Delete the user copy of a shipped agent. Model settings are kept."""
        return self.content.agents.use_shipped(agent_id)

    def delete_custom_agent(self, agent_id: str, purge_history: bool = False) -> bool:
        """Shipped agent -> hidden (persisted); user-created -> file removed."""
        if agent_id in ("agent-builder", "autoreiv"):
            return False
        in_memory = self._profiles.pop(agent_id, None) is not None
        outcome = self.content.agents.delete(agent_id)
        if purge_history and self.state_store and hasattr(self.state_store, "delete_agent_history"):
            try:
                self.state_store.delete_agent_history(agent_id)
            except Exception:
                pass
        return in_memory or outcome in ("hidden", "deleted")

    def unhide_agent(self, agent_id: str) -> bool:
        return self.content.agents.unhide(agent_id)

    def agent_file_status(self, agent_id: str) -> dict:
        loaded = self.content.agents.load(agent_id, include_hidden=True)
        if loaded is None:
            return {"source": "memory", "shipped": False, "edited": False, "shipped_changed": False, "warnings": []}
        status = loaded.status()
        status["hidden"] = agent_id in self.content.agents.hidden()
        return status

    # reads -------------------------------------------------------------------------------------
    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Agent file (user copy wins), else an in-memory profile; alias fallback."""
        raw = (agent_id or "").strip()
        if raw in RETIRED_LIVE_AGENT_IDS or canonical_agent_id(raw) in RETIRED_LIVE_AGENT_IDS:
            return None
        for lookup in dict.fromkeys([raw, canonical_agent_id(raw)]):
            if not lookup:
                continue
            loaded = self.content.agents.load(lookup)
            if loaded is not None:
                return profile_from_file(loaded, self.model_settings(lookup))
            if lookup in self.content.agents.hidden() and self.content.agents.shipped_path(lookup).is_file():
                return None
            profile = self._profiles.get(lookup) or get_builtin_profile(lookup)
            if profile is not None:
                settings = self.model_settings(lookup)
                return profile.model_copy(update=settings) if settings else profile
        return None

    def get_profile(self, agent_id: str) -> Optional[AgentProfile]:
        return self.get_agent(agent_id)

    def list_agents(self) -> List[AgentProfile]:
        """Every visible agent: files (shipped + user), then in-memory profiles."""
        ids: list[str] = [f.id for f in self.content.agents.list()]
        ids += [p.id for p in BUILTIN_PROFILES] + list(self._profiles)
        result: List[AgentProfile] = []
        for aid in dict.fromkeys(ids):
            if aid in RETIRED_LIVE_AGENT_IDS:
                continue
            ag = self.get_agent(aid)
            if ag is not None and ag.id not in {r.id for r in result}:
                result.append(ag)
        return result

    def list_profiles(self) -> List[AgentProfile]:
        return self.list_agents()

    @classmethod
    def bootstrap(
        cls,
        store: SQLiteStateStore,
        telemetry: TelemetryCollector,
        wiki_root: Optional[Union[str, Path]] = None,
        skills_dir: Optional[str] = None,
    ) -> Tuple["BuiltinAgentRegistry", ScopedToolRegistry]:
        """
        Bootstrap the agent ecosystem: platform packs, tool groups, and the master ScopedToolRegistry.
        Does not register agent-builder [CARD-429]. Builder HITL tools stay on the master registry
        for Developer.
        """
        from src.infrastructure.data.resolver import LEGACY_WIKI_STRINGS, DataDirResolver

        if wiki_root is None or str(wiki_root).strip() in LEGACY_WIKI_STRINGS:
            resolved_wiki_root = str(DataDirResolver().resolve().wiki_path)
        else:
            resolved_wiki_root = str(Path(wiki_root).resolve())
        tool_registry = ScopedToolRegistry()
        agent_registry = cls(
            profiles=BUILTIN_PROFILES,
            state_store=store,
            master_tool_registry=tool_registry,
        )

        # CARD-570: agents and skills are files (platform/ in the repo, user copies in the data dir)
        data_root = Path(skills_dir).parent if skills_dir else None
        from src.infrastructure.content.store import configure

        agent_registry._content = configure(data_root)

        # 0. Lean Platform Primitives (CARD-339, ADR-0052)
        from src.application.skills.platform_primitives import PlatformPrimitiveTools

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
        from src.application.sdlc.projects_service import ProjectsService

        projects_service = ProjectsService(store=store)
        projects_service.register_tools(tool_registry)

        # 3. Linux Sysadmin Tools -> AutoReiv
        # CARD-558 D1 / CARD-562: no project selected -> OS-temp scratch folder, never the checkout.
        sysadmin_tools = SysadminTools(root_resolver=projects_service.selected_or_scratch)
        sysadmin_tools.register_tools(tool_registry)

        # 3b. Remote SSH Platform Tools -> AutoReiv
        from src.application.skills.remote_tools import RemoteTools

        remote_tools = RemoteTools(store=store)
        remote_tools.register_tools(tool_registry)

        # 4. Platform Diagnostics Tools -> AutoReiv
        system_tools = SystemAgentTools(store=store, telemetry=telemetry)
        system_tools.register_tools(tool_registry)

        # 5. Programmatic Verification Tools
        from src.application.skills.verification_tools import VerificationTools

        verify_tools = VerificationTools(store=store)
        verify_tools.register_tools(tool_registry)

        # 6. Goal & Planning Engine Tools
        from src.application.skills.planning_tools import PlanningTools

        planning_tools = PlanningTools()
        planning_tools.register_tools(tool_registry)

        # 7. Agent Builder Tools
        from src.application.skills.agent_builder_tools import AgentBuilderTools

        builder_tools = AgentBuilderTools(agent_registry=agent_registry, tool_registry=tool_registry, store=store)
        builder_tools.register_tools(tool_registry)

        # 7b. Read-only inspect_agent for the agent-authoring skill [CARD-569]
        from src.application.skills.agent_inspect_tools import AgentInspectTools

        AgentInspectTools(agent_registry=agent_registry).register_tools(tool_registry)

        # 8. Orchestration & Subagent Handoff Tools
        from src.application.orchestration.directory_service import AgentDirectoryService
        from src.application.orchestration.handoff_engine import HandoffIsolationEngine
        from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
        from src.application.skills.orchestration_tools import OrchestrationTools

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

        # 9. Batch Worker & Map-Reduce Tools
        from src.application.skills.worker_tools import BatchWorkerTools

        worker_tools = BatchWorkerTools(state_store=store, wiki_tools=wiki_tools)
        worker_tools.register_tools(tool_registry)

        # 10. Sandbox Execution Tools (Coding pack ticks execute_code)
        from src.application.skills.sandbox_tools import SandboxExecutionTools

        sandbox_tools = SandboxExecutionTools()
        sandbox_tools.register_tools(tool_registry)

        # 10b. Document Reading & Extraction Tools [CARD-145]
        from src.application.skills.document_tools import DocumentTools

        document_tools = DocumentTools()
        document_tools.register_tools(tool_registry)

        # 11. Spec-driven SDLC cards / specs / steering
        from src.application.skills.card_tools import CardTools

        card_tools = CardTools(root_resolver=projects_service.selected_or_refuse)  # CARD-562: no silent checkout
        card_tools.register_tools(tool_registry)

        # 12. Project-scoped file tools (jailed)
        from src.application.skills.project_file_tools import ProjectFileTools

        # CARD-556 D1: no project selected -> <data root>/scratch, never the checkout.
        project_file_tools = ProjectFileTools(
            root_resolver=projects_service.selected_or_refuse,
            project_resolver=projects_service.selected_root,
        )  # CARD-562: scratch is <OS temp>/autoreiv-scratch
        project_file_tools.register_tools(tool_registry)

        # 12a. Checkout-jailed read-only repo tools [CARD-262]
        from src.application.skills.repo_tools import RepoCheckoutTools

        repo_tools = RepoCheckoutTools()
        repo_tools.register_tools(tool_registry)
        from src.application.skills.git_tools import GitTools

        git_tools = GitTools(root_resolver=projects_service.selected_or_refuse)
        git_tools.register_tools(tool_registry)
        from src.application.skills.github_issue_tools import GitHubIssueTools

        github_tools = GitHubIssueTools(
            root_resolver=projects_service.selected_or_refuse,
            card_tools=card_tools,
        )
        github_tools.register_tools(tool_registry)
        from src.application.skills.project_dev_tools import ProjectDevTools

        project_dev_tools = ProjectDevTools(
            root_resolver=projects_service.selected_or_refuse,
            card_tools=card_tools,
            selected_info=projects_service.get_selected,
        )
        project_dev_tools.register_tools(tool_registry)
        agent_registry.projects_service = projects_service
        from src.application.skills.card_handoff_tools import CardHandoffTools

        CardHandoffTools(  # CARD-563: Architect hands a Ready card to Developer
            root_resolver=projects_service.selected_or_refuse,
            card_tools=card_tools,
            handoff_engine=handoff_engine,
            agent_registry=agent_registry,
        ).register_tools(tool_registry)
        from src.application.skills.card_review_tools import CardReviewTools

        CardReviewTools(  # CARD-564: Architect reviews In Review cards (Done / Returned)
            root_resolver=projects_service.selected_or_refuse,
            card_tools=card_tools,
            dev_tools=project_dev_tools,
        ).register_tools(tool_registry)

        # 12b. Agent Private Storage Tools [CARD-148, REQ-STORAGE-003]
        from src.application.skills.agent_storage_tools import AgentStorageTools

        data_root = Path(skills_dir).parent if skills_dir else None
        storage_tools = AgentStorageTools(data_dir=data_root)
        storage_tools.register_tools(tool_registry)

        # 12b. Dedicated Cognitive Memory Brain Tools [CARD-116, CARD-405]
        from src.application.memory.agent_memory_tools import AgentMemoryTools

        memory_tools = AgentMemoryTools(data_dir=data_root)
        memory_tools.register_tools(tool_registry)

        # 12c. Enterprise MCP Engineering Tools [CARD-394]
        from src.application.skills.mcp_engineering_tools import MCPEngineeringTools

        mcp_engineering_tools = MCPEngineeringTools(
            state_store=store,
            tool_registry=tool_registry,
            data_dir=data_root,
            root_resolver=projects_service.resolve_root,
        )
        mcp_engineering_tools.register_tools(tool_registry)
        agent_registry.mcp_engineering_tools = mcp_engineering_tools

        from src.application.skills.native_tool_engineering import NativeToolEngineeringTools

        native_tool_engineering = NativeToolEngineeringTools(
            state_store=store,
            tool_registry=tool_registry,
            agent_registry=agent_registry,
        )
        native_tool_engineering.register_tools(tool_registry)
        agent_registry.native_tool_engineering = native_tool_engineering

        # 13. User agentskills.io packs (CARD-104) [REQ-DATA-009 - REQ-DATA-011]
        from src.application.skills.user_catalog import UserSkillCatalog

        catalog = UserSkillCatalog(skills_dir=skills_dir, tool_registry=tool_registry)
        catalog.agent_lookup = agent_registry.get_agent
        catalog.mount_at_bootstrap()
        agent_registry.user_skill_catalog = catalog

        # 14. Validate skill tools: an unknown tool id is a warning and grants nothing [CARD-570]
        from src.infrastructure.content.store import set_tool_registry

        known = {t.name for t in tool_registry.list_tools()}
        set_tool_registry(tool_registry)
        agent_registry.skill_tool_warnings = agent_registry._content.validate_tools(known)
        for sid, names in agent_registry.skill_tool_warnings.items():
            logger.warning("Skill %s names unknown tools %s; they grant nothing.", sid, names)

        return agent_registry, tool_registry
