"""
Built-in Agent Registry & Bootstrapper [REQ-AGENTS-001].
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.sysadmin_tools import SysadminTools
from src.application.skills.system_agent_tools import SystemAgentTools
from src.application.skills.wiki_tools import WikiTools
from src.application.telemetry.collector import TelemetryCollector
from src.domain.agents.profiles import BUILTIN_PROFILES, canonical_agent_id, get_builtin_profile
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class BuiltinAgentRegistry:
    """
    Registry for managing available agent profiles and bootstrapping
    the hidden Agent Builder builtin, Platform Agent Packs, custom agents, and authorized tools.
    """

    def __init__(
        self,
        profiles: Optional[List[AgentProfile]] = None,
        state_store: Optional[SQLiteStateStore] = None,
        master_tool_registry: Optional[ScopedToolRegistry] = None,
    ):
        self._profiles: Dict[str, AgentProfile] = {}
        self.state_store = state_store
        self.master_tool_registry = master_tool_registry or ScopedToolRegistry()

        for p in profiles or BUILTIN_PROFILES:
            self.register_profile(p)

    def register_profile(self, profile: AgentProfile) -> None:
        self._profiles[profile.id] = profile

    def register_custom_agent(self, profile: AgentProfile) -> None:
        """Persist a custom agent profile and cache in memory."""
        self._profiles[profile.id] = profile
        if self.state_store:
            self.state_store.save_agent_profile(profile)

    def delete_custom_agent(self, agent_id: str) -> bool:
        """Delete custom agent profile (protects built-in agents)."""
        from src.application.agent_packs.schema import PLATFORM_PACK_IDS

        builtin_ids = {p.id for p in BUILTIN_PROFILES}
        if agent_id in builtin_ids or agent_id in PLATFORM_PACK_IDS:
            return False

        if agent_id in self._profiles:
            del self._profiles[agent_id]

        if self.state_store:
            return self.state_store.delete_agent_profile(agent_id)
        return True

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Fetch agent profile with SQLite custom agent resolution, alias fallback, and override overlay."""
        profile: Optional[AgentProfile] = None
        lookup_id = canonical_agent_id(agent_id)

        if self.state_store:
            profile = self.state_store.get_agent_profile(lookup_id)

        if not profile:
            profile = self._profiles.get(lookup_id)

        if not profile:
            profile = get_builtin_profile(lookup_id)

        if not profile:
            return None

        # Apply any operator override
        if self.state_store:
            override = self.state_store.get_agent_override(profile.id)
            if override:
                profile = profile.model_copy()
                if override.system_prompt:
                    profile.system_prompt = override.system_prompt
                if override.tone:
                    from src.domain.kernel.models import AgentTone

                    profile.tone = (
                        AgentTone(override.tone) if override.tone in [t.value for t in AgentTone] else profile.tone
                    )
                if override.model:
                    profile.model = override.model
                if override.purpose:
                    from src.domain.settings.models import ModelPurpose

                    try:
                        profile.purpose = ModelPurpose(override.purpose)
                    except ValueError:
                        pass
                if override.allowed_tool_names is not None:
                    profile.allowed_tool_names = override.allowed_tool_names
                if override.allowed_skill is not None:
                    profile.allowed_skill = override.allowed_skill
                if override.pack_tool_names is not None:
                    profile.pack_tool_names = override.pack_tool_names
                if override.show_in_chat is not None:
                    profile.show_in_chat = override.show_in_chat
                if override.max_turns:
                    profile.max_turns = override.max_turns
                if override.history_retention_days is not None:
                    profile.history_retention_days = override.history_retention_days

        return profile

    def get_profile(self, agent_id: str) -> Optional[AgentProfile]:
        return self.get_agent(agent_id)

    def list_agents(self) -> List[AgentProfile]:
        """List all available agents (built-in baseline merged with custom agents)."""
        agents_map: Dict[str, AgentProfile] = {}

        # 1. Built-in defaults
        for p in BUILTIN_PROFILES:
            agents_map[p.id] = p

        # 2. In-memory registrations
        for pid, p in self._profiles.items():
            agents_map[pid] = p

        # 3. SQLite custom agents
        if self.state_store:
            custom_agents = self.state_store.list_custom_agent_profiles()
            for ca in custom_agents:
                agents_map[ca.id] = ca

        # 4. Resolve overrides for all
        result = []
        for aid in agents_map:
            ag = self.get_agent(aid)
            if ag and ag not in result:
                result.append(ag)

        return result

    def list_profiles(self) -> List[AgentProfile]:
        return self.list_agents()

    def get_scoped_registry_for_agent(self, agent: AgentProfile) -> ScopedToolRegistry:
        """Return a tool registry scoped strictly to the agent's authorized tools."""
        if not agent.allowed_tool_names:
            return self.master_tool_registry

        scoped = ScopedToolRegistry()
        allowed_set = set(agent.allowed_tool_names)
        for name, tool in self.master_tool_registry._tools.items():
            if name in allowed_set:
                scoped._tools[name] = tool
        return scoped

    @classmethod
    def bootstrap(
        cls,
        store: SQLiteStateStore,
        telemetry: TelemetryCollector,
        wiki_root: str = "data/wiki",
        skills_dir: Optional[str] = None,
    ) -> Tuple["BuiltinAgentRegistry", ScopedToolRegistry]:
        """
        Bootstrap the agent ecosystem: registers the hidden Agent Builder builtin,
        initializes platform tool groups, and binds authorized tools to master ScopedToolRegistry.
        """
        tool_registry = ScopedToolRegistry()
        agent_registry = cls(
            profiles=BUILTIN_PROFILES,
            state_store=store,
            master_tool_registry=tool_registry,
        )

        # 1. Universal Wiki Tools -> Assistant, AutoReiv, Custom Agents
        wiki_tools = WikiTools(wiki_root=wiki_root)
        wiki_tools.register_tools(tool_registry)

        # 2. Weekly Notes & To-Dos Tools -> Assistant
        from src.application.skills.weekly_notes_tools import WeeklyNotesTools

        weekly_notes_tools = WeeklyNotesTools(wiki_tools=wiki_tools, wiki_root=wiki_root)
        weekly_notes_tools.register_tools(tool_registry)

        # 3. Linux Sysadmin Tools -> AutoReiv
        sysadmin_tools = SysadminTools()
        sysadmin_tools.register_tools(tool_registry)

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

        # 7b. Agent Pack import/export/scaffold tools -> AutoReiv
        from src.application.skills.agent_pack_tools import AgentPackTools

        pack_tools = AgentPackTools(
            agent_registry=agent_registry,
            tool_registry=tool_registry,
            store=store,
            data_dir=Path(skills_dir).parent if skills_dir else None,
        )
        pack_tools.register_tools(tool_registry)

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

        # 11. Spec-driven SDLC cards / specs / steering
        from src.application.sdlc.projects_service import ProjectsService
        from src.application.skills.card_tools import CardTools

        projects_service = ProjectsService(store=store)
        projects_service.register_tools(tool_registry)
        card_tools = CardTools(root_resolver=projects_service.resolve_root)
        card_tools.register_tools(tool_registry)

        # 12. Project-scoped file tools (jailed)
        from src.application.skills.project_file_tools import ProjectFileTools

        project_file_tools = ProjectFileTools(root_resolver=projects_service.resolve_root)
        project_file_tools.register_tools(tool_registry)
        from src.application.skills.git_tools import GitTools

        git_tools = GitTools(root_resolver=projects_service.resolve_root)
        git_tools.register_tools(tool_registry)
        from src.application.skills.github_issue_tools import GitHubIssueTools

        github_tools = GitHubIssueTools(
            root_resolver=projects_service.resolve_root,
            card_tools=card_tools,
        )
        github_tools.register_tools(tool_registry)
        agent_registry.projects_service = projects_service

        # 13. User agentskills.io packs (CARD-104) [REQ-DATA-009 - REQ-DATA-011]
        from src.application.skills.user_catalog import UserSkillCatalog

        catalog = UserSkillCatalog(skills_dir=skills_dir, tool_registry=tool_registry)
        catalog.agent_lookup = agent_registry.get_agent
        catalog.mount_at_bootstrap()
        agent_registry.user_skill_catalog = catalog

        # 14. Platform Agent Packs (Assistant, AutoReiv) — copy-if-missing, import if unregistered.
        if skills_dir:
            from src.infrastructure.skills.platform_packs import install_platform_agent_packs
            from src.infrastructure.skills.seed import seed_bundled_skill_packs

            seed_bundled_skill_packs(skills_dir)
            install_platform_agent_packs(
                Path(skills_dir).parent,
                agent_registry,
                tool_registry,
            )

        return agent_registry, tool_registry
