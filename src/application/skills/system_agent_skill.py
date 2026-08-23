"""
System Agent Skill for Platform Health & Telemetry Inspection [REQ-AGENTS-006].
"""

from typing import Any, Dict, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.agents.profiles import BUILTIN_PROFILES
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class SystemAgentSkill:
    """
    Skill providing system health inspection, database monitoring,
    and platform telemetry analytics.
    """

    def __init__(self, store: SQLiteStateStore, telemetry: TelemetryCollector):
        self.store = store
        self.telemetry = telemetry

    def inspect_system_health(self) -> Dict[str, Any]:
        """
        Inspect the database connectivity, query response, and platform KPIs.
        """
        db_status = "healthy"
        try:
            sessions = self.store.list_sessions()
            _ = len(sessions)
        except Exception as e:
            db_status = f"error: {e}"

        kpis = self.telemetry.get_global_kpis()
        return {
            "database_status": db_status,
            "total_turns": kpis["total_turns"],
            "total_tool_calls": kpis["total_tool_calls"],
            "total_tokens": kpis["total_tokens"],
            "global_error_rate": kpis["global_error_rate"],
        }

    def get_agent_usage_summary(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Return token usage, turn counts, and success rates for a specific agent or all agents.
        """
        if agent_id:
            return self.telemetry.get_agent_metrics(agent_id)

        all_agent_metrics = {}
        for profile in BUILTIN_PROFILES:
            all_agent_metrics[profile.id] = self.telemetry.get_agent_metrics(profile.id)
        return all_agent_metrics

    def get_tool_health_matrix(self) -> Dict[str, Dict[str, Any]]:
        """
        Return execution counts, success/failure counts, and error rates for all tools.
        """
        return self.telemetry.get_tool_metrics()

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register System Agent tools with the scoped registry."""
        registry.register_tool(
            name="inspect_system_health",
            description="Inspect platform database connectivity, total turns, tokens, and error rates.",
            parameters={"type": "object"},
            handler=self.inspect_system_health,
        )

        registry.register_tool(
            name="get_agent_usage_summary",
            description="Get token consumption and performance metrics per agent.",
            parameters={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Optional agent ID to filter (e.g. general-assistant)",
                    },
                },
            },
            handler=self.get_agent_usage_summary,
        )

        registry.register_tool(
            name="get_tool_health_matrix",
            description="Get tool reliability stats, failure counts, and execution latency.",
            parameters={"type": "object"},
            handler=self.get_tool_health_matrix,
        )
