"""
Observability Dashboard Application Service [REQ-OBS-001 - REQ-OBS-004].
"""

from typing import List, Optional

from src.domain.observability.models import (
    AgentKPISummary,
    KPIDashboardSummary,
    TelemetryFilter,
    TimeSeriesDataPoint,
    ToolReliabilityMetric,
)
from src.domain.telemetry.models import TelemetrySpan
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class ObservabilityDashboardService:
    """
    High-level application service querying platform KPIs, per-agent breakdowns,
    tool reliability statistics, time-series timelines, and execution traces.
    """

    def __init__(self, state_store: SQLiteStateStore):
        self.state_store = state_store

    def get_overview_kpis(self, filter: Optional[TelemetryFilter] = None) -> KPIDashboardSummary:
        """Fetch global platform KPIs."""
        return self.state_store.get_kpi_summary(filter=filter)

    def get_agent_breakdown(self) -> List[AgentKPISummary]:
        """Fetch per-agent KPI breakdown."""
        return self.state_store.get_agent_kpi_breakdown()

    def get_tool_reliability(self) -> List[ToolReliabilityMetric]:
        """Fetch tool invocation and reliability matrix."""
        return self.state_store.get_tool_reliability_metrics()

    def get_timeline(self, bucket_hours: int = 1, limit: int = 24) -> List[TimeSeriesDataPoint]:
        """Fetch time-series chart data."""
        return self.state_store.get_time_series_metrics(bucket_hours=bucket_hours, limit=limit)

    def get_traces(
        self,
        filter: Optional[TelemetryFilter] = None,
        limit: int = 100,
    ) -> List[TelemetrySpan]:
        """Fetch filtered execution traces."""
        return self.state_store.get_filtered_traces(filter=filter, limit=limit)
