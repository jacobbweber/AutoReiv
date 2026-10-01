"""Keep the words already shown when a reply is stopped [CARD-489].

The chat worker watches the kernel's token events for the current model call. When Stop cancels the
worker, the partial text is saved as an assistant row ending with ``STOPPED_MARKER``. Because the
marker is part of the text, the next turn's model context sees the words labelled as stopped (D2).
Nothing is saved when Stop comes before the first token [REQ-489-003].
"""

from __future__ import annotations

from typing import List, Optional

from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import KernelEvent, KernelEventType

STOPPED_MARKER = "_(Stopped)_"

# Events after which the kernel has already saved (or will not save) the streamed text.
_BOUNDARY = frozenset(
    {
        KernelEventType.TOOL_START,
        KernelEventType.HANDOFF_START,
        KernelEventType.APPROVAL_REQUIRED,
        KernelEventType.TURN_END,
        KernelEventType.ERROR,
    }
)


class PartialReply:
    """Text streamed since the last saved assistant row."""

    def __init__(self) -> None:
        self._parts: List[str] = []

    def observe(self, event: KernelEvent) -> None:
        if event.event_type == KernelEventType.TOKEN:
            if event.content:
                self._parts.append(event.content)
        elif event.event_type in _BOUNDARY:
            self._parts.clear()

    def text(self) -> str:
        return "".join(self._parts)


def stopped_message(text: str) -> Optional[ChatMessage]:
    """The assistant row to save for a stopped reply, or None when nothing was shown."""
    body = (text or "").rstrip()
    if not body.strip():
        return None
    return ChatMessage(role=Role.ASSISTANT, content=f"{body}\n\n{STOPPED_MARKER}")
