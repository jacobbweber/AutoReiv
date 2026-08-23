"""
Telemetry Collector & KPI Aggregator [REQ-KERNEL-005].
Records execution spans and computes performance/reliability metrics.
"""

import uuid
from typing import Any, Dict, Optional

from src.domain.telemetry.models import TelemetrySpan, utc_now
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class TelemetryCollector:
    """
    Service for capturing execution traces and computing real-time telemetry metrics.
    """

    def __init__(self, store: SQLiteStateStore):
        self.store = store

    def record_turn_span(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        model: str = "default",
        duration_ms: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TelemetrySpan:
        """Record an LLM turn execution span."""
        span = TelemetrySpan(
            id=str(uuid.uuid4()),
            session_id=session_id,
            agent_id=agent_id,
            span_type="turn",
            name=model,
            duration_ms=duration_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
            created_at=utc_now(),
        )
        self.store.save_telemetry_span(span)
        return span

    def record_tool_span(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        tool_name: str = "unknown_tool",
        duration_ms: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TelemetrySpan:
        """Record a tool execution span."""
        span = TelemetrySpan(
            id=str(uuid.uuid4()),
            session_id=session_id,
            agent_id=agent_id,
            span_type="tool",
            name=tool_name,
            duration_ms=duration_ms,
            prompt_tokens=0,
            completion_tokens=0,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
            created_at=utc_now(),
        )
        self.store.save_telemetry_span(span)
        return span

    def record_handoff_span(
        self,
        sender_agent_id: str,
        recipient_agent_id: str,
        session_id: str,
        correlation_id: str,
        duration_ms: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TelemetrySpan:
        """Record an inter-agent delegation span [REQ-A2A-005]."""
        meta = metadata or {}
        meta.update(
            {
                "sender_agent_id": sender_agent_id,
                "recipient_agent_id": recipient_agent_id,
                "correlation_id": correlation_id,
            }
        )
        span = TelemetrySpan(
            id=str(uuid.uuid4()),
            session_id=session_id,
            agent_id=sender_agent_id,
            span_type="handoff",
            name=f"handoff:{sender_agent_id}->{recipient_agent_id}",
            duration_ms=duration_ms,
            prompt_tokens=0,
            completion_tokens=0,
            success=success,
            error_message=error_message,
            metadata=meta,
            created_at=utc_now(),
        )
        self.store.save_telemetry_span(span)
        return span

    def get_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Compute aggregated metrics for a specific agent."""
        spans = self.store.get_telemetry_spans(agent_id=agent_id, span_type="turn", limit=10000)
        if not spans:
            return {
                "turn_count": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "avg_duration_ms": 0.0,
                "success_rate": 1.0,
            }

        total_prompt = sum(s.prompt_tokens for s in spans)
        total_comp = sum(s.completion_tokens for s in spans)
        total_dur = sum(s.duration_ms for s in spans)
        successes = sum(1 for s in spans if s.success)

        return {
            "turn_count": len(spans),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_comp,
            "total_tokens": total_prompt + total_comp,
            "avg_duration_ms": total_dur / len(spans) if spans else 0.0,
            "success_rate": successes / len(spans) if spans else 1.0,
        }

    def get_tool_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Compute reliability and latency statistics for every registered tool."""
        spans = self.store.get_telemetry_spans(span_type="tool", limit=10000)
        grouped: Dict[str, list[TelemetrySpan]] = {}
        for s in spans:
            grouped.setdefault(s.name, []).append(s)

        results: Dict[str, Dict[str, Any]] = {}
        for tool_name, tool_spans in grouped.items():
            call_count = len(tool_spans)
            success_count = sum(1 for s in tool_spans if s.success)
            fail_count = call_count - success_count
            avg_duration = sum(s.duration_ms for s in tool_spans) / call_count if call_count else 0.0

            results[tool_name] = {
                "call_count": call_count,
                "success_count": success_count,
                "fail_count": fail_count,
                "success_rate": success_count / call_count if call_count else 1.0,
                "avg_duration_ms": avg_duration,
            }
        return results

    def get_global_kpis(self) -> Dict[str, Any]:
        """Compute platform-wide KPIs across all agents and tools."""
        all_spans = self.store.get_telemetry_spans(limit=10000)
        turn_spans = [s for s in all_spans if s.span_type == "turn"]
        tool_spans = [s for s in all_spans if s.span_type == "tool"]

        total_tokens = sum(s.prompt_tokens + s.completion_tokens for s in turn_spans)
        total_failures = sum(1 for s in all_spans if not s.success)
        error_rate = total_failures / len(all_spans) if all_spans else 0.0

        return {
            "total_turns": len(turn_spans),
            "total_tool_calls": len(tool_spans),
            "total_tokens": total_tokens,
            "global_error_rate": error_rate,
        }
