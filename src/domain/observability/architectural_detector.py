"""
Pure domain detector for the 5 God-Agent Architectural Thresholds [CARD-364, ADR-0054].
Audits runtime telemetry spans and message transcripts for structural and cognitive degradation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Set

from src.domain.gateway.models import ChatMessage, Role
from src.domain.observability.models import (
    ArchitecturalAlert,
    ArchitecturalThresholdType,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ArchitecturalThresholdDetector:
    """
    Evaluates telemetry turn spans and session message transcripts against the
    5 God-Agent architectural thresholds defined in ADR-0054.
    """

    DEFAULT_UNTRUSTED_TOOLS: Set[str] = {
        "web_search",
        "read_url_content",
        "fetch",
        "http_get",
        "browser_navigate",
        "search_web",
        "read_browser_page",
    }

    DEFAULT_MUTATING_TOOLS: Set[str] = {
        "cli_exec",
        "write_project_file",
        "repo_file_write",
        "repo_file_patch",
        "execute_code",
        "execute_agent_database",
        "delete_file",
        "bash",
        "shell",
    }

    DEFAULT_VERIFICATION_MARKERS: Set[str] = {
        "pytest",
        "test",
        "status",
        "verify",
        "check",
        "assert",
        "checker",
    }

    def __init__(
        self,
        max_active_tools: int = 8,
        max_schema_chars: int = 4000,
        max_autonomous_turns: int = 5,
        untrusted_tools: Optional[Set[str]] = None,
        mutating_tools: Optional[Set[str]] = None,
    ) -> None:
        self.max_active_tools = max_active_tools
        self.max_schema_chars = max_schema_chars
        self.max_autonomous_turns = max_autonomous_turns
        self.untrusted_tools = untrusted_tools or self.DEFAULT_UNTRUSTED_TOOLS
        self.mutating_tools = mutating_tools or self.DEFAULT_MUTATING_TOOLS

    def is_untrusted_tool(self, tool_name: str) -> bool:
        norm = (tool_name or "").lower()
        return any(t in norm for t in self.untrusted_tools)

    def is_mutating_tool(self, tool_name: str) -> bool:
        norm = (tool_name or "").lower()
        return any(t in norm for t in self.mutating_tools)

    def is_verification_call(self, tool_name: str, content: str) -> bool:
        combined = f"{tool_name} {content}".lower()
        return any(m in combined for m in self.DEFAULT_VERIFICATION_MARKERS)

    def evaluate_turn_span(self, span: Any) -> List[ArchitecturalAlert]:
        """
        Evaluate a single turn telemetry span for entropy and context tax breaches.
        Accepts dict or TelemetrySpan object.
        """
        alerts: List[ArchitecturalAlert] = []

        if hasattr(span, "model_dump"):
            span_dict = span.model_dump()
        elif isinstance(span, dict):
            span_dict = span
        else:
            span_dict = dict(getattr(span, "__dict__", {}))

        meta = span_dict.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}

        session_id = span_dict.get("session_id")
        agent_id = span_dict.get("agent_id") or "autoreiv"
        occurred_at = span_dict.get("start_time") or span_dict.get("created_at") or _utc_now()
        if isinstance(occurred_at, str):
            try:
                occurred_at = datetime.fromisoformat(occurred_at)
            except Exception:
                occurred_at = _utc_now()

        # 1. Tool Entropy Limit (Rule of 7) [REQ-ARCH-001]
        active_tool_count = (
            span_dict.get("active_tool_count")
            if span_dict.get("active_tool_count") is not None
            else meta.get("active_tool_count", 0)
        ) or 0
        if active_tool_count > self.max_active_tools:
            alerts.append(
                ArchitecturalAlert(
                    id=f"alert_bloat_{uuid.uuid4().hex[:12]}",
                    threshold_type=ArchitecturalThresholdType.TOOL_BLOAT,
                    severity="high",
                    agent_id=agent_id,
                    session_id=session_id,
                    evidence=(
                        f"Turn mounted {active_tool_count} tools, exceeding the "
                        f"Rule of 7 budget ({self.max_active_tools})."
                    ),
                    remediation_proposal=(
                        "Decompose agent skill into modular SOPs or rely on demand-paged "
                        "tool mounting to preserve the Rule of 7 entropy budget."
                    ),
                    occurred_at=occurred_at,
                    metadata={"active_tool_count": active_tool_count, "span_id": span_dict.get("span_id") or span_dict.get("id")},
                )
            )

        # 2. Context Budget Limit (Pre-fill Tax) [REQ-ARCH-002]
        tool_schema_chars = (
            span_dict.get("tool_schema_chars")
            if span_dict.get("tool_schema_chars") is not None
            else meta.get("tool_schema_chars", 0)
        ) or 0
        if tool_schema_chars > self.max_schema_chars:
            alerts.append(
                ArchitecturalAlert(
                    id=f"alert_tax_{uuid.uuid4().hex[:12]}",
                    threshold_type=ArchitecturalThresholdType.CONTEXT_TAX,
                    severity="medium",
                    agent_id=agent_id,
                    session_id=session_id,
                    evidence=(
                        f"Tool schema pre-fill consumed {tool_schema_chars} characters "
                        f"(> {self.max_schema_chars} limit), imposing heavy latency and KV-cache tax."
                    ),
                    remediation_proposal=(
                        "Adopt compact capability index and demand-paged tool schemas to restore "
                        "lean sub-second Time to First Token."
                    ),
                    occurred_at=occurred_at,
                    metadata={"tool_schema_chars": tool_schema_chars, "span_id": span_dict.get("span_id") or span_dict.get("id")},
                )
            )

        return alerts

    def evaluate_session_messages(
        self,
        session_id: str,
        agent_id: str,
        messages: List[ChatMessage],
        hitl_approved: bool = False,
    ) -> List[ArchitecturalAlert]:
        """
        Evaluate session message history for security boundary collision,
        lifecycle mismatch, and cognitive conflict.
        """
        alerts: List[ArchitecturalAlert] = []
        if not messages:
            return alerts

        now = _utc_now()

        # Check for HITL indicators in message content
        session_has_hitl = hitl_approved or any(
            "hitl" in (m.content or "").lower() or "approval" in (m.content or "").lower()
            for m in messages
            if m.role == Role.SYSTEM
        )

        untrusted_tools_called: List[str] = []
        mutating_tools_called: List[str] = []
        has_mechanical_verification = False

        consecutive_autonomous_turns = 0
        max_observed_autonomous_turns = 0

        for msg in messages:
            if msg.role == Role.USER:
                consecutive_autonomous_turns = 0
            elif msg.role in (Role.ASSISTANT, Role.TOOL):
                consecutive_autonomous_turns += 1
                if consecutive_autonomous_turns > max_observed_autonomous_turns:
                    max_observed_autonomous_turns = consecutive_autonomous_turns

            if msg.role == Role.TOOL:
                name = msg.name or ""
                content = msg.content or ""
                if self.is_untrusted_tool(name):
                    untrusted_tools_called.append(name)
                if self.is_mutating_tool(name):
                    mutating_tools_called.append(name)
                if self.is_verification_call(name, content):
                    has_mechanical_verification = True

        # 3. Security Boundary Collision [REQ-ARCH-003]
        if untrusted_tools_called and mutating_tools_called and not session_has_hitl:
            alerts.append(
                ArchitecturalAlert(
                    id=f"alert_sec_{uuid.uuid4().hex[:12]}",
                    threshold_type=ArchitecturalThresholdType.SECURITY_COLLISION,
                    severity="critical",
                    agent_id=agent_id,
                    session_id=session_id,
                    evidence=(
                        f"Untrusted input tool(s) ({', '.join(set(untrusted_tools_called))}) invoked "
                        f"alongside mutating tool(s) ({', '.join(set(mutating_tools_called))}) "
                        "in the same session without operator approval."
                    ),
                    remediation_proposal=(
                        "Enforce requires_hitl: true (HITL gating) for mutating operations or isolate "
                        "untrusted ingestion into a sandboxed secondary service account."
                    ),
                    occurred_at=now,
                    metadata={
                        "untrusted_tools": list(set(untrusted_tools_called)),
                        "mutating_tools": list(set(mutating_tools_called)),
                    },
                )
            )

        # 4. Lifecycle Mismatch (Daemon Drift) [REQ-ARCH-004]
        if max_observed_autonomous_turns >= self.max_autonomous_turns:
            alerts.append(
                ArchitecturalAlert(
                    id=f"alert_life_{uuid.uuid4().hex[:12]}",
                    threshold_type=ArchitecturalThresholdType.LIFECYCLE_MISMATCH,
                    severity="medium",
                    agent_id=agent_id,
                    session_id=session_id,
                    evidence=(
                        f"Session executed {max_observed_autonomous_turns} automated turns without "
                        f"human intervention (threshold: {self.max_autonomous_turns}), displaying "
                        "unattended daemon behavior."
                    ),
                    remediation_proposal=(
                        "Promote recurring or multi-step polling workflows into an unattended "
                        "AutoReiv background Routine."
                    ),
                    occurred_at=now,
                    metadata={"observed_turns": max_observed_autonomous_turns},
                )
            )

        # 5. Cognitive Conflict (Self-Auditing) [REQ-ARCH-005]
        if mutating_tools_called and not has_mechanical_verification:
            alerts.append(
                ArchitecturalAlert(
                    id=f"alert_cog_{uuid.uuid4().hex[:12]}",
                    threshold_type=ArchitecturalThresholdType.COGNITIVE_CONFLICT,
                    severity="high",
                    agent_id=agent_id,
                    session_id=session_id,
                    evidence=(
                        f"Mutating tool(s) ({', '.join(set(mutating_tools_called))}) executed "
                        "without subsequent mechanical test execution or verification check."
                    ),
                    remediation_proposal=(
                        "Define a deterministic verification contract (test suite, compiler check, "
                        "or assertion) to verify mutations mechanically rather than relying on self-critique."
                    ),
                    occurred_at=now,
                    metadata={"mutating_tools": list(set(mutating_tools_called))},
                )
            )

        return alerts
