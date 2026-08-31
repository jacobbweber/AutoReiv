"""
Domain Agents package.
"""

from src.domain.agents.profiles import (
    BUILTIN_PROFILES,
    GENERAL_ASSISTANT_PROFILE,
    LIBRARIAN_PROFILE,
    LINUX_SYSADMIN_PROFILE,
    SYSTEM_AGENT_PROFILE,
    get_builtin_profile,
)

__all__ = [
    "GENERAL_ASSISTANT_PROFILE",
    "LINUX_SYSADMIN_PROFILE",
    "LIBRARIAN_PROFILE",
    "SYSTEM_AGENT_PROFILE",
    "BUILTIN_PROFILES",
    "get_builtin_profile",
]
