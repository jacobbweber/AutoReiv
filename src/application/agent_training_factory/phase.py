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
        return list(getattr(self.job, "objectives", None) or [])
