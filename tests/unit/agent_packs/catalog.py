"""Helpers to load repo catalog packs in tests (not auto-loaded at startup)."""

from pathlib import Path
from typing import Any, List

from src.application.agent_packs.schema import AgentPackManifest
from src.application.agent_packs.service import AgentPackService
from src.infrastructure.data.resolver import repo_root

SDLC_PACK_IDS = ("conductor", "coding", "review")


def catalog_dir() -> Path:
    return repo_root() / "agent-packs"


def load_catalog_manifest(pack_id: str) -> AgentPackManifest:
    path = catalog_dir() / pack_id / "pack.json"
    return AgentPackManifest.model_validate_json(path.read_text(encoding="utf-8"))


def import_sdlc_packs(data_dir: Any, registry: Any, tool_reg: Any) -> List[Any]:
    available = {t.name for t in tool_reg.list_tools()} if tool_reg is not None else None
    service = AgentPackService(
        data_dir=data_dir,
        agent_registry=registry,
        store=getattr(registry, "state_store", None),
        available_tools=available,
    )
    return [service.import_path(catalog_dir() / pack_id) for pack_id in SDLC_PACK_IDS]


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
