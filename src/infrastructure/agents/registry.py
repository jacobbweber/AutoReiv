"""
Built-in Agent Registry & Bootstrapper [REQ-AGENTS-001].
"""

from typing import Dict, List, Optional, Tuple

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.sysadmin_skill import SysadminSkill
from src.application.skills.system_agent_skill import SystemAgentSkill
from src.application.skills.wiki_skill import WikiSkill
from src.application.telemetry.collector import TelemetryCollector
from src.domain.agents.profiles import BUILTIN_PROFILES, get_builtin_profile
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class BuiltinAgentRegistry:
    """
    Registry for managing available agent profiles and bootstrapping
    the default core agents (Assistant, AutoReiv, Coding), custom agents, and authorized skills.
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
        builtin_ids = {p.id for p in BUILTIN_PROFILES}
        if agent_id in builtin_ids:
            return False

        if agent_id in self._profiles:
            del self._profiles[agent_id]

        if self.state_store:
            return self.state_store.delete_agent_profile(agent_id)
        return True

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Fetch agent profile with SQLite custom agent resolution, alias fallback, and override overlay."""
        profile: Optional[AgentProfile] = None

        if self.state_store:
            profile = self.state_store.get_agent_profile(agent_id)

        if not profile:
            profile = self._profiles.get(agent_id)

        if not profile:
            profile = get_builtin_profile(agent_id)

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
                if override.allowed_tool_names is not None:
                    profile.allowed_tool_names = override.allowed_tool_names
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
    ) -> Tuple["BuiltinAgentRegistry", ScopedToolRegistry]:
        """
        Bootstrap the agent ecosystem: registers baseline agents (Assistant, AutoReiv, Coding),
        initializes platform skills, and binds authorized tools to master ScopedToolRegistry.
        """
        tool_registry = ScopedToolRegistry()
        agent_registry = cls(
            profiles=BUILTIN_PROFILES,
            state_store=store,
            master_tool_registry=tool_registry,
        )

        # 1. Universal Wiki Skill -> Assistant, AutoReiv, Coding, Custom Agents
        wiki_skill = WikiSkill(wiki_root=wiki_root)
        wiki_skill.register_tools(tool_registry)

        # 2. Weekly Notes & To-Dos Skill -> Assistant
        from src.application.skills.weekly_notes_skill import WeeklyNotesSkill

        weekly_notes_skill = WeeklyNotesSkill(wiki_skill=wiki_skill, wiki_root=wiki_root)
        weekly_notes_skill.register_tools(tool_registry)

        # 3. Linux Sysadmin Skill -> AutoReiv
        sysadmin_skill = SysadminSkill()
        sysadmin_skill.register_tools(tool_registry)

        # 4. Platform Diagnostics Skill -> AutoReiv
        system_skill = SystemAgentSkill(store=store, telemetry=telemetry)
        system_skill.register_tools(tool_registry)

        # 5. Programmatic Verification Skill
        from src.application.skills.verification_skill import VerificationSkill

        verify_skill = VerificationSkill(store=store)
        verify_skill.register_tools(tool_registry)

        # 6. Goal & Planning Engine Skill
        from src.application.skills.planning_skill import PlanningSkill

        planning_skill = PlanningSkill()
        planning_skill.register_tools(tool_registry)

        # 7. Agent Builder Skill
        from src.application.skills.agent_builder_skill import AgentBuilderSkill

        builder_skill = AgentBuilderSkill(agent_registry=agent_registry, tool_registry=tool_registry)
        builder_skill.register_tools(tool_registry)

        # 8. Orchestration & Subagent Handoff Skill
        from src.application.orchestration.directory_service import AgentDirectoryService
        from src.application.orchestration.handoff_engine import HandoffIsolationEngine
        from src.application.skills.orchestration_skill import OrchestrationSkill

        directory_service = AgentDirectoryService(agent_registry=agent_registry, state_store=store)
        handoff_engine = HandoffIsolationEngine(agent_registry=agent_registry, state_store=store)
        orch_skill = OrchestrationSkill(directory_service=directory_service, handoff_engine=handoff_engine)
        orch_skill.register_tools(tool_registry)
        agent_registry.handoff_engine = handoff_engine

        # 9. Batch Worker & Map-Reduce Skill
        from src.application.skills.worker_skill import BatchWorkerSkill

        worker_skill = BatchWorkerSkill(state_store=store, wiki_skill=wiki_skill)
        worker_skill.register_tools(tool_registry)

        # 10. Sandbox Execution Skill -> Coding
        from src.application.skills.sandbox_skill import SandboxExecutionSkill

        sandbox_skill = SandboxExecutionSkill()
        sandbox_skill.register_tools(tool_registry)

        # 11. Spec-driven SDLC cards / specs / steering
        from src.application.skills.card_skill import CardSkill

        card_skill = CardSkill()
        card_skill.register_tools(tool_registry)

        return agent_registry, tool_registry
