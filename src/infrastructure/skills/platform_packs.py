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

# Initial Factory Seed Agent Packs (repo platform-packs/ -> $DATA_DIR/packs/).
# All seeded packs are simply agent packs once installed.
DEFAULT_SEEDED_PACK_IDS: tuple[str, ...] = ("autoreiv", "direct", "developer", "tutor")
PLATFORM_PACK_IDS: tuple[str, ...] = DEFAULT_SEEDED_PACK_IDS
ALL_PLATFORM_PACK_IDS: tuple[str, ...] = DEFAULT_SEEDED_PACK_IDS
RETIRED_PLATFORM_PACK_IDS: tuple[str, ...] = (
    "assistant",
    "wiki",
    "forge",
    "homelab",
    "homelab-admin",
    "finance",
)


def cleanup_orphaned_platform_packs(
    packs_path: Union[str, Path],
    agent_registry: Any = None,
    state_store: Any = None,
) -> list[str]:
    """CARD-341 / CARD-366: Clean up permanently retired platform packs from user data, registry, and database."""
    dest_root = Path(packs_path)
    cleaned: list[str] = []
    store = state_store or getattr(agent_registry, "state_store", None)
    for retired_id in RETIRED_PLATFORM_PACK_IDS:
        target_dir = dest_root / retired_id
        if target_dir.is_dir():
            try:
                shutil.rmtree(target_dir, ignore_errors=True)
                logger.info("Cleaned up retired platform pack folder: %s", target_dir)
                cleaned.append(retired_id)
            except Exception:
                logger.exception("Failed to remove retired pack folder %s", target_dir)
        if agent_registry is not None:
            if hasattr(agent_registry, "delete_custom_agent"):
                try:
                    agent_registry.delete_custom_agent(retired_id, purge_history=True)
                except Exception:
                    pass
            if hasattr(agent_registry, "unregister_agent"):
                try:
                    agent_registry.unregister_agent(retired_id)
                except Exception:
                    pass
            if hasattr(agent_registry, "_agents"):
                agent_registry._agents.pop(retired_id, None)
            if hasattr(agent_registry, "_profiles"):
                agent_registry._profiles.pop(retired_id, None)
        if store is not None and hasattr(store, "delete_agent_profile"):
            try:
                store.delete_agent_profile(retired_id, purge_history=True)
            except Exception:
                pass
    return cleaned


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


