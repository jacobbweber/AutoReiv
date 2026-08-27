"""
Telemetry Spans & KPI Metrics Aggregation Repository Mixin [REQ-OBS-001 - REQ-OBS-008].
"""

import json
from datetime import datetime
from typing import Any, List, Optional

from src.domain.observability.models import (
    AgentKPISummary,
    KPIDashboardSummary,
    TelemetryFilter,
    TimeSeriesDataPoint,
    ToolReliabilityMetric,
)
from src.domain.telemetry.models import TelemetrySpan


class TelemetryRepositoryMixin:
    """Methods for recording spans, querying traces, and computing KPI metrics."""

    def save_telemetry_span(self, span: TelemetrySpan) -> None:
        metadata_json = json.dumps(span.metadata) if span.metadata else None
        now_str = span.created_at.isoformat()
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO telemetry_spans (id, session_id, agent_id, span_type, name, duration_ms, prompt_tokens, completion_tokens, success, error_message, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    span.id,
                    span.session_id,
                    span.agent_id,
                    span.span_type,
                    span.name,
                    span.duration_ms,
                    span.prompt_tokens,
                    span.completion_tokens,
                    1 if span.success else 0,
                    span.error_message,
                    metadata_json,
                    now_str,
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_telemetry_spans(
        self,
        agent_id: Optional[str] = None,
        span_type: Optional[str] = None,
        has_error: Optional[bool] = None,
        limit: int = 100,
    ) -> List[TelemetrySpan]:
        query = "SELECT id, session_id, agent_id, span_type, name, duration_ms, prompt_tokens, completion_tokens, success, error_message, metadata_json, created_at FROM telemetry_spans WHERE 1=1"
        params: List[Any] = []

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
        if span_type:
            query += " AND span_type = ?"
            params.append(span_type)
        if has_error is not None:
            if has_error:
                query += " AND success = 0"
            else:
                query += " AND success = 1"

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            spans = []
            for r in rows:
                meta = {}
                if r["metadata_json"]:
                    try:
                        meta = json.loads(r["metadata_json"])
                    except Exception:
                        pass

                spans.append(
                    TelemetrySpan(
                        id=r["id"],
                        session_id=r["session_id"],
                        agent_id=r["agent_id"],
                        span_type=r["span_type"],
                        name=r["name"],
                        duration_ms=r["duration_ms"],
                        prompt_tokens=r["prompt_tokens"],
                        completion_tokens=r["completion_tokens"],
                        success=bool(r["success"]),
                        error_message=r["error_message"],
                        metadata=meta,
                        created_at=datetime.fromisoformat(r["created_at"]),
                    )
                )
            return spans
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_kpi_summary(self, filter: Optional[TelemetryFilter] = None) -> KPIDashboardSummary:
        query = """
            SELECT
                COUNT(*) as total_turns,
                COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0) as total_tokens,
                COALESCE(AVG(duration_ms), 0.0) as avg_turn_duration_ms,
                COALESCE(SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END), 0) as error_count
            FROM telemetry_spans
            WHERE span_type = 'turn'
        """
        params: List[Any] = []
        if filter:
            if filter.agent_id:
                query += " AND agent_id = ?"
                params.append(filter.agent_id)
            if filter.session_id:
                query += " AND session_id = ?"
                params.append(filter.session_id)
            if filter.start_time:
                query += " AND created_at >= ?"
                params.append(filter.start_time.isoformat())
            if filter.end_time:
                query += " AND created_at <= ?"
                params.append(filter.end_time.isoformat())

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            row = cur.fetchone()
            if not row or row["total_turns"] == 0:
                return KPIDashboardSummary()

            total_turns = row["total_turns"]
            err_count = row["error_count"]
            err_rate = (err_count / total_turns * 100.0) if total_turns > 0 else 0.0

            return KPIDashboardSummary(
                total_turns=total_turns,
                total_prompt_tokens=row["total_prompt_tokens"],
                total_completion_tokens=row["total_completion_tokens"],
                total_tokens=row["total_tokens"],
                avg_turn_duration_ms=round(row["avg_turn_duration_ms"], 2),
                error_count=err_count,
                error_rate_pct=round(err_rate, 2),
            )
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_agent_kpi_breakdown(self) -> List[AgentKPISummary]:
        query = """
            SELECT
                agent_id,
                COALESCE(SUM(CASE WHEN span_type = 'turn' THEN 1 ELSE 0 END), 0) as turn_count,
                COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0) as total_tokens,
                COALESCE(SUM(CASE WHEN span_type = 'tool_call' OR span_type = 'tool' THEN 1 ELSE 0 END), 0) as tool_call_count,
                COALESCE(SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END), 0) as error_count,
                COALESCE(AVG(CASE WHEN span_type = 'turn' THEN duration_ms END), 0.0) as avg_duration_ms
            FROM telemetry_spans
            WHERE agent_id IS NOT NULL
            GROUP BY agent_id
            ORDER BY turn_count DESC
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            return [
                AgentKPISummary(
                    agent_id=r["agent_id"],
                    turn_count=r["turn_count"],
                    prompt_tokens=r["prompt_tokens"],
                    completion_tokens=r["completion_tokens"],
                    total_tokens=r["total_tokens"],
                    tool_call_count=r["tool_call_count"],
                    error_count=r["error_count"],
                    avg_duration_ms=round(r["avg_duration_ms"], 2),
                )
                for r in rows
            ]
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_tool_reliability_metrics(self) -> List[ToolReliabilityMetric]:
        query = """
            SELECT
                name as tool_name,
                COUNT(*) as total_invocations,
                COALESCE(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END), 0) as success_count,
                COALESCE(SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END), 0) as failure_count,
                COALESCE(AVG(duration_ms), 0.0) as avg_duration_ms
            FROM telemetry_spans
            WHERE span_type = 'tool_call' OR span_type = 'tool'
            GROUP BY name
            ORDER BY total_invocations DESC
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            metrics = []
            for r in rows:
                total = r["total_invocations"]
                succ = r["success_count"]
                rate = (succ / total * 100.0) if total > 0 else 100.0
                metrics.append(
                    ToolReliabilityMetric(
                        tool_name=r["tool_name"],
                        total_invocations=total,
                        success_count=succ,
                        failure_count=r["failure_count"],
                        success_rate_pct=round(rate, 2),
                        avg_duration_ms=round(r["avg_duration_ms"], 2),
                    )
                )
            return metrics
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_time_series_metrics(self, bucket_hours: int = 1, limit: int = 24) -> List[TimeSeriesDataPoint]:
        query = """
            SELECT
                strftime('%Y-%m-%d %H:00:00', created_at) as time_bucket,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0) as token_count,
                COALESCE(SUM(CASE WHEN span_type = 'turn' THEN 1 ELSE 0 END), 0) as turn_count,
                COALESCE(SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END), 0) as error_count
            FROM telemetry_spans
            GROUP BY time_bucket
            ORDER BY time_bucket DESC
            LIMIT ?
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, (limit,))
            rows = cur.fetchall()
            return [
                TimeSeriesDataPoint(
                    timestamp_bucket=r["time_bucket"] or "unknown",
                    token_count=r["token_count"],
                    turn_count=r["turn_count"],
                    error_count=r["error_count"],
                )
                for r in reversed(rows)
            ]
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_filtered_traces(
        self,
        filter: Optional[TelemetryFilter] = None,
        limit: int = 100,
    ) -> List[TelemetrySpan]:
        query = "SELECT id, session_id, agent_id, span_type, name, duration_ms, prompt_tokens, completion_tokens, success, error_message, metadata_json, created_at FROM telemetry_spans WHERE 1=1"
        params: List[Any] = []

        if filter:
            if filter.agent_id:
                query += " AND agent_id = ?"
                params.append(filter.agent_id)
            if filter.session_id:
                query += " AND session_id = ?"
                params.append(filter.session_id)
            if filter.span_type:
                query += " AND span_type = ?"
                params.append(filter.span_type)
            if filter.has_error is True:
                query += " AND success = 0"
            elif filter.has_error is False:
                query += " AND success = 1"
            if filter.start_time:
                query += " AND created_at >= ?"
                params.append(filter.start_time.isoformat())
            if filter.end_time:
                query += " AND created_at <= ?"
                params.append(filter.end_time.isoformat())

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            spans = []
            for r in rows:
                meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                spans.append(
                    TelemetrySpan(
                        id=r["id"],
                        session_id=r["session_id"],
                        agent_id=r["agent_id"],
                        span_type=r["span_type"],
                        name=r["name"],
                        duration_ms=r["duration_ms"],
                        prompt_tokens=r["prompt_tokens"],
                        completion_tokens=r["completion_tokens"],
                        success=bool(r["success"]),
                        error_message=r["error_message"],
                        metadata=meta,
                        created_at=datetime.fromisoformat(r["created_at"]),
                    )
                )
            return spans
        finally:
            if self._mem_conn is None:
                conn.close()
