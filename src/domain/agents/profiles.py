"""
Built-in Agent Manifests & Profile Definitions [REQ-AGENTS-001].

CARD-429: no live builtin agents. autoreiv, direct, developer, and tutor are
Platform Agent Packs (platform-packs/, always seeded). The hidden agent-builder
profile is retired; Developer holds scaffold / propose / commit for agents,
skills, and tools.
"""

from typing import Dict, List, Optional

from src.domain.kernel.models import AgentProfile

# Ids that must not appear as live agents. Leftover SQLite rows are purged on boot.
RETIRED_LIVE_AGENT_IDS = frozenset({"agent-builder"})

BUILTIN_PROFILES: List[AgentProfile] = []

DEFAULT_PLATFORM_AGENT_ID: str = "autoreiv"

# Legacy lookup ids that used to alias the Assistant / Wiki / AutoReiv builtins.
LEGACY_AGENT_ALIASES: Dict[str, str] = {
    "assistant": "autoreiv",
    "wiki": "autoreiv",
    "general-assistant": "autoreiv",
    "general": "autoreiv",
    "librarian": "autoreiv",
    "system-librarian": "autoreiv",
    "system-agent": "autoreiv",
    "system": "autoreiv",
    "linux-sysadmin": "autoreiv",
    "sysadmin": "autoreiv",
    "auditor-critic": "autoreiv",
    "forge": "autoreiv",
}

_PROFILES_MAP: Dict[str, AgentProfile] = {}


def canonical_agent_id(agent_id: str) -> str:
    """Map legacy alias ids onto autoreiv. Retired ids stay themselves."""
    key = (agent_id or "").lower().strip()
    if key in RETIRED_LIVE_AGENT_IDS:
        return key
    return LEGACY_AGENT_ALIASES.get(key, key)


def get_builtin_profile(agent_id: str) -> Optional[AgentProfile]:
    """Retrieve a built-in agent profile by its ID (supporting legacy aliases)."""
    key = canonical_agent_id(agent_id)
    if key in RETIRED_LIVE_AGENT_IDS:
        return None
    return _PROFILES_MAP.get(key)
