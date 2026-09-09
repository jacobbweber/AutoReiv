"""FactoryOrchestrator — Agent Training Factory built-in system capability (CARD-171).

One orchestrator, phases only. Replaces costume FactoryRunner persona walker.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.registry import (
    PHASE_DONE,
    PHASE_PROMOTE,
    PhaseRegistry,
    default_registry,
)
from src.application.orchestration.verification_battery import VerificationBatteryService
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository

logger = logging.getLogger(__name__)


def format_phase_duration(duration_ms: Optional[int]) -> str:
    """Format milliseconds into a human-readable duration badge (e.g. '850ms', '1.5s') [REQ-FACT-051]."""
    if duration_ms is None:
        return ""
    if duration_ms < 1000:
        return f"{duration_ms}ms"
    secs = round(duration_ms / 1000.0, 1)
    return f"{secs:g}s"


class FactoryOrchestrator:
    """Background worker advancing Agent Training Factory jobs through the phase registry."""

    def __init__(
        self,
        repo: FactoryPacketRepository,
        registry: Optional[PhaseRegistry] = None,
        store: Optional[Any] = None,
        data_dir: Optional[Path] = None,
        battery_service: Optional[VerificationBatteryService] = None,
        poll_interval: float = 2.0,
        gateway: Optional[Any] = None,
        wiki: Optional[Any] = None,
        engine: Optional[Any] = None,  # legacy CapabilityGraphEngine ignored
        **_kwargs: Any,
    ):
        self.repo = repo
        self.registry = registry or default_registry()
        self.store = store
        self.data_dir = Path(data_dir or "./data").resolve()
        self.battery = battery_service or VerificationBatteryService()
        self.poll_interval = poll_interval
        self.gateway = gateway
        self.wiki = wiki
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        self._running = True
        logger.info("FactoryOrchestrator (Agent Training Factory) started.")
        while self._running:
            try:
                await self.tick()
            except Exception as e:
                logger.error("FactoryOrchestrator tick error: %s", e, exc_info=True)
            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
        self._running = False

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        logger.info("FactoryOrchestrator stopped.")

    async def tick(self) -> int:
        async with self._lock:
            active_jobs = self.repo.list_jobs()
            steppable = [j for j in active_jobs if j.status in ("queued", "running")]
            stepped_count = 0
            for job in steppable:
                stepped = await self._step_job_unlocked(job.id)
                if stepped:
                    stepped_count += 1
            return stepped_count

    def _normalize_job_node(self, job) -> str:
        node = self.registry.normalize_node(job.current_node_id)
        if node != job.current_node_id:
            self.repo.update_job_status(job.id, job.status, current_node_id=node)
            job.current_node_id = node
        return node

    async def step_job(self, job_id: str) -> bool:
        # Serialize with tick() so concurrent /step + background poll cannot double-advance.
        async with self._lock:
            return await self._step_job_unlocked(job_id)

    async def _step_job_unlocked(self, job_id: str) -> bool:
        job = self.repo.get_job(job_id)
        if not job or job.status in ("done", "failed", "cancelled", "waiting_approval"):
            return False

        if job.status == "queued":
            # Guarantee Intent Distill is first even if a stale create seeded ground.
            first = self.registry.pipeline[0] if self.registry.pipeline else "intent_distill"
            node0 = self.registry.normalize_node(job.current_node_id)
            # Fresh jobs must always enter Intent Distill first (ignore stale ground seed).
            if int(job.cycles_consumed or 0) == 0 and node0 != first:
                self.repo.update_job_status(job.id, "running", current_node_id=first)
            else:
                self.repo.update_job_status(job.id, "running")
            job = self.repo.get_job(job.id)

        node = self._normalize_job_node(job)
        if node in (PHASE_DONE, "failed", "pack_finalized_node"):
            return False

        phase = self.registry.get(node)
        if phase is None:
            logger.warning("No phase registered for node %s (job %s)", node, job_id)
            return False

        ctx = PhaseContext(
            job=job,
            repo=self.repo,
            gateway=self.gateway,
            wiki=self.wiki,
            store=self.store,
            data_dir=self.data_dir,
            battery=self.battery,
        )
        start_time = asyncio.get_event_loop().time()
        result = await phase.run(ctx)
        elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

        # Record phase duration in packet payload [REQ-FACT-051]
        try:
            recent_packets = self.repo.list_packets(job.id, node_id=node)
            if recent_packets:
                last_pkt = recent_packets[-1]
                if isinstance(last_pkt.payload, dict):
                    last_pkt.payload["duration_ms"] = elapsed_ms
                    self.repo.save_packet(last_pkt)
        except Exception as e:
            logger.debug("Failed to record duration_ms on packet for node %s: %s", node, e)

        if result.waiting or node == PHASE_PROMOTE:
            self.repo.update_job_status(
                job.id,
                "waiting_approval",
                current_node_id=PHASE_PROMOTE,
                cycles_consumed=job.cycles_consumed + 1,
            )
            return False

        next_node = self.registry.next_phase(node, result.outcome)
        new_status = "running"
        if next_node == PHASE_DONE:
            new_status = "done"
        elif next_node == PHASE_PROMOTE:
            # Promote phase itself sets waiting; advance into it next tick
            new_status = "running"
        elif next_node == "failed":
            new_status = "failed"

        self.repo.update_job_status(
            job.id,
            new_status,
            current_node_id=next_node,
            cycles_consumed=job.cycles_consumed + 1,
        )
        return True


# Back-compat alias used by older imports / tests during rename
FactoryRunner = FactoryOrchestrator
