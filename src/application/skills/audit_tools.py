"""Performance & Cost Audit Tools [CARD-337 / REQ-AUDIT-002].

Exposes the audit_performance_and_cost tool for platform agents,
generating structured latency and token attribution reports and exporting to Wiki Studio.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.observability.audit_service import AuditService
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class AuditTools:
    """
    Exposes performance and cost auditing capabilities as agent tools.
    """

    def __init__(
        self,
        store: SQLiteStateStore,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        self.store = store
        self.audit_service = audit_service or AuditService(store=store)

    def audit_performance_and_cost(
        self,
        target_type: str = "window",
        target_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Audit LLM latency, token attribution, and cost; returns structured metrics and markdown report."""
        if target_type == "job":
            report = self.audit_service.audit_job(target_id or "")
        elif target_type == "session":
            report = self.audit_service.audit_session(target_id or "")
        elif target_type == "window":
            hours = int(target_id) if target_id and target_id.isdigit() else 24
            report = self.audit_service.audit_window(hours=hours)
        else:
            return {
                "success": False,
                "error": f"Invalid target_type '{target_type}'. Must be 'job', 'session', or 'window'.",
            }

        report_md = self.audit_service.format_markdown_report(report)

        return {
            "success": True,
            "target_type": report.target_type,
            "target_id": report.target_id,
            "total_turns": report.total_turns,
            "total_tokens": report.total_tokens,
            "scaffold_ratio": report.scaffold_ratio,
            "estimated_cost_usd": report.estimated_cost_usd,
            "warnings": report.warnings,
            "report_markdown": report_md,
        }

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register the audit_performance_and_cost tool."""
        registry.register_tool(
            name="audit_performance_and_cost",
            description=(
                "Audit LLM execution telemetry, token attribution, and cost for a job, "
                "session, or time window. Returns structured metrics and markdown report. "
                "To document in the Wiki, hand off the report to the wiki agent via handoff_to_agent."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "target_type": {
                        "type": "string",
                        "enum": ["job", "session", "window"],
                        "description": "Scope of the audit: 'job' for specific job ID, 'session' for chat session ID, or 'window' for recent hours.",
                    },
                    "target_id": {
                        "type": "string",
                        "description": "Target identifier: job ID, session ID, or number of hours for window (e.g. '24').",
                    },
                },
            },
            handler=self.audit_performance_and_cost,
        )
