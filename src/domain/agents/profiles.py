"""
Built-in Agent Manifests & Profile Definitions [REQ-AGENTS-001].
Shipped builtin: hidden Agent Builder. Assistant and AutoReiv are Platform Agent Packs
(platform-packs/, always seeded). Conductor, Coding, and Review stay optional catalog packs.
"""

from typing import Dict, List, Optional

from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.settings.models import ModelPurpose

AGENT_BUILDER_PROFILE = AgentProfile(
    id="agent-builder",
    name="Agent Builder",
    description=(
        "Talks to the human about skills, tools, and workflows. "
        "Researches with Job/Phase and commits approved packs into $DATA_DIR/skills. "
        "Not Conductor: does not write SDLC cards or hand Ready work to Coding."
    ),
    system_prompt=(
        "You are AutoReiv's Agent Builder. You talk to the human about skills, tools, and workflows. "
        "You research with Job/Phase. You emit HITL drafts via propose_skill / propose_tool / propose_workflow. "
        "You never auto-write SKILL.md or Python under src/. After Approve, you may commit a pack into "
        "$DATA_DIR/skills through commit_skill_pack - the same files Agent Studio edits. "
        "Prefer adding tools/skills to an existing specialist over a new agent when the allowlist would exceed 12. "
        "You are not Conductor: you do not write SDLC cards or hand Ready work to Coding."
    ),
    purpose=ModelPurpose.GENERAL,
    tone=AgentTone.FRIENDLY,
    avatar_icon="sparkles",
    model="default",
    allowed_tool_names=[
        "list_available_skills_and_tools",
        "propose_agent_specification",
        "save_agent_specification",
        "propose_skill",
        "propose_tool",
        "propose_workflow",
        "commit_skill_pack",
        "list_user_skill_packs",
        "skill_view",
        "lookup_agents",
        "handoff_to_agent",
    ],
    pinned_tool_names=["propose_skill", "commit_skill_pack"],
    max_turns=10,
    is_builtin=True,
    show_in_chat=False,
)


BUILTIN_PROFILES: List[AgentProfile] = [
    AGENT_BUILDER_PROFILE,
]

# Legacy lookup ids that used to alias the Assistant / AutoReiv builtins.
LEGACY_AGENT_ALIASES: Dict[str, str] = {
    "general-assistant": "assistant",
    "general": "assistant",
    "librarian": "assistant",
    "system-agent": "autoreiv",
    "system": "autoreiv",
    "linux-sysadmin": "autoreiv",
    "sysadmin": "autoreiv",
    "auditor-critic": "autoreiv",
}

_PROFILES_MAP: Dict[str, AgentProfile] = {
    "agent-builder": AGENT_BUILDER_PROFILE,
}


def canonical_agent_id(agent_id: str) -> str:
    """Map legacy alias ids onto assistant / autoreiv / agent-builder."""
    key = (agent_id or "").lower().strip()
    return LEGACY_AGENT_ALIASES.get(key, key)


def get_builtin_profile(agent_id: str) -> Optional[AgentProfile]:
    """Retrieve a built-in agent profile by its ID (supporting legacy aliases)."""
    key = canonical_agent_id(agent_id)
    return _PROFILES_MAP.get(key)
