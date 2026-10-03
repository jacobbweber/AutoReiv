"""CARD-551 / CARD-460: repeat guard and the no-tools final answer.

- A tool call identical (name + arguments) to one that ran in the immediately previous step is not run again; the
  model gets the earlier result back with a notice. Tools meant to be polled (``REPEAT_SAFE_TOOLS``) always run.
- CARD-613: a tool the operator rejected since the last user message is not offered again in that reply, and a
  call to it is refused with a plain "rejected, do not call it again" result (no new approval card).
- When the cycle detector still fires (third identical call, or an A,B,A,B,A,B loop), the kernel makes one last model
  call with no tools so the user gets an answer built from the tool results already in hand, instead of
  "Execution terminated".
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, Iterable, Optional, Set

from src.domain.gateway.models import Role, ToolCall
from src.domain.kernel.models import ToolResult

# Tools whose identical call can legitimately return new data (polling / status reads).
REPEAT_SAFE_TOOLS = frozenset({
    "git_status",
    "get_recent_errors",
    "get_tool_health_matrix",
    "inspect_system_health",
})

LOOP_FINAL_INSTRUCTION = (
    "(AutoReiv) You are repeating the same tool call. Do not call any tools now. Using the tool results you already "
    "have in this conversation, answer my last request directly. If something is still missing, say briefly what "
    "and why."
)
LOOP_FALLBACK_MESSAGE = (
    "I stopped because I kept repeating the same step without getting further. The results so far are above; "
    "tell me how you'd like to continue, or ask again with more detail."
)
TEXT_LOOP_MESSAGE = (
    "I stopped because my reply started repeating itself. Please ask again, or ask for a smaller step."
)


REJECTED_PREFIX = "Rejected. Tool did not run."
TOOL_REJECTED = "tool_rejected"  # refusal code; a self-correcting refusal, not a failure


def rejection_text(tool_name: str) -> str:
    """CARD-613: the TOOL row the model reads after the operator rejects an approval card."""
    return (
        f"{REJECTED_PREFIX} The operator rejected this {tool_name} call. Do not call {tool_name} again for this "
        "request: finish without it (give the result in your reply instead) and say plainly what was not done."
    )


def rejected_tool_names(history: Iterable) -> Set[str]:
    """Tools the operator rejected since the last user message (rejection TOOL rows)."""
    names: Set[str] = set()
    for msg in history or []:
        role = getattr(msg, "role", None)
        if role == Role.USER:
            names = set()
        elif role == Role.TOOL and str(getattr(msg, "content", "") or "").startswith(REJECTED_PREFIX):
            if getattr(msg, "name", None):
                names.add(str(msg.name))
    return names


def call_signature(tc: ToolCall) -> str:
    try:
        args = json.dumps(tc.arguments or {}, sort_keys=True, default=str)
    except (TypeError, ValueError):
        args = str(tc.arguments)
    return hashlib.sha256(f"{tc.name}:{args}".encode("utf-8")).hexdigest()


class RepeatGuard:
    """Per-reply record of the previous step's executed calls and their results."""

    def __init__(self, rejected: Optional[Iterable[str]] = None) -> None:
        self._previous: Dict[str, ToolResult] = {}
        self._current: Dict[str, ToolResult] = {}
        self.rejected: Set[str] = set(rejected or ())  # CARD-613

    def next_step(self) -> None:
        self._previous, self._current = self._current, {}

    def reuse(self, tc: ToolCall) -> Optional[ToolResult]:
        """The earlier result (with a notice) when this exact call ran in the previous step, else None.
        CARD-613: a call to a tool the operator rejected in this reply is refused without a new approval card."""
        if tc.name in self.rejected:
            return ToolResult(
                call_id=tc.id,
                tool_name=tc.name,
                success=False,
                output=None,
                error=(
                    f"{TOOL_REJECTED}: the operator already rejected {tc.name} for this request, so it was not run. "
                    "Do not call it again: finish without it and say plainly what was not done."
                ),
                duration_ms=0.0,
            )
        if tc.name in REPEAT_SAFE_TOOLS:
            return None
        earlier = self._previous.get(call_signature(tc))
        if earlier is None:
            return None
        return ToolResult(
            call_id=tc.id,
            tool_name=tc.name,
            success=True,
            output={
                "already_done": True,
                "notice": (
                    f"Already done: you called {tc.name} with these exact arguments in the previous step, so it was "
                    "not run again. Here is that result. Use it, or try a different approach."
                ),
                "result": earlier.output,
            },
            duration_ms=0.0,
        )

    def record(self, tc: ToolCall, result: ToolResult) -> None:
        """Remember a call that really ran and succeeded (never a parked approval or an error)."""
        if not result.success or result.error:
            return
        out = result.output if isinstance(result.output, dict) else None
        if out and (out.get("status") == "approval_required" or out.get("already_done")):
            return
        self._current[call_signature(tc)] = result
