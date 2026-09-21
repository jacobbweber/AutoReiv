"""
Data Directory Automated Backup Scheduler [CARD-404].
Runs background cadence checks and retention pruning for data directory backups.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.infrastructure.data.backup import DataDirBackupService
from src.infrastructure.data.resolver import (
    BACKUP_RETENTION_SETTING_KEY,
    BACKUP_SCHEDULE_SETTING_KEY,
    DataDirPaths,
)

logger = logging.getLogger(__name__)

CADENCE_HOURLY_SECONDS = 3600
CADENCE_DAILY_SECONDS = 86400
CADENCE_WEEKLY_SECONDS = 7 * 86400


class DataDirBackupScheduler:
    """
    Background worker periodically checking whether a scheduled backup is due
    and executing backup creation + retention pruning.
    """

    def __init__(
        self,
        paths: DataDirPaths,
        store: Any,
        *,
        interval_seconds: float = 60.0,
    ) -> None:
        self.paths = paths
        self.store = store
        self.interval_seconds = interval_seconds
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def is_backup_due(self, schedule: str, last_backup_iso: Optional[str], now: datetime) -> bool:
        """Determines if a backup is due based on schedule and last run time."""
        clean_sched = (schedule or "disabled").strip().lower()
        if clean_sched in {"disabled", "off", "none", ""}:
            return False

        if not last_backup_iso:
            # First time running under an active schedule: due!
            return True

        try:
            last_dt = datetime.fromisoformat(last_backup_iso)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
        except Exception:
            return True

        elapsed_seconds = (now - last_dt).total_seconds()

        if clean_sched == "hourly":
            return elapsed_seconds >= CADENCE_HOURLY_SECONDS
        if clean_sched == "daily":
            # Due if 24h passed OR calendar UTC date has advanced
            if elapsed_seconds >= CADENCE_DAILY_SECONDS:
                return True
            return now.date() > last_dt.date() and elapsed_seconds >= 3600
        if clean_sched == "weekly":
            return elapsed_seconds >= CADENCE_WEEKLY_SECONDS

        # Support interval in seconds (e.g. for testing or custom interval)
        try:
            custom_interval = float(clean_sched)
            return elapsed_seconds >= custom_interval
        except ValueError:
            pass

        return False

    async def tick(self, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        Evaluate if a backup is due; if so, create backup and prune.
        Returns execution summary dict if a backup was created, else None.
        """
        if not self.store or not hasattr(self.store, "get_setting"):
            return None

        schedule = self.store.get_setting(BACKUP_SCHEDULE_SETTING_KEY, "disabled")
        last_backup_iso = self.store.get_setting("last_backup_time", None)
        current_time = now or datetime.now(timezone.utc)

        if not self.is_backup_due(schedule, last_backup_iso, current_time):
            return None

        backup_service = DataDirBackupService(self.paths)
        backup_dir = getattr(self.paths, "backups_path", None)

        try:
            dest = backup_service.backup(backup_dir=backup_dir, now=current_time)
            retention = int(self.store.get_setting(BACKUP_RETENTION_SETTING_KEY, 7))
            pruned = backup_service.prune_backups(retention_count=retention, backup_dir=backup_dir)

            now_iso = current_time.isoformat()
            self.store.set_setting("last_backup_time", now_iso)

            logger.info(
                "Scheduled backup completed: %s (pruned %d older archives)",
                dest.name,
                len(pruned),
            )
            return {
                "status": "created",
                "filename": dest.name,
                "path": str(dest.resolve()),
                "size_bytes": dest.stat().st_size,
                "pruned": pruned,
                "created_at": now_iso,
            }
        except Exception as exc:
            logger.error("Scheduled backup failed: %s", exc, exc_info=True)
            return None

    async def start(self) -> None:
        """Runs the periodic loop until stop() is called."""
        self._running = True
        logger.info("DataDirBackupScheduler started (interval: %.1fs)", self.interval_seconds)
        while self._running:
            try:
                await self.tick()
            except Exception as exc:
                logger.error("Error in DataDirBackupScheduler tick: %s", exc, exc_info=True)
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
        self._running = False
        logger.info("DataDirBackupScheduler stopped")

    async def stop(self) -> None:
        """Signals the background loop to terminate."""
        self._running = False
