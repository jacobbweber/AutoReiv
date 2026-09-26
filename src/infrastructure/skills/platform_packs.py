"""Platform Agent Pack seed + Hybrid C+ reconciliation [ADR-0056 / CARD-414].

First install: copy from repo ``platform-packs/`` into ``$DATA_DIR/packs/`` when missing.
Upgrades: SQLite is the sole writer for profiles/bindings; hash-gated seed apply;
never overwrite when ``user_modified``; never prune operator skill dirs (retired list only).
``pack.json`` is an export projection, not a boot source of truth.

CARD-436: when a non-user_modified hash-gated seed apply runs, also refresh the live
``pack.json`` skill projection (skills / allowed_skill / pack_tool_names / system_prompt)
so Agent Studio ``pack_skills`` matches SQLite without a manual AppData copy.


CARD-425 exception: a named additive grant may append ``native-tool-engineering``
and ``register_native_tool`` / ``plan_native_folder`` onto a user_modified developer
allowlist. That grant does not rewrite the prompt, other allowlist entries, or MCP
servers, and it is recorded once so a later removal stays removed.

CARD-426 exception: when that developer's live ``native-tool-engineering/SKILL.md``
is missing the legacy-loader warning marker, boot appends only the seed warning
block. It does not replace the file, the prompt, or any other skill body. If the
marker or the warning heading is already present, the file is left alone.

CARD-433 exception: when a user_modified developer system prompt does not mention
``scaffold_agent_pack``, boot appends one authoring paragraph and leaves the
existing text in place. The append is recorded once so a later deletion stays
deleted. It does not rewrite a non-user_modified seed prompt.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Iterable, Optional, Union

logger = logging.getLogger(__name__)

# CARD-443: promotion lives in platform_pack_promotion; re-export for stable imports.
from src.infrastructure.skills import platform_pack_promotion as _pack_promo  # noqa: E402

PLATFORM_PACK_SYNC_REPORT_SETTING = _pack_promo.PLATFORM_PACK_SYNC_REPORT_SETTING
PLATFORM_SHIPPED_PROMPT_SETTING = _pack_promo.PLATFORM_SHIPPED_PROMPT_SETTING
PackSyncOutcome = _pack_promo.PackSyncOutcome
PlatformPackSyncReport = _pack_promo.PlatformPackSyncReport
get_last_platform_pack_sync_report = _pack_promo.get_last_platform_pack_sync_report
promote_platform_packs = _pack_promo.promote_platform_packs
prompt_content_hash = _pack_promo.prompt_content_hash

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


def compute_platform_seed_hash(pack_data: dict, src_pack_dir: Optional[Path] = None) -> str:
    """Stable content hash of platform seed (prompt + skills + tools) [ADR-0056]."""
    import hashlib
    import json as _json

    payload = {
        "system_prompt": pack_data.get("system_prompt") or "",
        "allowed_skill": list(pack_data.get("allowed_skill") or []),
        "pack_tool_names": list(pack_data.get("pack_tool_names") or []),
        "allowed_tool_names": list(pack_data.get("allowed_tool_names") or []),
        "skills": list(pack_data.get("skills") or []),
    }
    skill_bodies: dict[str, str] = {}
    if src_pack_dir is not None:
        skills_root = Path(src_pack_dir) / "skills"
        if skills_root.is_dir():
            for skill_dir in sorted(skills_root.iterdir()):
                skill_md = skill_dir / "SKILL.md" if skill_dir.is_dir() else None
                if skill_md and skill_md.is_file():
                    try:
                        skill_bodies[skill_dir.name] = skill_md.read_text(encoding="utf-8")
                    except OSError:
                        pass
    payload["skill_bodies"] = skill_bodies
    raw = _json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# CARD-425 / ADR-0056 exception. Append-only, once per skill id.
USER_MODIFIED_SKILL_GRANT_SETTING = "platform_user_modified_skill_grants"
USER_MODIFIED_ADDITIVE_SKILL_GRANTS: dict[str, dict[str, tuple[str, ...]]] = {
    "developer": {
        "native-tool-engineering": ("register_native_tool", "plan_native_folder"),
        # CARD-429: builder HITL + pack scaffold. Does not include save_agent_specification.
        "capability-authoring": (
            "list_available_skills_and_tools",
            "propose_agent_specification",
            "propose_skill",
            "propose_tool",
            "commit_skill_pack",
            "list_user_skill_packs",
            "skill_view",
            "scaffold_agent_pack",
            "export_agent_pack",
            "import_agent_pack",
        ),
        "proposals": (
            "propose_skill",
            "propose_tool",
            "propose_agent_specification",
            "list_available_skills_and_tools",
            "skill_view",
            "list_user_skill_packs",
            "commit_skill_pack",
        ),
        "build-agent-pack": (
            "export_agent_pack",
            "import_agent_pack",
            "scaffold_agent_pack",
        ),
    },
}


def _append_missing(current: list[str] | None, extras: Iterable[str]) -> tuple[list[str], bool]:
    merged = list(current or [])
    changed = False
    for item in extras:
        text = str(item or "").strip()
        if text and text not in merged:
            merged.append(text)
            changed = True
    return merged, changed


def _patch_allowlist(obj: Any, skill_ids: list[str], tool_names: list[str], *, only_present_fields: bool) -> bool:
    """Append skill ids and tool names. Never assigns prompt or MCP servers."""
    changed = False
    for field, extras in (
        ("allowed_skill", skill_ids),
        ("allowed_tool_names", tool_names),
        ("pack_tool_names", tool_names),
    ):
        current = getattr(obj, field, None)
        if only_present_fields and current is None:
            continue
        merged, field_changed = _append_missing(list(current or []), extras)
        if field_changed:
            setattr(obj, field, merged)
            changed = True
    return changed


def _recorded_skill_grants(store: Any, pack_id: str) -> set[str]:
    if store is None or not hasattr(store, "get_setting"):
        return set()
    raw = store.get_setting(USER_MODIFIED_SKILL_GRANT_SETTING) or {}
    if not isinstance(raw, dict):
        return set()
    recorded = raw.get(pack_id) or []
    if not isinstance(recorded, list):
        return set()
    return {str(item) for item in recorded if str(item).strip()}


def _record_skill_grants(store: Any, pack_id: str, skill_ids: list[str]) -> None:
    if store is None or not hasattr(store, "get_setting") or not hasattr(store, "set_setting"):
        return
    raw = store.get_setting(USER_MODIFIED_SKILL_GRANT_SETTING) or {}
    if not isinstance(raw, dict):
        raw = {}
    current = [str(item) for item in (raw.get(pack_id) or []) if str(item).strip()]
    for skill_id in skill_ids:
        if skill_id not in current:
            current.append(skill_id)
    raw[pack_id] = current
    store.set_setting(USER_MODIFIED_SKILL_GRANT_SETTING, raw)


def apply_user_modified_additive_skill_grants(*, pack_id: str, pack_data: dict, store: Any) -> None:
    """Append named seed skills onto a user_modified allowlist [CARD-425 / REQ-425-001].

    Leaves ``system_prompt``, unrelated tools, and MCP servers in place.
    Records each granted skill id so a later operator removal is not put back.
    """
    spec = USER_MODIFIED_ADDITIVE_SKILL_GRANTS.get(pack_id) or {}
    if not spec or store is None:
        return
    seed_skills = {str(item) for item in (pack_data.get("allowed_skill") or [])}
    already = _recorded_skill_grants(store, pack_id)
    pending = [
        (skill_id, tool_names)
        for skill_id, tool_names in spec.items()
        if skill_id in seed_skills and skill_id not in already
    ]
    if not pending:
        return

    skill_ids = [skill_id for skill_id, _tool_names in pending]
    tool_names: list[str] = []
    for _skill_id, names in pending:
        for name in names:
            if name not in tool_names:
                tool_names.append(name)

    raw = store.get_agent_profile(pack_id) if hasattr(store, "get_agent_profile") else None
    override = store.get_agent_override(pack_id) if hasattr(store, "get_agent_override") else None
    if raw is None and override is None:
        return

    changed = False
    if raw is not None and hasattr(store, "save_custom_agent_profile"):
        if _patch_allowlist(raw, skill_ids, tool_names, only_present_fields=False):
            # CARD-449: automated grant must not set content lock
            # raw.user_modified = True
            store.save_custom_agent_profile(raw)
            changed = True
    if override is not None and hasattr(store, "save_agent_override"):
        if _patch_allowlist(override, skill_ids, tool_names, only_present_fields=True):
            # CARD-449: automated grant must not set content lock
            # override.user_modified = True
            store.save_agent_override(override)
            changed = True

    _record_skill_grants(store, pack_id, skill_ids)
    if changed:
        logger.info(
            "Appended skill %s and tools %s onto user_modified %s allowlist; prompt and other entries left in place",
            skill_ids,
            tool_names,
            pack_id,
        )


# CARD-433 / ADR-0056 exception. Append-only, once per developer prompt.
USER_MODIFIED_PROMPT_APPEND_SETTING = "platform_user_modified_prompt_appends"
DEVELOPER_AUTHORING_PROMPT_GRANT_ID = "developer-authoring-sentence"
SCAFFOLD_AGENT_PACK_TOOL = "scaffold_agent_pack"
DEVELOPER_AUTHORING_PROMPT_PARAGRAPH = (
    "Developer can propose and commit skills, propose tools, and scaffold agent packs "
    "with the capability-authoring tools. `scaffold_agent_pack` writes the pack. "
    "Do not use `save_agent_specification`."
)


def _recorded_prompt_appends(store: Any, pack_id: str) -> set[str]:
    if store is None or not hasattr(store, "get_setting"):
        return set()
    raw = store.get_setting(USER_MODIFIED_PROMPT_APPEND_SETTING) or {}
    if not isinstance(raw, dict):
        return set()
    recorded = raw.get(pack_id) or []
    if not isinstance(recorded, list):
        return set()
    return {str(item) for item in recorded if str(item).strip()}


def _record_prompt_append(store: Any, pack_id: str, grant_id: str) -> None:
    if store is None or not hasattr(store, "get_setting") or not hasattr(store, "set_setting"):
        return
    raw = store.get_setting(USER_MODIFIED_PROMPT_APPEND_SETTING) or {}
    if not isinstance(raw, dict):
        raw = {}
    current = [str(item) for item in (raw.get(pack_id) or []) if str(item).strip()]
    if grant_id not in current:
        current.append(grant_id)
    raw[pack_id] = current
    store.set_setting(USER_MODIFIED_PROMPT_APPEND_SETTING, raw)


def _join_authoring_paragraph(prompt: str) -> str:
    body = prompt or ""
    paragraph = DEVELOPER_AUTHORING_PROMPT_PARAGRAPH
    if body.endswith("\n\n"):
        return body + paragraph
    if body.endswith("\n"):
        return body + "\n" + paragraph
    if body:
        return body + "\n\n" + paragraph
    return paragraph


def apply_user_modified_developer_authoring_prompt(*, pack_id: str, store: Any) -> None:
    """Append one authoring paragraph onto a user_modified developer prompt [CARD-433].

    The caller already proved ``user_modified``. Existing prompt text stays.
    A prompt that already mentions ``scaffold_agent_pack`` is left alone and is
    not recorded, so a later removal of that mention can still receive the
    paragraph. After this function appends once, a later deletion stays deleted.
    Allowlists and MCP servers are not changed.
    """
    if pack_id != "developer" or store is None:
        return
    if DEVELOPER_AUTHORING_PROMPT_GRANT_ID in _recorded_prompt_appends(store, pack_id):
        return

    raw = store.get_agent_profile(pack_id) if hasattr(store, "get_agent_profile") else None
    override = store.get_agent_override(pack_id) if hasattr(store, "get_agent_override") else None
    if raw is None and override is None:
        return

    if override is not None and (getattr(override, "system_prompt", None) or ""):
        visible = override.system_prompt
        source = "override"
    elif raw is not None:
        visible = getattr(raw, "system_prompt", None) or ""
        source = "profile"
    else:
        return
    if SCAFFOLD_AGENT_PACK_TOOL in visible:
        return

    updated = _join_authoring_paragraph(visible)
    changed = False
    if source == "override" and hasattr(store, "save_agent_override"):
        override.system_prompt = updated
        # CARD-449: automated grant must not set content lock
        # override.user_modified = True
        store.save_agent_override(override)
        changed = True
        if raw is not None and hasattr(store, "save_custom_agent_profile"):
            profile_prompt = getattr(raw, "system_prompt", None) or ""
            if profile_prompt == visible:
                raw.system_prompt = updated
                # CARD-449: automated grant must not set content lock
                # raw.user_modified = True
                store.save_custom_agent_profile(raw)
    elif source == "profile" and raw is not None and hasattr(store, "save_custom_agent_profile"):
        raw.system_prompt = updated
        # CARD-449: automated grant must not set content lock
        # raw.user_modified = True
        store.save_custom_agent_profile(raw)
        changed = True

    if not changed:
        return
    _record_prompt_append(store, pack_id, DEVELOPER_AUTHORING_PROMPT_GRANT_ID)
    logger.info(
        "Appended authoring paragraph onto user_modified %s prompt; existing text left in place",
        pack_id,
    )


# CARD-426 / ADR-0056 exception. Append-only warning on one skill file.
NATIVE_TOOL_ENGINEERING_SKILL_ID = "native-tool-engineering"
LEGACY_LOADER_WARNING_MARKER = "<!-- autoreiv:native-tool-legacy-loader -->"
LEGACY_LOADER_WARNING_HEADING = "## Not the legacy pack loader"


def skill_body_has_legacy_loader_warning(text: str) -> bool:
    """True when the live runbook already carries the legacy-loader warning."""
    if LEGACY_LOADER_WARNING_MARKER in (text or ""):
        return True
    for line in (text or "").replace("\r\n", "\n").split("\n"):
        if line.strip() == LEGACY_LOADER_WARNING_HEADING:
            return True
    return False


def extract_legacy_loader_warning_block(seed_text: str) -> str:
    """Seed warning section, from its heading through the line before the next heading.

    Empty when the seed is missing the heading or the stable marker. Callers must
    not invent a warning block.
    """
    lines = (seed_text or "").replace("\r\n", "\n").split("\n")
    start = None
    for index, line in enumerate(lines):
        if line.strip() == LEGACY_LOADER_WARNING_HEADING:
            start = index
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    block = "\n".join(lines[start:end]).strip()
    if LEGACY_LOADER_WARNING_MARKER not in block:
        return ""
    return block + "\n"


def append_legacy_loader_warning_block(live_text: str, block: str) -> str:
    """Append the warning. Return the original text when it is already present."""
    if skill_body_has_legacy_loader_warning(live_text):
        return live_text
    warning = (block or "").replace("\r\n", "\n").strip("\n")
    if not warning or LEGACY_LOADER_WARNING_MARKER not in warning:
        return live_text
    warning = warning + "\n"
    if live_text.endswith("\n\n"):
        return live_text + warning
    if live_text.endswith("\n"):
        return live_text + "\n" + warning
    return live_text + "\n\n" + warning


def refresh_user_modified_native_tool_engineering_warning(dest_pack: Path, seed_pack: Path) -> bool:
    """Append the seed legacy-loader warning onto one user_modified developer skill [CARD-426].

    Does not replace the file. A body that already has the marker or the warning
    heading is left byte-for-byte alone. Other skill files are not opened.
    """
    live = Path(dest_pack) / "skills" / NATIVE_TOOL_ENGINEERING_SKILL_ID / "SKILL.md"
    seed = Path(seed_pack) / "skills" / NATIVE_TOOL_ENGINEERING_SKILL_ID / "SKILL.md"
    if not live.is_file() or not seed.is_file():
        return False
    try:
        live_text = live.read_text(encoding="utf-8")
        seed_text = seed.read_text(encoding="utf-8")
    except OSError:
        logger.warning(
            "Could not read native-tool-engineering skill for legacy-loader warning refresh",
            exc_info=True,
        )
        return False
    if skill_body_has_legacy_loader_warning(live_text):
        return False
    block = extract_legacy_loader_warning_block(seed_text)
    if not block:
        logger.warning("Seed native-tool-engineering skill has no legacy-loader warning block; skip append")
        return False
    updated = append_legacy_loader_warning_block(live_text, block)
    if updated == live_text:
        return False
    try:
        live.write_text(updated, encoding="utf-8")
    except OSError:
        logger.warning(
            "Could not append legacy-loader warning onto %s",
            live,
            exc_info=True,
        )
        return False
    logger.info(
        "Appended legacy-loader warning onto user_modified developer skill %s; operator text left in place",
        live,
    )
    return True


def _is_user_modified(profile: Any, store: Any = None) -> bool:
    if bool(getattr(profile, "user_modified", False)):
        return True
    if store is not None and hasattr(store, "get_agent_override"):
        try:
            ov = store.get_agent_override(getattr(profile, "id", None) or getattr(profile, "agent_id", None))
            if ov is not None and bool(getattr(ov, "user_modified", False)):
                return True
        except Exception:
            pass
    return False


RETIRED_TOOL_NAMES: tuple[str, ...] = (
    "get_or_create_weekly_note",
    "log_daily_work_item",
    "complete_weekly_task",
    "rollover_weekly_tasks",
    "get_weekly_summary",
    "list_wiki_templates",
    "get_wiki_template",
    "launch_factory_training",  # retired Factory dispatch [CARD-497 D12]
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
    """Copy platform pack folders into ``packs_path`` when dest is missing (first install).

    Never overwrites an existing dest. Upgrades / stale repair are owned by
    ``promote_platform_packs`` [CARD-443]. Returns ids copied.
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



