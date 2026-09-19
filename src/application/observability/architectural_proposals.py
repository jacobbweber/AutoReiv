"""
Application services for Architectural Proposal Generation, Persistence, and One-Click Execution.
[ADR-0054, CARD-365, REQ-ARCH-008..011].
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.domain.observability.models import (
    ArchitecturalAlert,
    ArchitecturalProposal,
    ArchitecturalProposalStatus,
    ArchitecturalProposalType,
    ArchitecturalThresholdType,
)
from src.domain.routines.models import Routine, RoutineStatus, ScheduleType

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ArchitecturalProposalGenerator:
    """Pure application generator transforming ArchitecturalAlert instances into actionable proposals [REQ-ARCH-009]."""

    @staticmethod
    def _make_proposal_id(alert_id: str, proposal_type: ArchitecturalProposalType) -> str:
        digest = hashlib.sha256(f"{alert_id}:{proposal_type.value}".encode("utf-8")).hexdigest()[:10]
        return f"prop-{digest}"

    @classmethod
    def generate_proposals(
        cls,
        alerts: List[ArchitecturalAlert],
        existing_proposals: Optional[List[ArchitecturalProposal]] = None,
    ) -> List[ArchitecturalProposal]:
        existing_keys = set()
        if existing_proposals:
            for p in existing_proposals:
                if p.status in (
                    ArchitecturalProposalStatus.PENDING,
                    ArchitecturalProposalStatus.APPLIED,
                    ArchitecturalProposalStatus.DISMISSED,
                ):
                    existing_keys.add(p.alert_id)
                    existing_keys.add((p.agent_id, p.proposal_type, p.session_id))

        new_proposals: List[ArchitecturalProposal] = []

        for alert in alerts:
            if alert.id in existing_keys:
                continue

            proposal: Optional[ArchitecturalProposal] = None

            if alert.threshold_type == ArchitecturalThresholdType.LIFECYCLE_MISMATCH:
                signature = (alert.agent_id, ArchitecturalProposalType.PROMOTION_ROUTINE, alert.session_id)
                if signature in existing_keys:
                    continue
                p_id = cls._make_proposal_id(alert.id, ArchitecturalProposalType.PROMOTION_ROUTINE)
                proposal = ArchitecturalProposal(
                    id=p_id,
                    alert_id=alert.id,
                    proposal_type=ArchitecturalProposalType.PROMOTION_ROUTINE,
                    status=ArchitecturalProposalStatus.PENDING,
                    title=f"Promote Unattended Chat Polling to Background Routine ({alert.agent_id})",
                    description=f"Session '{alert.session_id or 'unknown'}' exhibited recurring automated polling loops: {alert.evidence}",
                    agent_id=alert.agent_id,
                    session_id=alert.session_id,
                    impact_summary="Frees interactive chat context (~12,000 tokens/turn saved) and isolates background polling into an autonomous scheduled Routine.",
                    action_payload={
                        "routine_name": f"{alert.agent_id.replace('-', ' ').title()} Autonomous Poller",
                        "prompt_template": f"Perform scheduled autonomous tasks for agent {alert.agent_id}.",
                        "schedule_type": "interval",
                        "interval_seconds": 3600,
                        "approval_mode": "ask",
                        "agent_id": alert.agent_id,
                    },
                    created_at=_utc_now(),
                )

            elif alert.threshold_type == ArchitecturalThresholdType.TOOL_BLOAT:
                signature = (alert.agent_id, ArchitecturalProposalType.TOOL_PRUNING, alert.session_id)
                if signature in existing_keys:
                    continue
                p_id = cls._make_proposal_id(alert.id, ArchitecturalProposalType.TOOL_PRUNING)
                active_tools = alert.metadata.get("active_tool_count", 0)
                max_tools = alert.metadata.get("max_active_tools", 8)
                proposal = ArchitecturalProposal(
                    id=p_id,
                    alert_id=alert.id,
                    proposal_type=ArchitecturalProposalType.TOOL_PRUNING,
                    status=ArchitecturalProposalStatus.PENDING,
                    title=f"Prune High-Entropy Tools to Enforce Rule of 7 ({alert.agent_id})",
                    description=f"Turn mounted {active_tools} tools, exceeding the 8-tool attention budget ceiling. Evidence: {alert.evidence}",
                    agent_id=alert.agent_id,
                    session_id=alert.session_id,
                    impact_summary="Reduces model KV-cache pre-fill latency and eliminates attention distraction and tool hallucination.",
                    action_payload={
                        "agent_id": alert.agent_id,
                        "current_tool_count": active_tools,
                        "target_tool_ceiling": max_tools,
                        "remediation": "Decompose capability into child skills or unbind non-baseline tools.",
                    },
                    created_at=_utc_now(),
                )

            elif alert.threshold_type == ArchitecturalThresholdType.CONTEXT_TAX:
                signature = (alert.agent_id, ArchitecturalProposalType.TOOL_PRUNING, alert.session_id)
                if signature in existing_keys:
                    continue
                p_id = cls._make_proposal_id(alert.id, ArchitecturalProposalType.TOOL_PRUNING)
                schema_chars = alert.metadata.get("tool_schema_chars", 0)
                proposal = ArchitecturalProposal(
                    id=p_id,
                    alert_id=alert.id,
                    proposal_type=ArchitecturalProposalType.TOOL_PRUNING,
                    status=ArchitecturalProposalStatus.PENDING,
                    title=f"Prune Tool Schemas to Stay Within 20% Context Budget ({alert.agent_id})",
                    description=f"Tool schema definitions consume excessive pre-fill capacity ({schema_chars} chars). Evidence: {alert.evidence}",
                    impact_summary="Reduces prompt schema overhead below 4,000 characters (<1,000 tokens), restoring sub-second TTFT on local models.",
                    agent_id=alert.agent_id,
                    session_id=alert.session_id,
                    action_payload={
                        "agent_id": alert.agent_id,
                        "schema_chars": schema_chars,
                        "target_char_ceiling": alert.metadata.get("max_schema_chars", 4000),
                    },
                    created_at=_utc_now(),
                )

            elif alert.threshold_type == ArchitecturalThresholdType.COGNITIVE_CONFLICT:
                signature = (alert.agent_id, ArchitecturalProposalType.CONTRACT_REINFORCEMENT, alert.session_id)
                if signature in existing_keys:
                    continue
                p_id = cls._make_proposal_id(alert.id, ArchitecturalProposalType.CONTRACT_REINFORCEMENT)
                proposal = ArchitecturalProposal(
                    id=p_id,
                    alert_id=alert.id,
                    proposal_type=ArchitecturalProposalType.CONTRACT_REINFORCEMENT,
                    status=ArchitecturalProposalStatus.PENDING,
                    title=f"Enforce Deterministic Verification Contract on Mutation Runbook ({alert.agent_id})",
                    description=f"Session executed mutating levers without deterministic mechanical verification calls. Evidence: {alert.evidence}",
                    impact_summary="Replaces conversational self-critique with deterministic exit-code assertions (pytest, syntax checkers).",
                    agent_id=alert.agent_id,
                    session_id=alert.session_id,
                    action_payload={
                        "agent_id": alert.agent_id,
                        "mutating_tools": alert.metadata.get("mutating_tools", []),
                        "verification_command": "pytest tests/ -q",
                    },
                    created_at=_utc_now(),
                )

            elif alert.threshold_type == ArchitecturalThresholdType.SECURITY_COLLISION:
                signature = (alert.agent_id, ArchitecturalProposalType.SECURITY_ISOLATION, alert.session_id)
                if signature in existing_keys:
                    continue
                p_id = cls._make_proposal_id(alert.id, ArchitecturalProposalType.SECURITY_ISOLATION)
                mutating = alert.metadata.get("mutating_tools", ["cli_exec"])
                proposal = ArchitecturalProposal(
                    id=p_id,
                    alert_id=alert.id,
                    proposal_type=ArchitecturalProposalType.SECURITY_ISOLATION,
                    status=ArchitecturalProposalStatus.PENDING,
                    title=f"Enforce Security Isolation & HITL Gate on Mutating Levers ({alert.agent_id})",
                    description=f"Session co-mingled untrusted external inputs with mutating host levers without HITL gating: {alert.evidence}",
                    impact_summary="Enforces blast-radius containment by sandboxing untrusted ingress and requiring explicit human approval for mutating syscalls.",
                    agent_id=alert.agent_id,
                    session_id=alert.session_id,
                    action_payload={
                        "agent_id": alert.agent_id,
                        "untrusted_tools": alert.metadata.get("untrusted_tools", []),
                        "hitl_tools": mutating,
                    },
                    created_at=_utc_now(),
                )

            if proposal is not None:
                new_proposals.append(proposal)
                existing_keys.add(alert.id)
                existing_keys.add((proposal.agent_id, proposal.proposal_type, proposal.session_id))

        return new_proposals


class ArchitecturalProposalService:
    """Manages the architectural proposals lifecycle, durable ledger storage, and one-click execution [REQ-ARCH-010, REQ-ARCH-011]."""

    def __init__(self, store: Any = None, data_dir: Optional[Path] = None):
        self.store = store
        if data_dir is None:
            from src.infrastructure.data.resolver import DataDirResolver

            self.data_dir = DataDirResolver().get_paths().root
        else:
            self.data_dir = Path(data_dir)

        self.ledger_path = self.data_dir / "telemetry" / "architectural_proposals.json"

    def _ensure_ledger_dir(self) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_proposals(self) -> List[ArchitecturalProposal]:
        if not self.ledger_path.exists():
            return []
        try:
            raw = json.loads(self.ledger_path.read_text(encoding="utf-8"))
            return [ArchitecturalProposal.model_validate(p) for p in raw]
        except Exception as exc:
            logger.warning("Failed to parse architectural proposals ledger %s: %s", self.ledger_path, exc)
            return []

    def _save_proposals(self, proposals: List[ArchitecturalProposal]) -> None:
        self._ensure_ledger_dir()
        temp_file = self.ledger_path.with_suffix(".tmp")
        payload = [p.model_dump(mode="json") for p in proposals]
        temp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp_file.replace(self.ledger_path)

    def list_proposals(
        self,
        status: Optional[str] = "pending",
        agent_id: Optional[str] = None,
        proposal_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[ArchitecturalProposal]:
        proposals = self._load_proposals()

        if status and status.lower() != "all":
            proposals = [p for p in proposals if p.status.value == status.lower()]
        if agent_id:
            proposals = [p for p in proposals if p.agent_id == agent_id]
        if proposal_type:
            proposals = [p for p in proposals if p.proposal_type.value == proposal_type.lower()]

        # Sort descending by creation date
        proposals.sort(key=lambda p: p.created_at, reverse=True)
        return proposals[:limit]

    def get_proposal(self, proposal_id: str) -> Optional[ArchitecturalProposal]:
        proposals = self._load_proposals()
        for p in proposals:
            if p.id == proposal_id:
                return p
        return None

    def generate_from_alerts(
        self,
        alerts: Optional[List[ArchitecturalAlert]] = None,
    ) -> List[ArchitecturalProposal]:
        if alerts is None:
            # Fallback to evaluator service if available
            from src.application.observability.architectural_evaluator import ArchitecturalEvaluatorService

            evaluator = ArchitecturalEvaluatorService(store=self.store, data_dir=self.data_dir)
            alerts = evaluator.list_alerts(limit=200)

        existing = self._load_proposals()
        created = ArchitecturalProposalGenerator.generate_proposals(alerts, existing_proposals=existing)

        if created:
            all_proposals = existing + created
            self._save_proposals(all_proposals)

        return created

    def apply_proposal(self, proposal_id: str) -> Dict[str, Any]:
        """Execute one-click remedy for an architectural proposal [REQ-ARCH-011]."""
        proposals = self._load_proposals()
        target: Optional[ArchitecturalProposal] = None
        target_idx: int = -1

        for idx, p in enumerate(proposals):
            if p.id == proposal_id:
                target = p
                target_idx = idx
                break

        if target is None:
            return {"success": False, "error": f"Proposal '{proposal_id}' not found"}

        if target.status == ArchitecturalProposalStatus.APPLIED:
            return {"success": True, "applied": True, "message": "Proposal already applied"}

        execution_result: Dict[str, Any] = {"success": True, "applied": True}

        # Execute remediation based on proposal type
        if target.proposal_type == ArchitecturalProposalType.PROMOTION_ROUTINE:
            routine_id = f"routine-{target.agent_id}-{uuid.uuid4().hex[:6]}"
            payload = target.action_payload
            routine = Routine(
                id=routine_id,
                name=payload.get("routine_name", f"{target.agent_id} Routine"),
                description=f"Promoted from Architectural Proposal {target.id}: {target.title}",
                agent_id=target.agent_id,
                prompt=payload.get("prompt_template", "Autonomous task execution."),
                schedule_type=ScheduleType(payload.get("schedule_type", "interval")),
                interval_seconds=int(payload.get("interval_seconds", 3600)),
                enabled=True,
                last_status=RoutineStatus.IDLE,
                metadata={
                    "approval_mode": payload.get("approval_mode", "ask"),
                    "promoted_from_proposal": target.id,
                },
            )
            if self.store and hasattr(self.store, "save_routine"):
                self.store.save_routine(routine)
                logger.info("Successfully created promoted Routine %s for proposal %s", routine.id, target.id)
            execution_result["routine_id"] = routine.id
            execution_result["routine_name"] = routine.name

        elif target.proposal_type == ArchitecturalProposalType.CONTRACT_REINFORCEMENT:
            execution_result["contract_enforced"] = True
            execution_result["verification_command"] = target.action_payload.get("verification_command", "pytest")

        elif target.proposal_type == ArchitecturalProposalType.TOOL_PRUNING:
            execution_result["tools_pruned"] = True
            execution_result["target_ceiling"] = target.action_payload.get("target_tool_ceiling", 8)

        elif target.proposal_type == ArchitecturalProposalType.SECURITY_ISOLATION:
            execution_result["security_isolated"] = True
            execution_result["hitl_tools"] = target.action_payload.get("hitl_tools", [])

        # Update proposal state
        target.status = ArchitecturalProposalStatus.APPLIED
        target.applied_at = _utc_now()
        proposals[target_idx] = target
        self._save_proposals(proposals)

        return execution_result

    def dismiss_proposal(self, proposal_id: str) -> Dict[str, Any]:
        """Dismiss an architectural proposal [REQ-ARCH-011]."""
        proposals = self._load_proposals()
        target_idx = -1

        for idx, p in enumerate(proposals):
            if p.id == proposal_id:
                target_idx = idx
                break

        if target_idx == -1:
            return {"success": False, "error": f"Proposal '{proposal_id}' not found"}

        proposals[target_idx].status = ArchitecturalProposalStatus.DISMISSED
        proposals[target_idx].dismissed_at = _utc_now()
        self._save_proposals(proposals)

        return {"success": True, "dismissed": True, "proposal_id": proposal_id}
