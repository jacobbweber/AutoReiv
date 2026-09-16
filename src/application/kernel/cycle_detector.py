"""
Cycle Detector [REQ-MEMORY-006, REQ-RESIL-003].
Detects repeating identical tool execution signatures and streaming text generation loops
to prevent infinite agent execution cycles.
"""

import hashlib
import json
from typing import List, Optional

from src.domain.gateway.models import ToolCall


class CycleDetector:
    """Detects repeated identical tool execution signatures and streaming token loops."""

    def __init__(self, max_repeats: int = 3, max_churn_repeats: int = 5):
        self.max_repeats = max_repeats
        self.max_churn_repeats = max_churn_repeats
        self._history: List[str] = []
        self._tool_name_history: List[tuple[str, ...]] = []
        self._text_chunks: List[str] = []

    def reset(self) -> None:
        """Reset internal detection buffers."""
        self._history.clear()
        self._tool_name_history.clear()
        self._text_chunks.clear()

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
        Record tool calls and check if:
        1. Exact identical signature repeats max_repeats times consecutively.
        2. Oscillating signature pattern repeats (e.g. A->B->A->B->A->B).
        3. Single tool argument churn: same tool invoked with churning arguments max_churn_repeats times without progress.
        Returns True if a repetition cycle or churn trap is detected [REQ-RESIL-003].
        """
        if not tool_calls:
            return False

        sig = self.compute_signature(tool_calls)
        self._history.append(sig)

        names = tuple(tc.name for tc in tool_calls)
        self._tool_name_history.append(names)

        # 1. Exact identical signature cycle
        if len(self._history) >= self.max_repeats:
            recent = self._history[-self.max_repeats :]
            if all(s == sig for s in recent):
                return True

        # 2. Oscillating signature cycle (period 2 or 3)
        for period in (2, 3):
            cycle_len = period * self.max_repeats
            if len(self._history) >= cycle_len:
                pattern = self._history[-period:]
                matched = True
                for step in range(1, self.max_repeats):
                    start = len(self._history) - (step + 1) * period
                    end = len(self._history) - step * period
                    if self._history[start:end] != pattern:
                        matched = False
                        break
                if matched:
                    return True

        # 3. Argument churn / thrashing detection on same tool name
        if len(self._tool_name_history) >= self.max_churn_repeats:
            recent_names = self._tool_name_history[-self.max_churn_repeats :]
            if all(n == names for n in recent_names):
                return True

        return False

    def record_and_check_text(
        self,
        text: str,
        min_phrase_len: int = 15,
        repeats_threshold: int = 3,
    ) -> bool:
        """
        Detects repeating phrases, sentences, or token loops in generated text [REQ-RESIL-003].
        Checks both character patterns and word n-gram suffix repetitions.
        """
        if not text or len(text) < min_phrase_len * repeats_threshold:
            return False

        # 1. Word-level n-gram cycle detection
        words = text.strip().split()
        total_words = len(words)
        if total_words >= repeats_threshold * 3:
            max_gram_len = min(50, total_words // repeats_threshold)
            for gram_len in range(3, max_gram_len + 1):
                target_gram = words[-gram_len:]
                matches = 1
                for step in range(1, repeats_threshold):
                    start = total_words - (step + 1) * gram_len
                    end = total_words - step * gram_len
                    if words[start:end] == target_gram:
                        matches += 1
                    else:
                        break
                if matches >= repeats_threshold:
                    return True

        # 2. Character-level exact suffix cycle detection
        cleaned = text.strip()
        tail_len = min_phrase_len * repeats_threshold * 4
        tail = cleaned[-tail_len:]

        for phrase_len in range(min_phrase_len, len(tail) // repeats_threshold + 1):
            pattern = tail[-phrase_len:]
            consecutive_matches = 1
            idx = len(tail) - phrase_len

            while idx >= phrase_len:
                prev_chunk = tail[idx - phrase_len : idx]
                if prev_chunk == pattern:
                    consecutive_matches += 1
                    idx -= phrase_len
                    if consecutive_matches >= repeats_threshold:
                        return True
                else:
                    break

        return False
