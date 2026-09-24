"""Platform pack -> AppData promotion + stored-profile resync [CARD-443 / ADR-0056].

Trigger: app startup via ``install_platform_agent_packs`` and operator
``POST /api/platform-packs/sync``.

Rules:
- ``user_modified`` packs are never overwritten; return a deterministic skip with
  an operator resolution path.
- Non-user_modified packs: refresh AppData ``pack.json`` + ``skills/*/SKILL.md``
  from ``platform-packs/<id>/``, remove stock skills retired from the platform
  seed (never prune operator-only skill dirs), and resync pack-owned SQLite
  fields (system_prompt when still at shipped baseline, allowed_skill,
  pack_tool_names / allowed_tool_names). Preserve operator fields: max_turns,
  model, and unrelated tool ticks.
- Generic for every platform pack id; no skill-name special cases.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence, Union

logger = logging.getLogger(__name__)

PLATFORM_SHIPPED_PROMPT_SETTING = "platform_shipped_prompt_hashes"
PLATFORM_PACK_SYNC_REPORT_SETTING = "platform_pack_sync_last_report"

RESOLUTION_USER_MODIFIED = (
    "Pack is locked (user_modified). To accept the platform seed: "
    "call mark_agent_user_modified('<pack_id>', modified=False) on the state store "
    "(or POST /api/agents/<pack_id>/accept-platform-seed), then restart serve or "
    "POST /api/platform-packs/sync. Operator fields such as max_turns stay until "
    "you change them again in Agent Studio."
)


@dataclass
class PackSyncOutcome:
    pack_id: str
    status: str  # promoted | promoted_partial | skipped_user_modified | unchanged | missing_source | missing_dest
    reason: str = ""
    resolution: str = ""
    source_path: str = ""
    destination_path: str = ""
    skipped_fields: list[str] = field(default_factory=list)
    updated_skills: list[str] = field(default_factory=list)
    removed_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlatformPackSyncReport:
    triggered_at: str
    results: list[PackSyncOutcome] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "triggered_at": self.triggered_at,
            "results": [r.to_dict() for r in self.results],
        }


def prompt_content_hash(prompt: str) -> str:
    return hashlib.sha256((prompt or "").encode("utf-8")).hexdigest()


def _shipped_prompt_map(store: Any) -> dict[str, str]:
    if store is None or not hasattr(store, "get_setting"):
        return {}
    raw = store.get_setting(PLATFORM_SHIPPED_PROMPT_SETTING) or {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if str(k).strip() and str(v).strip()}


def _set_shipped_prompt_hash(store: Any, pack_id: str, prompt: str) -> None:
    if store is None or not hasattr(store, "set_setting"):
        return
    current = _shipped_prompt_map(store)
    current[pack_id] = prompt_content_hash(prompt)
    store.set_setting(PLATFORM_SHIPPED_PROMPT_SETTING, current)


def _persist_report(store: Any, report: PlatformPackSyncReport) -> None:
    if store is None or not hasattr(store, "set_setting"):
        return
    store.set_setting(PLATFORM_PACK_SYNC_REPORT_SETTING, report.to_dict())


def get_last_platform_pack_sync_report(store: Any) -> Optional[dict[str, Any]]:
    if store is None or not hasattr(store, "get_setting"):
        return None
    raw = store.get_setting(PLATFORM_PACK_SYNC_REPORT_SETTING)
    return raw if isinstance(raw, dict) else None


def _read_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _preserve_operator_scalars(existing: Any) -> tuple[Any, Any]:
    return getattr(existing, "max_turns", None), getattr(existing, "model", None)


def _restore_operator_scalars(existing: Any, max_turns: Any, model: Any) -> None:
    if max_turns is not None:
        existing.max_turns = max_turns
    if model is not None:
        existing.model = model


def _sync_skill_filesystem(
    *,
    src: Path,
    dest: Path,
    previous_stock_skills: set[str],
    new_stock_skills: set[str],
) -> tuple[list[str], list[str]]:
    """Refresh stock skill bodies from platform; remove retired stock dirs only."""
    updated: list[str] = []
    removed: list[str] = []
    src_skills = src / "skills"
    dest_skills = dest / "skills"
    dest_skills.mkdir(parents=True, exist_ok=True)
    if src_skills.is_dir():
        for skill_dir in sorted(src_skills.iterdir()):
            if not skill_dir.is_dir():
                continue
            target = dest_skills / skill_dir.name
            if target.exists():
                shutil.copytree(skill_dir, target, dirs_exist_ok=True)
            else:
                shutil.copytree(skill_dir, target)
            updated.append(skill_dir.name)
    # Remove stock skills retired from the platform seed; never touch operator-only dirs.
    if dest_skills.is_dir():
        for skill_dir in list(dest_skills.iterdir()):
            if not skill_dir.is_dir():
                continue
            name = skill_dir.name
            if name in previous_stock_skills and name not in new_stock_skills:
                shutil.rmtree(skill_dir, ignore_errors=True)
                removed.append(name)
    return updated, removed


def promote_one_platform_pack(
    *,
    pack_id: str,
    data_dir: Path,
    agent_registry: Any,
    tool_registry: Any = None,
    checkout_root: Optional[Union[str, Path]] = None,
) -> PackSyncOutcome:
    """Promote one platform pack into AppData + resync pack-owned SQLite fields."""
    from src.application.agent_packs.schema import tools_for_platform_skills
    from src.application.agent_packs.service import AgentPackService
    from src.domain.kernel.models import AgentOrigin
    from src.infrastructure.skills.platform_packs import (
        RETIRED_TOOL_NAMES,
        _is_user_modified,
        apply_user_modified_additive_skill_grants,
        apply_user_modified_developer_authoring_prompt,
        compute_platform_seed_hash,
        platform_packs_root,
        refresh_live_pack_json_skill_projection,
        refresh_user_modified_native_tool_engineering_warning,
    )

    root = Path(data_dir)
    packs_path = root / "packs"
    src = platform_packs_root(checkout_root) / pack_id
    dest = packs_path / pack_id
    source_path = str(src)
    destination_path = str(dest)

    if not (src / "pack.json").is_file():
        return PackSyncOutcome(
            pack_id=pack_id,
            status="missing_source",
            reason=f"Platform pack missing at {src}",
            source_path=source_path,
            destination_path=destination_path,
        )

    available = None
    if tool_registry is not None and hasattr(tool_registry, "list_tools"):
        available = {t.name for t in tool_registry.list_tools()}
    store = getattr(agent_registry, "state_store", None)
    service = AgentPackService(
        data_dir=root,
        agent_registry=agent_registry,
        store=store,
        available_tools=available,
    )

    pack_data = _read_json(src / "pack.json") or {}
    new_prompt = pack_data.get("system_prompt") or ""
    new_allowed_skill = list(pack_data.get("allowed_skill") or [])
    new_pack_tools = list(pack_data.get("pack_tool_names") or [])
    platform_tools = tools_for_platform_skills(new_allowed_skill)
    merged_tools = list(new_pack_tools) + [t for t in platform_tools if t not in new_pack_tools]
    seed_hash = compute_platform_seed_hash(pack_data, src)
    seed_version = str(pack_data.get("version") or pack_data.get("seed_version") or "1")

    # First install: copy tree if dest missing
    if not dest.exists():
        shutil.copytree(src, dest)
        logger.info("Seeded platform pack %s -> %s", pack_id, dest)

    if not (dest / "pack.json").is_file():
        return PackSyncOutcome(
            pack_id=pack_id,
            status="missing_dest",
            reason=f"AppData pack missing pack.json at {dest}",
            source_path=source_path,
            destination_path=destination_path,
        )

    existing = agent_registry.get_agent(pack_id) if agent_registry is not None else None
    if existing is None:
        # Import into registry (first registration)
        try:
            profile = service.import_path(dest)
            if profile is not None:
                if getattr(profile, "origin", None) != AgentOrigin.PACK:
                    profile.origin = AgentOrigin.PACK
                profile.seed_content_hash = seed_hash
                profile.seed_version = seed_version
                profile.user_modified = False
                if store and hasattr(store, "save_agent_profile"):
                    store.save_agent_profile(profile)
                _set_shipped_prompt_hash(store, pack_id, new_prompt)
            return PackSyncOutcome(
                pack_id=pack_id,
                status="promoted",
                reason="Imported missing platform pack into registry",
                source_path=source_path,
                destination_path=destination_path,
                updated_skills=list(new_allowed_skill),
            )
        except Exception as exc:
            logger.exception("Failed to import platform pack %s", pack_id)
            return PackSyncOutcome(
                pack_id=pack_id,
                status="missing_dest",
                reason=f"Import failed: {exc}",
                source_path=source_path,
                destination_path=destination_path,
            )

    if getattr(existing, "origin", None) != AgentOrigin.PACK:
        existing.origin = AgentOrigin.PACK
        if store and hasattr(store, "save_custom_agent_profile"):
            store.save_custom_agent_profile(existing)

    user_pack_tools: list[str] = []
    live_pack = _read_json(dest / "pack.json") or {}
    user_pack_tools = list(live_pack.get("allowed_tool_names") or [])

    stored_hash = getattr(existing, "seed_content_hash", None)
    user_mod = _is_user_modified(existing, store)
    previous_stock = set(getattr(existing, "allowed_skill", None) or [])
    new_stock = set(new_allowed_skill)

    if user_mod:
        if stored_hash and stored_hash != seed_hash:
            logger.info(
                "Upstream seed update available for %s (user_modified=true); skipping overwrite",
                pack_id,
            )
        # Retire permanently removed tools only; copy missing skill bodies only
        current_tools = list(getattr(existing, "allowed_tool_names", None) or [])
        filtered = [t for t in current_tools if t not in RETIRED_TOOL_NAMES]
        if filtered != current_tools:
            keep_max, keep_model = _preserve_operator_scalars(existing)
            existing.allowed_tool_names = filtered
            existing.user_modified = True
            _restore_operator_scalars(existing, keep_max, keep_model)
            if store and hasattr(store, "save_custom_agent_profile"):
                store.save_custom_agent_profile(existing)
        src_skills = src / "skills"
        dest_skills = dest / "skills"
        if src_skills.is_dir():
            dest_skills.mkdir(parents=True, exist_ok=True)
            for s in src_skills.iterdir():
                if s.is_dir() and not (dest_skills / s.name).exists():
                    shutil.copytree(s, dest_skills / s.name)
        if pack_id == "developer":
            try:
                refresh_user_modified_native_tool_engineering_warning(dest, src)
            except Exception:
                logger.exception("Legacy-loader warning refresh failed for user_modified developer")
        apply_user_modified_additive_skill_grants(pack_id=pack_id, pack_data=pack_data, store=store)
        apply_user_modified_developer_authoring_prompt(pack_id=pack_id, store=store)
        outcome = PackSyncOutcome(
            pack_id=pack_id,
            status="skipped_user_modified",
            reason="user_modified=true; platform pack promotion refused to overwrite operator content",
            resolution=RESOLUTION_USER_MODIFIED.replace("<pack_id>", pack_id),
            source_path=source_path,
            destination_path=destination_path,
        )
        logger.warning(
            "Platform pack sync skipped for %s: user_modified. Resolution: %s",
            pack_id,
            outcome.resolution,
        )
        return outcome

    # Idempotent short-circuit when seed unchanged and profile already matches
    if stored_hash and stored_hash == seed_hash:
        live_prompt = getattr(existing, "system_prompt", None) or ""
        if live_prompt == new_prompt and list(getattr(existing, "allowed_skill", None) or []) == new_allowed_skill:
            return PackSyncOutcome(
                pack_id=pack_id,
                status="unchanged",
                reason="seed_content_hash already matches platform seed",
                source_path=source_path,
                destination_path=destination_path,
            )

    # First Hybrid C+ boot (no stored hash): dual-read cutover
    if not stored_hash:
        live_prompt = getattr(existing, "system_prompt", None) or ""
        live_skills = list(getattr(existing, "allowed_skill", None) or [])
        live_tools = [
            t for t in (getattr(existing, "allowed_tool_names", None) or []) if t not in RETIRED_TOOL_NAMES
        ]
        seed_tools = [t for t in merged_tools if t not in RETIRED_TOOL_NAMES]
        diverged = (
            live_prompt != new_prompt
            or live_skills != new_allowed_skill
            or set(live_tools) != set(seed_tools)
        )
        if diverged:
            keep_max, keep_model = _preserve_operator_scalars(existing)
            existing.user_modified = True
            existing.seed_content_hash = seed_hash
            existing.seed_version = seed_version
            _restore_operator_scalars(existing, keep_max, keep_model)
            if store and hasattr(store, "save_custom_agent_profile"):
                store.save_custom_agent_profile(existing)
            logger.info(
                "Cutover: marked %s user_modified (live diverged from seed); skipping overwrite",
                pack_id,
            )
            return PackSyncOutcome(
                pack_id=pack_id,
                status="skipped_user_modified",
                reason="cutover: live profile diverged from seed with no stored hash; marked user_modified",
                resolution=RESOLUTION_USER_MODIFIED.replace("<pack_id>", pack_id),
                source_path=source_path,
                destination_path=destination_path,
            )

    # --- Clean promotion path ---
    keep_max, keep_model = _preserve_operator_scalars(existing)
    skipped_fields: list[str] = []

    baselines = _shipped_prompt_map(store)
    baseline = baselines.get(pack_id)
    stored_prompt = getattr(existing, "system_prompt", None) or ""
    prompt_at_baseline = baseline is None or prompt_content_hash(stored_prompt) == baseline
    applied_prompt = stored_prompt
    if new_prompt and prompt_at_baseline:
        if stored_prompt != new_prompt:
            existing.system_prompt = new_prompt
        applied_prompt = new_prompt
    elif new_prompt and stored_prompt != new_prompt:
        skipped_fields.append("system_prompt")
        logger.info(
            "Skipped system_prompt resync for %s: stored prompt diverged from shipped baseline",
            pack_id,
        )

    final_tools = list(merged_tools)
    for tname in user_pack_tools:
        if tname not in final_tools:
            final_tools.append(tname)
    final_tools = [t for t in final_tools if t not in RETIRED_TOOL_NAMES]

    existing.allowed_skill = new_allowed_skill
    existing.pack_tool_names = new_pack_tools
    existing.allowed_tool_names = final_tools
    existing.seed_content_hash = seed_hash
    existing.seed_version = seed_version
    existing.user_modified = False
    _restore_operator_scalars(existing, keep_max, keep_model)

    if store and hasattr(store, "save_custom_agent_profile"):
        store.save_custom_agent_profile(existing)
        logger.info("Applied hash-gated platform seed for %s", pack_id)

    if store and hasattr(store, "get_agent_override") and hasattr(store, "save_agent_override"):
        ov = store.get_agent_override(pack_id)
        if ov is not None and not bool(getattr(ov, "user_modified", False)):
            if "system_prompt" not in skipped_fields:
                ov.system_prompt = applied_prompt
            ov.allowed_tool_names = final_tools
            ov.pack_tool_names = new_pack_tools
            ov.allowed_skill = new_allowed_skill
            ov.seed_content_hash = seed_hash
            ov.seed_version = seed_version
            ov.user_modified = False
            if keep_max is not None:
                ov.max_turns = keep_max
            if keep_model is not None:
                ov.model = keep_model
            store.save_agent_override(ov)

    updated_skills, removed_skills = _sync_skill_filesystem(
        src=src,
        dest=dest,
        previous_stock_skills=previous_stock,
        new_stock_skills=new_stock,
    )
    # pack.json projection: use platform pack_data but keep operator-edited prompt in projection
    # when system_prompt was skipped
    projection = dict(pack_data)
    if "system_prompt" in skipped_fields:
        projection["system_prompt"] = stored_prompt
    try:
        refresh_live_pack_json_skill_projection(dest, projection)
    except Exception:
        logger.exception("Failed to refresh live pack.json projection for %s", pack_id)

    if "system_prompt" not in skipped_fields and new_prompt:
        _set_shipped_prompt_hash(store, pack_id, new_prompt)
    elif baseline is None and stored_prompt:
        # Establish baseline without clobbering an operator-held prompt
        _set_shipped_prompt_hash(store, pack_id, stored_prompt)

    status = "promoted_partial" if skipped_fields else "promoted"
    return PackSyncOutcome(
        pack_id=pack_id,
        status=status,
        reason="platform pack promoted into AppData and pack-owned profile fields resynced"
        + (f"; skipped fields: {', '.join(skipped_fields)}" if skipped_fields else ""),
        source_path=source_path,
        destination_path=destination_path,
        skipped_fields=skipped_fields,
        updated_skills=updated_skills,
        removed_skills=removed_skills,
    )


def promote_platform_packs(
    data_dir: Union[str, Path],
    agent_registry: Any,
    tool_registry: Any = None,
    *,
    checkout_root: Optional[Union[str, Path]] = None,
    pack_ids: Optional[Sequence[str]] = None,
) -> PlatformPackSyncReport:
    """Promote platform packs into AppData and resync pack-owned profile fields [CARD-443]."""
    from src.infrastructure.skills.platform_packs import ALL_PLATFORM_PACK_IDS

    ids: Iterable[str] = tuple(pack_ids) if pack_ids is not None else ALL_PLATFORM_PACK_IDS
    report = PlatformPackSyncReport(
        triggered_at=datetime.now(timezone.utc).isoformat(),
        results=[],
    )
    for pack_id in ids:
        outcome = promote_one_platform_pack(
            pack_id=pack_id,
            data_dir=Path(data_dir),
            agent_registry=agent_registry,
            tool_registry=tool_registry,
            checkout_root=checkout_root,
        )
        report.results.append(outcome)

    store = getattr(agent_registry, "state_store", None)
    _persist_report(store, report)
    return report
