"""Performance & Cost Audit Service [CARD-337 / REQ-AUDIT-001].

Aggregates telemetry spans across jobs, sessions, or time windows to produce
granular token distributions, latency benchmarks, cost estimates, and harness tax analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from src.domain.telemetry.models import TelemetrySpan, utc_now
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@dataclass
class PerformanceAuditReport:
    """Aggregated performance, token distribution, and cost audit metrics."""

    target_type: str
    target_id: str
    total_spans: int
    total_turns: int
    total_wall_clock_ms: float
    avg_ttft_ms: Optional[float]
    avg_tps: Optional[float]
    total_prompt_tokens: int
    total_completion_tokens: int
    total_reasoning_tokens: int
    total_tokens: int
    token_breakdown: Dict[str, int]
    token_percentages: Dict[str, float]
    scaffold_tokens: int
    scaffold_ratio: float
    estimated_cost_usd: float
    warnings: List[str] = field(default_factory=list)


class AuditService:
    """
    Analyzes telemetry execution spans to provide performance and cost auditing.
    """

    def __init__(
        self,
        store: SQLiteStateStore,
        input_cost_per_m: float = 0.15,
        output_cost_per_m: float = 0.60,
    ) -> None:
        self.store = store
        self.input_cost_per_m = input_cost_per_m
        self.output_cost_per_m = output_cost_per_m

    def audit_job(self, job_id: str) -> PerformanceAuditReport:
        """Audit all spans associated with a specific job execution."""
        all_spans = self.store.get_telemetry_spans(limit=1000)
        matching = [
            s
            for s in all_spans
            if s.trace_id == job_id
            or s.session_id == job_id
            or (s.metadata and s.metadata.get("step_context", {}).get("job_id") == job_id)
        ]
        return self._build_report(target_type="job", target_id=job_id, spans=matching)

    def audit_session(self, session_id: str) -> PerformanceAuditReport:
        """Audit all spans within a conversation session."""
        spans = self.store.get_telemetry_spans(session_id=session_id, limit=1000)
        return self._build_report(target_type="session", target_id=session_id, spans=spans)

    def audit_window(self, hours: int = 24) -> PerformanceAuditReport:
        """Audit all spans within the trailing time window."""
        cutoff = utc_now() - timedelta(hours=hours)
        all_spans = self.store.get_telemetry_spans(limit=2000)
        matching = []
        for s in all_spans:
            if s.created_at:
                try:
                    dt = s.created_at if isinstance(s.created_at, datetime) else datetime.fromisoformat(str(s.created_at))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt >= cutoff:
                        matching.append(s)
                except Exception:
                    matching.append(s)
            else:
                matching.append(s)
        return self._build_report(target_type="window", target_id=f"{hours}h", spans=matching)

    def _build_report(
        self, target_type: str, target_id: str, spans: List[TelemetrySpan]
    ) -> PerformanceAuditReport:
        turn_spans = [s for s in spans if s.span_type == "turn"]
        total_turns = len(turn_spans)
        total_wall_ms = round(sum(s.duration_ms for s in turn_spans), 2)

        ttft_vals = [s.ttft_ms for s in turn_spans if s.ttft_ms is not None]
        avg_ttft = round(sum(ttft_vals) / len(ttft_vals), 2) if ttft_vals else None

        tps_vals = []
        for s in turn_spans:
            if s.metadata and "timing_breakdown" in s.metadata:
                tps = s.metadata["timing_breakdown"].get("tokens_per_second")
                if tps:
                    tps_vals.append(tps)
        avg_tps = round(sum(tps_vals) / len(tps_vals), 2) if tps_vals else None

        tot_prompt = sum(s.prompt_tokens for s in turn_spans)
        tot_comp = sum(s.completion_tokens for s in turn_spans)

        tb_agg: Dict[str, int] = {
            "user_prompt": 0,
            "agent_persona": 0,
            "tool_schemas": 0,
            "progressive_skills": 0,
            "episodic_memory": 0,
            "compacted_history": 0,
            "tool_results_injected": 0,
            "completion": 0,
            "reasoning": 0,
        }

        for s in turn_spans:
            if s.metadata and "token_breakdown" in s.metadata:
                tb = s.metadata["token_breakdown"]
                for k in tb_agg:
                    tb_agg[k] += tb.get(k, 0)
            else:
                tb_agg["user_prompt"] += s.prompt_tokens
                tb_agg["completion"] += s.completion_tokens

        tot_reasoning = tb_agg["reasoning"]
        total_tokens = tot_prompt + tot_comp + tot_reasoning
        scaffold = tot_prompt - tb_agg["user_prompt"]
        scaffold_ratio = round(scaffold / max(tb_agg["user_prompt"], 1), 2)

        # Percentages of prompt tokens
        percentages: Dict[str, float] = {}
        for k in [
            "user_prompt",
            "agent_persona",
            "tool_schemas",
            "progressive_skills",
            "episodic_memory",
            "compacted_history",
            "tool_results_injected",
        ]:
            percentages[k] = round((tb_agg[k] / max(tot_prompt, 1)) * 100.0, 1)

        # Estimated cost
        cost = (tot_prompt / 1_000_000.0) * self.input_cost_per_m + (tot_comp / 1_000_000.0) * self.output_cost_per_m
        cost = round(cost, 6)

        # Warnings
        warnings = []
        if percentages["tool_schemas"] > 50.0:
            warnings.append(
                f"Tool schemas account for {percentages['tool_schemas']}% of prompt tokens (> 50%). Consider unmounting or scoping unused tools."
            )
        if percentages["compacted_history"] > 50.0:
            warnings.append(
                f"Compacted history accounts for {percentages['compacted_history']}% of prompt tokens (> 50%). Consider resetting or summarizing session."
            )
        if scaffold_ratio > 30.0:
            warnings.append(
                f"Harness Tax is high ({scaffold_ratio}x). Scaffold tokens ({scaffold}) significantly outweigh user prompt tokens ({tb_agg['user_prompt']})."
            )

        return PerformanceAuditReport(
            target_type=target_type,
            target_id=target_id,
            total_spans=len(spans),
            total_turns=total_turns,
            total_wall_clock_ms=total_wall_ms,
            avg_ttft_ms=avg_ttft,
            avg_tps=avg_tps,
            total_prompt_tokens=tot_prompt,
            total_completion_tokens=tot_comp,
            total_reasoning_tokens=tot_reasoning,
            total_tokens=total_tokens,
            token_breakdown=tb_agg,
            token_percentages=percentages,
            scaffold_tokens=scaffold,
            scaffold_ratio=scaffold_ratio,
            estimated_cost_usd=cost,
            warnings=warnings,
        )

    def format_markdown_report(self, report: PerformanceAuditReport) -> str:
        """Generate a formatted markdown report suitable for Wiki and chat output."""
        lines = [
            f"# Performance & Cost Audit: {report.target_type.upper()} `{report.target_id}`",
            "",
            "> Automated Harness Efficiency & Telemetry Attribution Report",
            "",
            "## 1. Executive Summary",
            "",
            "| Metric | Value |",
            "| :--- | :--- |",
            f"| Target | `{report.target_id}` ({report.target_type}) |",
            f"| Total Turns | {report.total_turns} |",
            f"| Total Wall-Clock Time | {report.total_wall_clock_ms / 1000.0:.2f}s |",
            f"| Avg TTFT | {report.avg_ttft_ms:.1f}ms |" if report.avg_ttft_ms is not None else "| Avg TTFT | N/A |",
            f"| Avg Generation Speed | {report.avg_tps:.1f} tok/s |" if report.avg_tps is not None else "| Avg Generation Speed | N/A |",
            f"| Total Tokens | {report.total_tokens:,} |",
            f"| Estimated Cost | ${report.estimated_cost_usd:.6f} |",
            f"| Harness Tax (Scaffold Ratio) | **{report.scaffold_ratio}x** |",
            "",
            "## 2. Granular Token Attribution",
            "",
            "| Component | Tokens | % of Prompt |",
            "| :--- | :--- | :--- |",
            f"| User Prompt | {report.token_breakdown.get('user_prompt', 0):,} | {report.token_percentages.get('user_prompt', 0.0):.1f}% |",
            f"| Agent Persona | {report.token_breakdown.get('agent_persona', 0):,} | {report.token_percentages.get('agent_persona', 0.0):.1f}% |",
            f"| Tool Schemas | {report.token_breakdown.get('tool_schemas', 0):,} | {report.token_percentages.get('tool_schemas', 0.0):.1f}% |",
            f"| Progressive Skills | {report.token_breakdown.get('progressive_skills', 0):,} | {report.token_percentages.get('progressive_skills', 0.0):.1f}% |",
            f"| Episodic Memory | {report.token_breakdown.get('episodic_memory', 0):,} | {report.token_percentages.get('episodic_memory', 0.0):.1f}% |",
            f"| Compacted History | {report.token_breakdown.get('compacted_history', 0):,} | {report.token_percentages.get('compacted_history', 0.0):.1f}% |",
            f"| Tool Results Injected | {report.token_breakdown.get('tool_results_injected', 0):,} | {report.token_percentages.get('tool_results_injected', 0.0):.1f}% |",
            f"| Completion Output | {report.token_breakdown.get('completion', 0):,} | - |",
            f"| Reasoning (<think>) | {report.token_breakdown.get('reasoning', 0):,} | - |",
            "",
            "## 3. Latency & Throughput",
            "",
            "| Stage | Measurement |",
            "| :--- | :--- |",
            f"| Wall-Clock Time | {report.total_wall_clock_ms:.1f}ms |",
            f"| Time to First Token (Avg) | {f'{report.avg_ttft_ms:.1f}ms' if report.avg_ttft_ms is not None else 'N/A'} |",
            f"| Generation Throughput (Avg) | {f'{report.avg_tps:.1f} tokens/s' if report.avg_tps is not None else 'N/A'} |",
            "",
        ]

        if report.warnings:
            lines.extend([
                "## ⚠️ Warnings & Recommendations",
                "",
            ])
            for w in report.warnings:
                lines.append(f"- {w}")
            lines.append("")

        return "\n".join(lines)
