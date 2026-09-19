"""
Architectural Evaluator Service [CARD-364, ADR-0054].
Scans historical session messages and telemetry turn spans, evaluates the
5 God-Agent thresholds, and persists alerts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.domain.observability.architectural_detector import ArchitecturalThresholdDetector
from src.domain.observability.models import (
    ArchitecturalAlert,
    ArchitecturalScanReport,
    ArchitecturalThresholdType,
)

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ArchitecturalEvaluatorService:
    """
    Coordinates historical analysis of session transcripts and telemetry spans.
    """

    def __init__(
        self,
        store: Any = None,
        detector: Optional[ArchitecturalThresholdDetector] = None,
        data_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.store = store
        self.detector = detector or ArchitecturalThresholdDetector()
        self.data_dir = Path(data_dir).expanduser().resolve() if data_dir else None
        self._cached_alerts: List[ArchitecturalAlert] = []

    def scan_history(
        self,
        lookback_hours: int = 24,
        session_limit: int = 50,
        span_limit: int = 500,
    ) -> ArchitecturalScanReport:
        """
        Scan recent sessions and telemetry spans against God-Agent thresholds.
        """
        all_alerts: List[ArchitecturalAlert] = []
        scanned_sessions = 0
        scanned_spans = 0

        cutoff = _utc_now() - timedelta(hours=lookback_hours)

        # 1. Scan Sessions
        if self.store and hasattr(self.store, "list_sessions"):
            try:
                sessions = self.store.list_sessions()
            except Exception as exc:
                logger.warning("Failed to list sessions for architectural scan: %s", exc)
                sessions = []

            for sess in sessions:
                if scanned_sessions >= session_limit:
                    break

                t = getattr(sess, "updated_at", None) or getattr(sess, "created_at", None)
                if t:
                    try:
                        if isinstance(t, str):
                            t_dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                        else:
                            t_dt = t
                        if t_dt.tzinfo is None:
                            t_dt = t_dt.replace(tzinfo=timezone.utc)
                        if t_dt < cutoff:
                            continue
                    except Exception:
                        pass

                agent_id = getattr(sess, "agent_id", "autoreiv") or "autoreiv"
                messages = []
                if hasattr(self.store, "get_messages"):
                    try:
                        messages = self.store.get_messages(sess.id)
                    except Exception:
                        messages = []

                session_alerts = self.detector.evaluate_session_messages(
                    session_id=sess.id,
                    agent_id=agent_id,
                    messages=messages,
                )
                all_alerts.extend(session_alerts)
                scanned_sessions += 1

        # 2. Scan Telemetry Turn Spans
        if self.store and hasattr(self.store, "get_telemetry_spans"):
            try:
                spans = self.store.get_telemetry_spans(span_type="turn", limit=span_limit)
            except Exception as exc:
                logger.warning("Failed to query telemetry spans for architectural scan: %s", exc)
                spans = []

            for span in spans:
                t = getattr(span, "created_at", None) or getattr(span, "start_time", None)
                if t:
                    try:
                        if isinstance(t, str):
                            t_dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                        else:
                            t_dt = t
                        if t_dt.tzinfo is None:
                            t_dt = t_dt.replace(tzinfo=timezone.utc)
                        if t_dt < cutoff:
                            continue
                    except Exception:
                        pass

                span_alerts = self.detector.evaluate_turn_span(span)
                all_alerts.extend(span_alerts)
                scanned_spans += 1

        # Deduplicate alerts
        deduped: List[ArchitecturalAlert] = []
        seen = set()
        for alert in all_alerts:
            key = (alert.threshold_type, alert.session_id, alert.agent_id, alert.evidence[:40])
            if key not in seen:
                seen.add(key)
                deduped.append(alert)

        self._cached_alerts = deduped
        self._persist_alerts(deduped)

        # Build type breakdown
        counts_by_type: Dict[str, int] = {}
        for a in deduped:
            val = a.threshold_type.value if hasattr(a.threshold_type, "value") else str(a.threshold_type)
            counts_by_type[val] = counts_by_type.get(val, 0) + 1

        clean = not any(a.severity in ("high", "critical") for a in deduped)

        return ArchitecturalScanReport(
            scanned_sessions=scanned_sessions,
            scanned_spans=scanned_spans,
            alert_count=len(deduped),
            alerts_by_type=counts_by_type,
            alerts=deduped,
            clean=clean,
        )

    def list_alerts(
        self,
        threshold_type: Optional[Union[str, ArchitecturalThresholdType]] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[ArchitecturalAlert]:
        """
        Query detected alerts with optional filters.
        """
        alerts = list(self._cached_alerts)
        if not alerts and self.data_dir:
            alerts = self._load_persisted_alerts()

        filtered = []
        for a in alerts:
            if threshold_type:
                target_val = (
                    threshold_type.value
                    if hasattr(threshold_type, "value")
                    else str(threshold_type)
                )
                a_val = a.threshold_type.value if hasattr(a.threshold_type, "value") else str(a.threshold_type)
                if a_val != target_val:
                    continue
            if severity and a.severity.lower() != severity.lower():
                continue
            filtered.append(a)
            if len(filtered) >= limit:
                break
        return filtered

    def _persist_alerts(self, alerts: List[ArchitecturalAlert]) -> None:
        if not self.data_dir:
            return
        try:
            target = self.data_dir / "telemetry"
            target.mkdir(parents=True, exist_ok=True)
            ledger_file = target / "architectural_alerts.json"
            data = [a.model_dump(mode="json") for a in alerts]
            ledger_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug("Failed to persist architectural alerts: %s", exc)

    def _load_persisted_alerts(self) -> List[ArchitecturalAlert]:
        if not self.data_dir:
            return []
        ledger_file = self.data_dir / "telemetry" / "architectural_alerts.json"
        if not ledger_file.is_file():
            return []
        try:
            raw = json.loads(ledger_file.read_text(encoding="utf-8"))
            return [ArchitecturalAlert.model_validate(item) for item in raw]
        except Exception as exc:
            logger.debug("Failed to load persisted architectural alerts: %s", exc)
            return []
