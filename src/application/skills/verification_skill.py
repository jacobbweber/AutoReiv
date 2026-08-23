"""
Verification Skill [REQ-VERIFY-001, REQ-VERIFY-004].
Provides deterministic programmatic assertion tools for self-verifying agent workflows.
"""

import json
from typing import Any, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class VerificationSkill:
    """Skill exposing programmatic verification and discrepancy diagnostic assertions."""

    def __init__(self, store: SQLiteStateStore):
        self.store = store

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register verification tools into ScopedToolRegistry."""
        registry.register_tool(
            name="verify_telemetry_consistency",
            description="Programmatically assert that reported error counts match SQLite telemetry database spans.",
            parameters={
                "type": "object",
                "properties": {
                    "reported_errors": {
                        "type": "integer",
                        "description": "Number of tool/turn errors claimed by agent",
                    },
                    "reported_total_spans": {
                        "type": "integer",
                        "description": "Total spans claimed by agent (optional)",
                    },
                },
                "required": ["reported_errors"],
            },
            handler=self.verify_telemetry_consistency,
        )

        registry.register_tool(
            name="assert_json_schema",
            description="Validate JSON string syntax and assert presence of required keys.",
            parameters={
                "type": "object",
                "properties": {
                    "payload": {"type": "string", "description": "JSON string to validate"},
                    "required_keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Required schema keys",
                    },
                },
                "required": ["payload", "required_keys"],
            },
            handler=self.assert_json_schema,
        )

        registry.register_tool(
            name="validate_metric_bounds",
            description="Assert that a numerical metric lies strictly within expected min/max boundaries.",
            parameters={
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string"},
                    "value": {"type": "number"},
                    "min_val": {"type": "number"},
                    "max_val": {"type": "number"},
                },
                "required": ["metric_name", "value", "min_val", "max_val"],
            },
            handler=self.validate_metric_bounds,
        )

    def verify_telemetry_consistency(
        self,
        reported_errors: int,
        reported_total_spans: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Assert reported error metrics against SQLite ground truth."""
        all_spans = self.store.get_telemetry_spans(limit=10000)
        actual_errors = sum(1 for s in all_spans if not s.success)
        actual_total = len(all_spans)

        discrepancies: List[str] = []
        if reported_errors != actual_errors:
            discrepancies.append(
                f"Discrepancy: Agent reported {reported_errors} errors, but Database recorded {actual_errors} failed spans."
            )

        if reported_total_spans is not None and reported_total_spans != actual_total:
            discrepancies.append(
                f"Discrepancy: Agent reported {reported_total_spans} total spans, but Database recorded {actual_total} spans."
            )

        is_valid = len(discrepancies) == 0
        return {
            "is_valid": is_valid,
            "discrepancies": discrepancies,
            "ground_truth": {
                "actual_errors": actual_errors,
                "actual_total_spans": actual_total,
            },
            "status": "pass" if is_valid else "fail",
        }

    def assert_json_schema(
        self,
        payload: str,
        required_keys: List[str],
    ) -> Dict[str, Any]:
        """Validate JSON format and key requirements."""
        discrepancies: List[str] = []
        parsed_data = None
        try:
            parsed_data = json.loads(payload)
            if not isinstance(parsed_data, dict):
                discrepancies.append(f"Expected JSON object (dict), got {type(parsed_data).__name__}.")
            else:
                for key in required_keys:
                    if key not in parsed_data:
                        discrepancies.append(f"Missing required key: '{key}' in JSON payload.")
        except Exception as e:
            discrepancies.append(f"Invalid JSON syntax: {e}")

        is_valid = len(discrepancies) == 0
        return {
            "is_valid": is_valid,
            "discrepancies": discrepancies,
            "parsed": parsed_data if is_valid else None,
            "status": "pass" if is_valid else "fail",
        }

    def validate_metric_bounds(
        self,
        metric_name: str,
        value: float,
        min_val: float,
        max_val: float,
    ) -> Dict[str, Any]:
        """Check numerical bound constraints."""
        discrepancies: List[str] = []
        if value < min_val:
            discrepancies.append(f"Metric '{metric_name}' value {value} is below minimum bound {min_val}.")
        elif value > max_val:
            discrepancies.append(f"Metric '{metric_name}' value {value} exceeds maximum bound {max_val}.")

        is_valid = len(discrepancies) == 0
        return {
            "is_valid": is_valid,
            "discrepancies": discrepancies,
            "metric_name": metric_name,
            "value": value,
            "status": "pass" if is_valid else "fail",
        }