def sync_checkout_example_user_packs(
    packs_path: Union[str, Path],
    *,
    checkout_root: Optional[Union[str, Path]] = None,
) -> list[str]:
    """CARD-269: refresh example user packs (e.g. finance) from checkout when thin/missing sections.

    Does not touch platform packs. Overwrites dest pack.json only when missing required
    good-agent Instruction section headers (or dest missing).
    """
    dest_root = Path(packs_path)
    dest_root.mkdir(parents=True, exist_ok=True)
    root = Path(checkout_root) if checkout_root is not None else Path(__file__).resolve().parents[3]
    src_root = root / "packs"
    if not src_root.is_dir():
        return []
    try:
        from src.domain.agents.good_agent_instructions import assert_good_agent_sections
    except Exception:
        assert_good_agent_sections = None  # type: ignore[assignment]
    updated: list[str] = []
    for sub in sorted(src_root.iterdir()):
        if not sub.is_dir() or sub.name in ALL_PLATFORM_PACK_IDS:
            continue
        src_json = sub / "pack.json"
        if not src_json.is_file():
            continue
        dest = dest_root / sub.name
        dest_json = dest / "pack.json"
        should_copy = not dest_json.is_file()
        if not should_copy and assert_good_agent_sections is not None:
            try:
                import json as _json

                raw = _json.loads(dest_json.read_text(encoding="utf-8"))
                prompt = raw.get("system_prompt") or ""
                should_copy = bool(assert_good_agent_sections(prompt))
            except Exception:
                should_copy = True
        if not should_copy:
            continue
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_json, dest_json)
        logger.info("Synced example user pack Instructions %s -> %s", sub.name, dest_json)
        updated.append(sub.name)
    return updated


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

    # CARD-367: Run declarative desired-state pack reconciler before seeding
    from src.infrastructure.skills.reconciler import DeclarativePackReconciler

    reconciler = DeclarativePackReconciler(
        data_dir=root,
        state_store=getattr(agent_registry, "state_store", None),
        agent_registry=agent_registry,
    )
    reconciler.reconcile()

    cleanup_orphaned_platform_packs(packs_path, agent_registry=agent_registry)
    seed_platform_pack_folders(packs_path, checkout_root=checkout_root)
    sync_checkout_example_user_packs(packs_path, checkout_root=checkout_root)

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
    from src.domain.kernel.models import AgentOrigin

    for pack_id in ALL_PLATFORM_PACK_IDS:
        dest = packs_path / pack_id
        src = platform_packs_root(checkout_root) / pack_id
        # Factory seed is repo platform-packs/; live brain is always DATA_DIR/packs/.
        # seed_platform_pack_folders already ran - never fall back to reading the seed as live.
        if not (dest / "pack.json").is_file():
            logger.warning("Platform pack %s missing under user data after seed; skip install", pack_id)
            continue
        existing = agent_registry.get_agent(pack_id) if agent_registry is not None else None
        if existing is not None:
            if getattr(existing, "origin", None) != AgentOrigin.PACK:
                existing.origin = AgentOrigin.PACK
                if service.store and hasattr(service.store, "save_custom_agent_profile"):
                    service.store.save_custom_agent_profile(existing)
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

                    # CARD-381: Read live pack.json in user data to discover any operator custom tools
                    user_pack_tools: list[str] = []
                    if (dest / "pack.json").is_file():
                        try:
                            with open(dest / "pack.json", "r", encoding="utf-8") as upf:
                                user_pack_data = json.load(upf)
                            user_pack_tools = list(user_pack_data.get("allowed_tool_names") or [])
                        except Exception:
                            pass

                    # Union merge: keep existing tools (and user pack tools) without clobbering operator grants
                    current_tools = list(getattr(existing, "allowed_tool_names", None) or [])
                    final_tools = list(current_tools)
                    for t in user_pack_tools:
                        if t not in final_tools:
                            final_tools.append(t)
                    for t in merged_tools:
                        if t not in final_tools:
                            final_tools.append(t)

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
                    if getattr(existing, "allowed_tool_names", None) != final_tools:
                        existing.allowed_tool_names = final_tools
                        changed = True

                    if changed and service.store and hasattr(service.store, "save_custom_agent_profile"):
                        service.store.save_custom_agent_profile(existing)
                        logger.info("Synchronized agent pack profile for %s", pack_id)
                    # CARD-269 / CARD-381: Refresh operator override without wiping custom tools
                    if (
                        service.store
                        and hasattr(service.store, "get_agent_override")
                        and hasattr(service.store, "save_agent_override")
                    ):
                        ov = service.store.get_agent_override(pack_id)
                        if ov is not None:
                            ov_changed = False
                            if new_prompt and getattr(ov, "system_prompt", None) != new_prompt:
                                ov.system_prompt = new_prompt
                                ov_changed = True
                            if getattr(ov, "allowed_tool_names", None) != final_tools:
                                ov.allowed_tool_names = final_tools
                                ov_changed = True
                            if ov_changed:
                                service.store.save_agent_override(ov)
                                logger.info("Synchronized agent_overrides for %s", pack_id)

                    if dest.exists():
                        # Non-destructive pack.json update: keep operator customizations intact
                        if (dest / "pack.json").is_file():
                            try:
                                with open(dest / "pack.json", "r", encoding="utf-8") as dpf:
                                    dest_data = json.load(dpf)
                                dest_data["allowed_tool_names"] = final_tools
                                dest_data["pack_tool_names"] = new_pack_tools
                                dest_data["allowed_skill"] = new_allowed_skill
                                if dest_data.get("purpose") == "code":
                                    dest_data["purpose"] = "task_execution"
                                dest_data["origin"] = "pack"
                                if new_prompt:
                                    dest_data["system_prompt"] = new_prompt
                                with open(dest / "pack.json", "w", encoding="utf-8") as dpf:
                                    json.dump(dest_data, dpf, indent=2)
                            except Exception:
                                if (src / "pack.json").is_file():
                                    shutil.copy2(src / "pack.json", dest / "pack.json")
                        elif (src / "pack.json").is_file():
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
            # Heal legacy purpose: "code" before importing
            dest_json_path = dest / "pack.json"
            if dest_json_path.is_file():
                try:
                    with open(dest_json_path, "r", encoding="utf-8") as dpf:
                        ddata = json.load(dpf)
                    if ddata.get("purpose") == "code":
                        ddata["purpose"] = "task_execution"
                        ddata["origin"] = "pack"
                        with open(dest_json_path, "w", encoding="utf-8") as dpf:
                            json.dump(ddata, dpf, indent=2)
                except Exception:
                    pass
            profile = service.import_path(dest)
            if profile and getattr(profile, "origin", None) != AgentOrigin.PACK:
                profile.origin = AgentOrigin.PACK
                if service.store and hasattr(service.store, "save_agent_profile"):
                    service.store.save_agent_profile(profile)
            installed.append(pack_id)
            logger.info("Imported agent pack %s", pack_id)
        except Exception:
            logger.exception("Failed to import agent pack %s from %s", pack_id, dest)

    # Discover and import any existing user packs in $DATA_DIR/packs/ that are not yet in the registry
    if packs_path.is_dir():
        for sub in sorted(packs_path.iterdir()):
            if not sub.is_dir() or sub.name in ALL_PLATFORM_PACK_IDS or sub.name in RETIRED_PLATFORM_PACK_IDS:
                continue
            if (sub / "pack.json").is_file():
                # CARD-367 Ghost Import Loop Elimination:
                # Do not auto-import packs that represent abandoned platform seeds
                try:
                    with open(sub / "pack.json", "r", encoding="utf-8") as pf:
                        pack_data = json.load(pf)
                except Exception:
                    continue

                existing = agent_registry.get_agent(sub.name) if agent_registry is not None else None
                if existing is None:
                    try:
                        imported_profile = service.import_path(sub)
                        if imported_profile and getattr(imported_profile, "origin", None) != AgentOrigin.PACK:
                            imported_profile.origin = AgentOrigin.PACK
                            if service.store and hasattr(service.store, "save_agent_profile"):
                                service.store.save_agent_profile(imported_profile)
                        installed.append(sub.name)
                        logger.info("Imported user pack %s from %s", sub.name, sub)
                    except Exception:
                        logger.exception("Failed to import user pack %s from %s", sub.name, sub)
                else:
                    # CARD-269: refresh user pack Instructions from data/packs/<id>/pack.json
                    try:
                        with open(sub / "pack.json", "r", encoding="utf-8") as pf:
                            pack_data = json.load(pf)
                        new_prompt = pack_data.get("system_prompt")
                        if new_prompt and getattr(existing, "system_prompt", None) != new_prompt:
                            existing.system_prompt = new_prompt
                            if service.store and hasattr(service.store, "save_custom_agent_profile"):
                                service.store.save_custom_agent_profile(existing)
                            if (
                                service.store
                                and hasattr(service.store, "get_agent_override")
                                and hasattr(service.store, "save_agent_override")
                            ):
                                ov = service.store.get_agent_override(sub.name)
                                if ov is not None:
                                    ov.system_prompt = new_prompt
                                    service.store.save_agent_override(ov)
                            elif service.store and hasattr(service.store, "save_agent_override"):
                                pass
                            logger.info("Synchronized user pack Instructions for %s", sub.name)
                    except Exception:
                        logger.exception("Failed to sync user pack prompt for %s", sub.name)

    return installed
