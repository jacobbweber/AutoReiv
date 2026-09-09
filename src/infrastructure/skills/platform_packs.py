"""Seed-if-missing Platform Agent Packs (Assistant, AutoReiv).

Copy from repo ``platform-packs/`` into ``$DATA_DIR/packs/`` when missing.
Never overwrite an existing dest. Do not scan ``agent-packs/``.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Iterable, Optional, Union

logger = logging.getLogger(__name__)

PLATFORM_PACK_IDS: tuple[str, ...] = ("assistant", "autoreiv", "developer")
HOMELAB_PACK_IDS: tuple[str, ...] = (
    "homelab",
    "homelab-architect",
    "homelab-engineer",
    "homelab-admin",
    "homelab-janitor",
)
ALL_PLATFORM_PACK_IDS: tuple[str, ...] = PLATFORM_PACK_IDS + HOMELAB_PACK_IDS


def platform_packs_root(checkout_root: Optional[Union[str, Path]] = None) -> Path:
    """Repo folder of always-installed Platform Agent Packs."""
    if checkout_root is not None:
        return Path(checkout_root) / "platform-packs"
    from src.infrastructure.data.resolver import repo_root

    return repo_root() / "platform-packs"


def seed_platform_pack_folders(
    packs_path: Union[str, Path],
    *,
    checkout_root: Optional[Union[str, Path]] = None,
    pack_ids: Optional[Iterable[str]] = None,
) -> list[str]:
    """Copy platform pack folders into ``packs_path`` when dest is missing.

    Never overwrites an existing dest (user copies stay). Returns ids copied.
    """
    dest_root = Path(packs_path)
    dest_root.mkdir(parents=True, exist_ok=True)
    src_root = platform_packs_root(checkout_root)
    copied: list[str] = []
    ids = tuple(pack_ids) if pack_ids is not None else ALL_PLATFORM_PACK_IDS
    for pack_id in ids:
        src = src_root / pack_id
        dest = dest_root / pack_id
        if not (src / "pack.json").is_file():
            logger.warning("Platform pack %s missing at %s; skip seed", pack_id, src)
            continue
        if dest.exists():
            continue
        shutil.copytree(src, dest)
        logger.info("Seeded platform pack %s -> %s", pack_id, dest)
        copied.append(pack_id)
    return copied


def install_platform_agent_packs(
    data_dir: Union[str, Path],
    agent_registry: Any,
    tool_registry: Any = None,
    *,
    checkout_root: Optional[Union[str, Path]] = None,
) -> list[str]:
    """Copy missing platform packs, then import any id not yet registered.

    Existing custom agents are not re-imported, but platform pack prompts are synchronized.
    ``agent-packs/`` is never scanned.
    """
    import json

    from src.application.agent_packs.service import AgentPackService

    root = Path(data_dir)
    packs_path = root / "packs"
    seed_platform_pack_folders(packs_path, checkout_root=checkout_root)

    available = None
    if tool_registry is not None and hasattr(tool_registry, "list_tools"):
        available = {t.name for t in tool_registry.list_tools()}
    service = AgentPackService(
        data_dir=root,
        agent_registry=agent_registry,
        store=getattr(agent_registry, "state_store", None),
        available_tools=available,
    )
    installed: list[str] = []
    for pack_id in ALL_PLATFORM_PACK_IDS:
        dest = packs_path / pack_id
        src = platform_packs_root(checkout_root) / pack_id
        if not (dest / "pack.json").is_file():
            if (src / "pack.json").is_file():
                dest = src
            else:
                continue
        existing = agent_registry.get_agent(pack_id) if agent_registry is not None else None
        if existing is not None:
            if (src / "pack.json").is_file():
                try:
                    with open(src / "pack.json", "r", encoding="utf-8") as pf:
                        pack_data = json.load(pf)
                    new_prompt = pack_data.get("system_prompt")
                    new_allowed_skill = list(pack_data.get("allowed_skill", []))
                    new_pack_tools = list(pack_data.get("pack_tool_names", []))

                    from src.application.agent_packs.schema import tools_for_platform_skills

                    platform_tools = tools_for_platform_skills(new_allowed_skill)
                    merged_tools = list(new_pack_tools) + [t for t in platform_tools if t not in new_pack_tools]

                    changed = False
                    if new_prompt and getattr(existing, "system_prompt", None) != new_prompt:
                        existing.system_prompt = new_prompt
                        changed = True
                    if getattr(existing, "allowed_skill", None) != new_allowed_skill:
                        existing.allowed_skill = new_allowed_skill
                        changed = True
                    if getattr(existing, "pack_tool_names", None) != new_pack_tools:
                        existing.pack_tool_names = new_pack_tools
                        changed = True
                    if getattr(existing, "allowed_tool_names", None) != merged_tools:
                        existing.allowed_tool_names = merged_tools
                        changed = True

                    if changed and service.store and hasattr(service.store, "save_custom_agent_profile"):
                        service.store.save_custom_agent_profile(existing)
                        logger.info("Synchronized platform pack profile for %s", pack_id)

                    if dest.exists():
                        if (src / "pack.json").is_file():
                            shutil.copy2(src / "pack.json", dest / "pack.json")
                        src_skills = src / "skills"
                        dest_skills = dest / "skills"
                        if src_skills.is_dir():
                            dest_skills.mkdir(parents=True, exist_ok=True)
                            for s in src_skills.iterdir():
                                if s.is_dir():
                                    shutil.copytree(s, dest_skills / s.name, dirs_exist_ok=True)
                            for d in list(dest_skills.iterdir()):
                                if d.is_dir() and not (src_skills / d.name).is_dir():
                                    shutil.rmtree(d, ignore_errors=True)
                        elif dest_skills.is_dir():
                            shutil.rmtree(dest_skills, ignore_errors=True)
                except Exception:
                    logger.exception("Failed to sync updated prompt for %s", pack_id)
            continue
        try:
            service.import_path(dest)
            installed.append(pack_id)
            logger.info("Imported platform pack %s", pack_id)
        except Exception:
            logger.exception("Failed to import platform pack %s from %s", pack_id, dest)

    # Discover and import any existing user packs in $DATA_DIR/packs/ that are not yet in the registry
    if packs_path.is_dir():
        for sub in sorted(packs_path.iterdir()):
            if not sub.is_dir() or sub.name in ALL_PLATFORM_PACK_IDS:
                continue
            if (sub / "pack.json").is_file():
                existing = agent_registry.get_agent(sub.name) if agent_registry is not None else None
                if existing is None:
                    try:
                        service.import_path(sub)
                        installed.append(sub.name)
                        logger.info("Imported user pack %s from %s", sub.name, sub)
                    except Exception:
                        logger.exception("Failed to import user pack %s from %s", sub.name, sub)

    return installed