def refresh_live_pack_json_skill_projection(dest_pack: Path, pack_data: dict) -> bool:
    """Merge seed skill projection into live pack.json without wiping local extras.

    SQLite remains sole writer for profiles; pack.json is an export projection used by
    Agent Studio ``pack_skills``. When a non-user_modified hash-gated seed apply runs,
    keep that projection honest for skills / allowlist / tools / Learning OS prompt.
    """
    dest_json = Path(dest_pack) / "pack.json"
    if not dest_json.is_file():
        return False
    try:
        live = json.loads(dest_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(live, dict):
        return False

    changed = False
    for key in (
        "skills",
        "allowed_skill",
        "pack_tool_names",
        "system_prompt",
        "description",
        "name",
        "tone",
        "avatar_icon",
        "purpose",
        "model",
        "show_in_chat",
        "schema_version",
    ):
        if key not in pack_data:
            continue
        if live.get(key) != pack_data.get(key):
            live[key] = pack_data.get(key)
            changed = True
    if not changed:
        return False
    dest_json.write_text(json.dumps(live, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info("Refreshed live pack.json skill projection for %s", dest_pack.name)
    return True


def install_platform_agent_packs(
    data_dir: Union[str, Path],
    agent_registry: Any,
    tool_registry: Any = None,
    *,
    checkout_root: Optional[Union[str, Path]] = None,
) -> list[str]:
    """Copy missing platform packs, promote stale AppData copies, import unregistered ids.

    CARD-443: upgrade path is ``promote_platform_packs`` (hash-gated, user_modified-safe,
    shipped-prompt baseline for system_prompt, preserves max_turns/model). First install
    still uses ``seed_platform_pack_folders`` for missing destinations.
    ``agent-packs/`` is never scanned.
    """
    import json

    from src.application.agent_packs.service import AgentPackService
    from src.domain.kernel.models import AgentOrigin
    from src.infrastructure.skills.reconciler import DeclarativePackReconciler

    root = Path(data_dir)
    packs_path = root / "packs"

    reconciler = DeclarativePackReconciler(
        data_dir=root,
        state_store=getattr(agent_registry, "state_store", None),
        agent_registry=agent_registry,
    )
    reconciler.reconcile()

    cleanup_orphaned_platform_packs(packs_path, agent_registry=agent_registry)
    seeded = seed_platform_pack_folders(packs_path, checkout_root=checkout_root)
    sync_checkout_example_user_packs(packs_path, checkout_root=checkout_root)

    report = promote_platform_packs(
        root,
        agent_registry,
        tool_registry,
        checkout_root=checkout_root,
        pack_ids=ALL_PLATFORM_PACK_IDS,
    )
    # CARD-445: one-time 10 -> 50 turn budget upgrade, after promotion (idempotent via settings key).
    from src.infrastructure.agents.max_turns_upgrade import apply_default_max_turns_upgrade

    try:
        apply_default_max_turns_upgrade(getattr(agent_registry, "state_store", None))
    except Exception:
        logger.exception("CARD-445 max_turns default upgrade failed")

    installed = [
        r.pack_id
        for r in report.results
        if r.status in {"promoted", "promoted_partial"} and r.pack_id in seeded
    ]
    for r in report.results:
        if r.status == "promoted" and r.pack_id not in installed:
            if "Imported" in (r.reason or ""):
                installed.append(r.pack_id)

    available = None
    if tool_registry is not None and hasattr(tool_registry, "list_tools"):
        available = {t.name for t in tool_registry.list_tools()}
    service = AgentPackService(
        data_dir=root,
        agent_registry=agent_registry,
        store=getattr(agent_registry, "state_store", None),
        available_tools=available,
    )

    if packs_path.is_dir():
        for sub in sorted(packs_path.iterdir()):
            if not sub.is_dir() or sub.name in ALL_PLATFORM_PACK_IDS or sub.name in RETIRED_PLATFORM_PACK_IDS:
                continue
            if (sub / "pack.json").is_file():
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
                            logger.info("Synchronized user pack Instructions for %s", sub.name)
                    except Exception:
                        logger.exception("Failed to sync user pack prompt for %s", sub.name)

    return installed
