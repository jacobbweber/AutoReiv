"""
Built-in Agent Registry & Bootstrapper [REQ-AGENTS-001].
"""

from typing import Dict, List, Optional, Tuple

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.librarian_skill import LibrarianSkill
from src.application.skills.sysadmin_skill import SysadminSkill
from src.application.skills.system_agent_skill import SystemAgentSkill
from src.application.skills.task_tracker_skill import TaskTrackerSkill
from src.application.telemetry.collector import TelemetryCollector
from src.domain.agents.profiles import BUILTIN_PROFILES
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class BuiltinAgentRegistry:
    """
    Registry for managing available agent profiles and bootstrapping
    the default 4 Day-1 agents and their authorized skill sets.
    """

    def __init__(self, profiles: Optional[List[AgentProfile]] = None):
        self._profiles: Dict[str, AgentProfile] = {}
        for p in profiles or BUILTIN_PROFILES:
            self.register_profile(p)

    def register_profile(self, profile: AgentProfile) -> None:
        self._profiles[profile.id] = profile

    def get_profile(self, agent_id: str) -> Optional[AgentProfile]:
        return self._profiles.get(agent_id)

    def list_profiles(self) -> List[AgentProfile]:
        return list(self._profiles.values())

    @classmethod
    def bootstrap(
        cls,
        store: SQLiteStateStore,
        telemetry: TelemetryCollector,
        wiki_root: str = "data/wiki",
    ) -> Tuple["BuiltinAgentRegistry", ScopedToolRegistry]:
        """
        Bootstrap the full agent ecosystem: creates profile registry,
        initializes all 4 skills, and binds authorized tools to ScopedToolRegistry.
        """
        agent_registry = cls(BUILTIN_PROFILES)
        tool_registry = ScopedToolRegistry()

        # 1. General Assistant -> Task Tracker
        task_skill = TaskTrackerSkill(store=store)
        task_skill.register_tools(tool_registry)

        # 2. Linux Sysadmin -> Hardware metrics & Safe CLI
        sysadmin_skill = SysadminSkill()
        sysadmin_skill.register_tools(tool_registry)

        # 3. Librarian -> YAML Frontmatter & PARA-Wiki
        librarian_skill = LibrarianSkill(wiki_root=wiki_root)
        librarian_skill.register_tools(tool_registry)

        # 4. System Agent -> Telemetry & Health checks
        system_skill = SystemAgentSkill(store=store, telemetry=telemetry)
        system_skill.register_tools(tool_registry)

        # 5. Auditor Critic & System Agent -> Programmatic Verification
        from src.application.skills.verification_skill import VerificationSkill

        verify_skill = VerificationSkill(store=store)
        verify_skill.register_tools(tool_registry)

        return agent_registry, tool_registry
