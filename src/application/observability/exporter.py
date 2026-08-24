"""
Trace Exporter & Structured JSON Telemetry Archiver [REQ-OBS-005, REQ-OBS-006].
"""

import json
from datetime import datetime, timezone
from typing import List, Optional

from src.domain.observability.models import TelemetryFilter
from src.domain.telemetry.models import TelemetrySpan
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class TraceExporter:
    """
    Serializes execution traces into structured JSON archives for auditing or external visualization.
    """

    @classmethod
    def export_spans_to_json(cls, spans: List[TelemetrySpan], indent: int = 2) -> str:
        """Serialize a list of spans to formatted JSON string."""
        now_str = datetime.now(timezone.utc).isoformat()
        span_dicts = [span.model_dump(mode="json") for span in spans]
        payload = {
            "version": "1.0",
            "exported_at": now_str,
            "count": len(spans),
            "spans": span_dicts,
        }
        return json.dumps(payload, indent=indent)

    @classmethod
    def export_session_traces(cls, state_store: SQLiteStateStore, session_id: str) -> str:
        """Fetch and serialize all traces for a specific session."""
        spans = state_store.get_filtered_traces(filter=TelemetryFilter(session_id=session_id))
        return cls.export_spans_to_json(spans)

    @classmethod
    def export_all_traces(
        cls,
        state_store: SQLiteStateStore,
        filter: Optional[TelemetryFilter] = None,
        limit: int = 500,
    ) -> str:
        """Fetch and serialize all traces matching the filter."""
        spans = state_store.get_filtered_traces(filter=filter, limit=limit)
        return cls.export_spans_to_json(spans)
