"""
Declarative Agent Pack Lifecycle Reconciliation [REQ-RECON-002, REQ-RECON-003, REQ-RECON-004].

Reconciles desired platform agent packs against runtime user data (%LOCALAPPDATA%\\AutoReiv\\).
Ensures retired or abandoned platform packs are cleanly purged from disk and SQLite,
while strictly preserving user-created custom agents (origin == AgentOrigin.CUSTOM).
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from src.infrastructure.skills.platform_packs import PLATFORM_PACK_IDS, RETIRED_PLATFORM_PACK_IDS

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationReport:
    purged_database_agents: list[str] = field(default_factory=list)
    purged_pack_directories: list[str] = field(default_factory=list)
    preserved_custom_agents: list[str] = field(default_factory=list)
    active_platform_agents: list[str] = field(default_factory=list)


class DeclarativePackReconciler:
    """Audits and reconciles agent packs in user data against declarative platform definitions."""

    def __init__(
        self,
        data_dir: Path | str,
        state_store: Any,
        agent_registry: Any = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.packs_dir = self.data_dir / "packs"
        self.store = state_store
        self.registry = agent_registry

    def reconcile(
        self,
        desired_platform_ids: Sequence[str] | None = None,
        retired_platform_ids: Sequence[str] | None = None,
    ) -> ReconciliationReport:
        desired = tuple(desired_platform_ids) if desired_platform_ids is not None else PLATFORM_PACK_IDS
        retired = set(retired_platform_ids) if retired_platform_ids is not None else set(RETIRED_PLATFORM_PACK_IDS)

        report = ReconciliationReport()
        self.packs_dir.mkdir(parents=True, exist_ok=True)

        # 1. Inspect and reconcile SQLite custom_agents
        if self.store is not None and hasattr(self.store, "list_custom_agent_profiles"):
            try:
                profiles = self.store.list_custom_agent_profiles()
            except Exception:
                logger.exception("Failed to query custom_agents during reconciliation")
                profiles = []

            for profile in profiles:
                agent_id = profile.id
                # Retired pack id: purge from database and disk
                is_retired = agent_id in retired

                if is_retired:
                    logger.info("Purging obsolete/retired agent from database: %s", agent_id)
                    try:
                        self.store.delete_agent_profile(agent_id, purge_history=True)
                        report.purged_database_agents.append(agent_id)
                    except Exception:
                        logger.exception("Failed to delete agent profile from database: %s", agent_id)

                    # Also unregister from memory registry if present
                    self._unregister_from_registry(agent_id)

                    # Also remove pack directory if it exists
                    pack_folder = self.packs_dir / agent_id
                    if pack_folder.is_dir():
                        try:
                            shutil.rmtree(pack_folder, ignore_errors=True)
                            report.purged_pack_directories.append(agent_id)
                            logger.info("Purged pack folder for: %s", agent_id)
                        except Exception:
                            logger.exception("Failed to delete pack folder: %s", pack_folder)
                elif agent_id in desired:
                    report.active_platform_agents.append(agent_id)
                else:
                    report.preserved_custom_agents.append(agent_id)

        # 2. Inspect filesystem for any orphaned retired packs
        if self.packs_dir.is_dir():
            for sub in sorted(self.packs_dir.iterdir()):
                if not sub.is_dir():
                    continue
                pack_name = sub.name

                if pack_name in retired:
                    if pack_name not in report.purged_pack_directories:
                        try:
                            shutil.rmtree(sub, ignore_errors=True)
                            report.purged_pack_directories.append(pack_name)
                            logger.info("Purged retired agent pack folder: %s", sub)
                        except Exception:
                            logger.exception("Failed to purge retired pack directory: %s", sub)
                    self._unregister_from_registry(pack_name)
                    continue

        return report

    def _unregister_from_registry(self, agent_id: str) -> None:
        if self.registry is None:
            return
        if hasattr(self.registry, "delete_custom_agent"):
            try:
                self.registry.delete_custom_agent(agent_id, purge_history=True)
            except Exception:
                pass
        if hasattr(self.registry, "unregister_agent"):
            try:
                self.registry.unregister_agent(agent_id)
            except Exception:
                pass
        if hasattr(self.registry, "_agents"):
            self.registry._agents.pop(agent_id, None)
        if hasattr(self.registry, "_profiles"):
            self.registry._profiles.pop(agent_id, None)
