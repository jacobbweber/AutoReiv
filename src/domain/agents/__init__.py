"""
Domain Agents package.
"""

from src.domain.agents.profiles import (
    BUILTIN_PROFILES,
    DEFAULT_PLATFORM_AGENT_ID,
    canonical_agent_id,
    get_builtin_profile,
)

__all__ = [
    "BUILTIN_PROFILES",
    "DEFAULT_PLATFORM_AGENT_ID",
    "canonical_agent_id",
    "get_builtin_profile",
]
