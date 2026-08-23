"""
Cycle Detector [REQ-MEMORY-006].
Detects repeating identical tool execution signatures to prevent infinite agent reasoning loops.
"""

import hashlib
import json
from typing import List, Optional

from src.domain.gateway.models import ToolCall


class CycleDetector:
    """Detects repeated identical tool execution signatures in agent turns."""

    def __init__(self, max_repeats: int = 3):
        self.max_repeats = max_repeats
        self._history: List[str] = []

    def compute_signature(self, tool_calls: List[ToolCall]) -> str:
        """Create a deterministic hash from a batch of tool calls."""
        elements = []
        for tc in tool_calls:
            args_str = json.dumps(tc.arguments or {}, sort_keys=True)
            elements.append(f"{tc.name}:{args_str}")
        raw = "|".join(elements)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def record_and_check(self, tool_calls: Optional[List[ToolCall]]) -> bool:
        """
        Record tool calls and check if the signature has repeated consecutively max_repeats times.
        Returns True if a repetition cycle is detected.
        """
        if not tool_calls:
            return False

        sig = self.compute_signature(tool_calls)
        self._history.append(sig)

        if len(self._history) >= self.max_repeats:
            recent = self._history[-self.max_repeats :]
            if all(s == sig for s in recent):
                return True

        return False
