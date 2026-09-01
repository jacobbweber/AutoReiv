"""Helpers to load repo catalog packs in tests (not auto-loaded at startup)."""

from pathlib import Path

from src.application.agent_packs.schema import AgentPackManifest
from src.infrastructure.data.resolver import repo_root


def catalog_dir() -> Path:
    return repo_root() / "agent-packs"


PLATFORM_PACK_IDS = ("assistant", "autoreiv")


def platform_dir() -> Path:
    return repo_root() / "platform-packs"


def load_platform_manifest(pack_id: str) -> AgentPackManifest:
    path = platform_dir() / pack_id / "pack.json"
    return AgentPackManifest.model_validate_json(path.read_text(encoding="utf-8"))


def platform_pack_profile(pack_id: str):
    """AgentProfile from a platform pack, including ticked Platform skill tools."""
    from src.application.agent_packs.schema import tools_for_platform_skills
    from src.domain.kernel.models import AgentProfile, AgentTone
    from src.domain.settings.models import ModelPurpose

    manifest = load_platform_manifest(pack_id)
    tools = list(manifest.pack_tool_names)
    for name in tools_for_platform_skills(list(manifest.allowed_skill)):
        if name not in tools:
            tools.append(name)
    try:
        purpose = ModelPurpose(manifest.purpose)
    except ValueError:
        purpose = ModelPurpose.GENERAL
    try:
        tone = AgentTone(manifest.tone)
    except ValueError:
        tone = AgentTone.DEFAULT
    return AgentProfile(
        id=manifest.id,
        name=manifest.name,
        description=manifest.description,
        system_prompt=manifest.system_prompt,
        purpose=purpose,
        tone=tone,
        avatar_icon=manifest.avatar_icon,
        model=manifest.model,
        allowed_tool_names=tools,
        allowed_skill=list(manifest.allowed_skill),
        pack_tool_names=list(manifest.pack_tool_names),
        show_in_chat=manifest.show_in_chat,
        is_builtin=False,
    )
