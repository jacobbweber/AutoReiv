"""Thin phase registry: ordered pipeline + rinse edges. No nested meta-engine (CARD-171)."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from src.application.agent_training_factory.phase import Phase

# Official pipeline node ids
PHASE_GROUND = "ground"
PHASE_BLUEPRINT = "blueprint"
PHASE_AUTHOR = "author"
PHASE_VERIFY = "verify"
PHASE_OPTIMIZE = "optimize"
PHASE_PROMOTE = "promote"
PHASE_DONE = "done"

DEFAULT_PIPELINE: List[str] = [
    PHASE_GROUND,
    PHASE_BLUEPRINT,
    PHASE_AUTHOR,
    PHASE_VERIFY,
    PHASE_OPTIMIZE,
    PHASE_PROMOTE,
]

# outcome → next phase (rinse edges included)
DEFAULT_EDGES: Dict[str, Dict[str, str]] = {
    PHASE_GROUND: {"ok": PHASE_BLUEPRINT, "fail": PHASE_GROUND},
    PHASE_BLUEPRINT: {"ok": PHASE_AUTHOR, "fail": PHASE_GROUND},
    PHASE_AUTHOR: {"ok": PHASE_VERIFY, "fail": PHASE_AUTHOR},
    PHASE_VERIFY: {"ok": PHASE_OPTIMIZE, "fail": PHASE_AUTHOR, "exhausted": "failed"},  # rinse / terminal
    PHASE_OPTIMIZE: {"ok": PHASE_PROMOTE, "fail": PHASE_AUTHOR},
    PHASE_PROMOTE: {"ok": PHASE_DONE, "approved": PHASE_DONE, "rejected": "failed"},
}

# Map legacy costume graph nodes → new phase ids (resume / in-flight jobs)
LEGACY_NODE_MAP: Dict[str, str] = {
    "socratic_handshake": PHASE_GROUND,
    "discovery_probe": PHASE_GROUND,
    "architecture_blueprint": PHASE_BLUEPRINT,
    "attempt_node": PHASE_AUTHOR,
    "conduct_node": PHASE_AUTHOR,
    "coder_node": PHASE_AUTHOR,
    "sandbox_battery_node": PHASE_VERIFY,
    "critic_signoff_node": PHASE_OPTIMIZE,
    "hitl_deploy_gate_node": PHASE_PROMOTE,
    "pack_finalized_node": PHASE_DONE,
}


class PhaseRegistry:
    """Ordered phase modules with rinse edges. Insert/reorder without rewrite."""

    def __init__(
        self,
        phases: Optional[Sequence[Phase]] = None,
        pipeline: Optional[List[str]] = None,
        edges: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        self._phases: Dict[str, Phase] = {}
        self.pipeline: List[str] = list(pipeline or DEFAULT_PIPELINE)
        self.edges: Dict[str, Dict[str, str]] = {
            k: dict(v) for k, v in (edges or DEFAULT_EDGES).items()
        }
        if phases:
            for p in phases:
                self.register(p)

    def register(self, phase: Phase) -> None:
        self._phases[phase.id] = phase

    def get(self, phase_id: str) -> Optional[Phase]:
        return self._phases.get(phase_id)

    def normalize_node(self, node_id: str) -> str:
        """Map legacy costume nodes onto the Agent Training Factory phase ids."""
        if node_id in self._phases or node_id in self.pipeline or node_id in (
            PHASE_DONE,
            "failed",
        ):
            return node_id
        return LEGACY_NODE_MAP.get(node_id, node_id)

    def next_phase(self, current: str, outcome: str = "ok") -> str:
        current = self.normalize_node(current)
        transitions = self.edges.get(current, {})
        if outcome in transitions:
            return transitions[outcome]
        if "ok" in transitions:
            return transitions["ok"]
        raise ValueError(
            f"No transition from '{current}' with outcome '{outcome}'. "
            f"Allowed: {list(transitions.keys())}"
        )

    def list_phases(self) -> List[Dict[str, str]]:
        out = []
        for pid in self.pipeline:
            p = self._phases.get(pid)
            out.append({"id": pid, "label": getattr(p, "label", pid.title())})
        return out


def default_registry() -> PhaseRegistry:
    """Build the standard Ground→…→Promote registry with all phase modules."""
    from src.application.agent_training_factory.phases.author import AuthorPhase
    from src.application.agent_training_factory.phases.blueprint import BlueprintPhase
    from src.application.agent_training_factory.phases.ground import GroundPhase
    from src.application.agent_training_factory.phases.optimize import OptimizePhase
    from src.application.agent_training_factory.phases.promote import PromotePhase
    from src.application.agent_training_factory.phases.verify import VerifyPhase

    reg = PhaseRegistry()
    for phase in (
        GroundPhase(),
        BlueprintPhase(),
        AuthorPhase(),
        VerifyPhase(),
        OptimizePhase(),
        PromotePhase(),
    ):
        reg.register(phase)
    return reg
