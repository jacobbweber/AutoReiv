"""
The one seed for shipped routines [CARD-636].

Shipped routines are BUILTIN_ROUTINES (src/domain/routines/manifests.py), copied into the routines
table at start. Once a row exists it is Jacob's: the seed never overwrites it. Deleting a shipped
routine is remembered in the ``deleted_builtin_routines`` setting so the next start does not bring it
back. The one-time CARD-636 migration (guarded by ``routines_card636_migrated``) removes the retired
routines and their run history and rewrites the kept rows onto the new night-time schedules.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.application.routines.matcher import ScheduleMatcher
from src.domain.routines.manifests import BUILTIN_ROUTINES, REMOVED_BUILTIN_ROUTINE_IDS

logger = logging.getLogger(__name__)

DELETED_BUILTINS_SETTING = "deleted_builtin_routines"
CARD636_MIGRATION_SETTING = "routines_card636_migrated"
LEGACY_AGENT_IDS = ("assistant", "wiki", "agent-builder")
# Keys Jacob (or a run) owns on a row; the migration keeps them when it rewrites metadata.
USER_METADATA_KEYS = ("approval_mode", "run_as_job", "last_standing_job_id", "last_minted_job_ids")

BUILTIN_ROUTINE_IDS = frozenset(r.id for r in BUILTIN_ROUTINES)


def deleted_builtin_ids(store: Any) -> List[str]:
    raw = store.get_setting(DELETED_BUILTINS_SETTING, []) if hasattr(store, "get_setting") else []
    return [str(x) for x in raw] if isinstance(raw, list) else []


def remember_deleted_builtin(store: Any, routine_id: str) -> None:
    """Called when a shipped routine is deleted, so it stays deleted."""
    if routine_id not in BUILTIN_ROUTINE_IDS:
        return
    ids = deleted_builtin_ids(store)
    if routine_id not in ids:
        store.set_setting(DELETED_BUILTINS_SETTING, ids + [routine_id])


def migrate_card636(store: Any, now: Optional[datetime] = None) -> Dict[str, Any]:
    """One time: drop retired routines + their runs; put kept rows on the manifest schedule."""
    if store.get_setting(CARD636_MIGRATION_SETTING, False):
        return {"ran": False}
    now = now or datetime.now(timezone.utc)
    removed: Dict[str, int] = {}
    for rid in REMOVED_BUILTIN_ROUTINE_IDS:
        runs = store.delete_routine_runs(rid)
        row = store.delete_routine(rid)
        if row or runs:
            removed[rid] = runs
    rewritten: List[str] = []
    for shipped in BUILTIN_ROUTINES:
        row = store.get_routine(shipped.id)
        if row is None:
            continue
        old_meta = row.metadata or {}
        row.name = shipped.name
        row.description = shipped.description
        row.prompt = shipped.prompt
        row.schedule_type = shipped.schedule_type
        row.interval_seconds = shipped.interval_seconds
        row.cron_expression = shipped.cron_expression
        row.enabled = shipped.enabled
        row.metadata = {**shipped.metadata, **{k: old_meta[k] for k in USER_METADATA_KEYS if k in old_meta}}
        row.next_run_at = ScheduleMatcher.compute_next_run(row, base_time=now)
        store.save_routine(row)
        rewritten.append(shipped.id)
    store.set_setting(CARD636_MIGRATION_SETTING, True)
    logger.info("CARD-636 routine migration: removed %s; rewrote %s", removed, rewritten)
    return {"ran": True, "removed": removed, "rewritten": rewritten}


def seed_builtin_routines(store: Any, now: Optional[datetime] = None) -> None:
    """Insert missing shipped routines (never ones Jacob deleted); existing rows are left alone."""
    now = now or datetime.now(timezone.utc)
    migrate_card636(store, now)
    deleted = set(deleted_builtin_ids(store))
    for shipped in BUILTIN_ROUTINES:
        if shipped.id in deleted:
            continue
        existing = store.get_routine(shipped.id)
        if existing is None:
            row = shipped.model_copy(deep=True)
            row.next_run_at = ScheduleMatcher.compute_next_run(row, base_time=now)
            store.save_routine(row)
        elif existing.agent_id in LEGACY_AGENT_IDS:
            existing.agent_id = shipped.agent_id
            store.save_routine(existing)
