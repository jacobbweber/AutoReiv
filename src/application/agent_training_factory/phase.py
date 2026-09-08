"""Phase protocol for Agent Training Factory (CARD-171)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Protocol, runtime_checkable


@dataclass
class PhaseResult:
    """Outcome of one phase execution."""

    outcome: str = "ok"  # ok | fail | need_human | skip
    message: str = ""
    artifacts: Dict[str, Any] = field(default_factory=dict)
    waiting: bool = False  # True when HITL gate holds the job


@runtime_checkable
class Phase(Protocol):
    """Thin phase contract: context → LLM/tools → artifacts → done-when."""

    id: str
    label: str

    async def run(self, ctx: "PhaseContext") -> PhaseResult:
        """Execute the phase against the shared job context."""
        ...


@dataclass
class PhaseContext:
    """Shared mutable context passed through the pipeline."""

    job: Any
    repo: Any
    gateway: Any = None
    wiki: Any = None
    store: Any = None
    data_dir: Any = None
    battery: Any = None
    extras: Dict[str, Any] = field(default_factory=dict)

    @property
    def job_id(self) -> str:
        return self.job.id

    @property
    def agent_id(self) -> str:
        return self.job.target_agent_id

    @property
    def seed_intent(self) -> str:
        return self.job.seed_intent or ""

    @property
    def objectives(self) -> list:
        """Job objectives plus facts from the latest orchestrator work packet."""
        merged: list = []
        seen = set()
        for item in list(getattr(self.job, "objectives", None) or []):
            s = str(item).strip()
            if s and s not in seen:
                seen.add(s)
                merged.append(s)
        try:
            packets = self.repo.list_packets(self.job_id) if self.repo is not None else []
        except Exception:
            packets = []
        for pkt in reversed(packets or []):
            role = getattr(pkt, "sender_role", "") or ""
            payload = getattr(pkt, "payload", None) or {}
            if role != "orchestrator" and "facts" not in payload:
                continue
            facts = payload.get("facts") if isinstance(payload, dict) else None
            if not isinstance(facts, list):
                continue
            for item in facts:
                s = str(item).strip()
                if s and s not in seen:
                    seen.add(s)
                    merged.append(s)
            break
        return merged

    @property
    def db_path(self) -> str | None:
        if hasattr(self.store, "db_path") and self.store.db_path:
            return str(self.store.db_path)
        if hasattr(self.repo, "db_path") and self.repo.db_path:
            return str(self.repo.db_path)
        if self.data_dir:
            from pathlib import Path
            p = Path(self.data_dir) / "database" / "autoreiv.db"
            if p.exists():
                return str(p)
        return None

