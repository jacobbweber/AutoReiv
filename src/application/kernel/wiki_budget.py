"""CARD-605: a per-reply budget for wiki look-ups.

AutoReiv sometimes made about 21 ``wiki_note_search`` / ``wiki_note_list`` calls in one reply while looking for
notes that do not exist. The CARD-551 repeat guard does not catch it because the arguments differ each time.

After the Settings > Reply limits "Wiki look-ups per reply" value (default 8) in one reply, further look-ups are
not run; the model gets a short
"Not run: ..." result telling it to answer with what it has and to say plainly when nothing matched.
"""

from __future__ import annotations

from typing import Any, List, Optional

from src.application.chat.past_chat_search import (
    MAX_SEARCHES_PER_TURN,
    PAST_CHATS_TOOL_NAME,
    answer_now,
)
from src.application.kernel.reply_limits import DEFAULT_WIKI_LOOKUPS
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import ToolResult

WIKI_LOOKUP_TOOLS = frozenset({"wiki_note_search", "wiki_note_list"})

WIKI_BUDGET_RESULT = (
    "Not run: you already looked in the wiki {n} times in this reply. Do not search or list the wiki again now. "
    "Answer with what you found. If nothing matched, say plainly that no matching note was found."
)

WIKI_LOOKUP_HINT = " If two or three look-ups find nothing, stop and say plainly that no matching note was found."


class WikiLookupBudget:
    """Counts wiki look-ups and past-chat searches in one reply; past the budget they are answered without running."""

    def __init__(
        self,
        budget: int = DEFAULT_WIKI_LOOKUPS,
        past_chat_budget: int = MAX_SEARCHES_PER_TURN,
    ) -> None:
        self.budget = budget
        self.used = 0
        self.refused = 0
        self.past_chat_budget = past_chat_budget
        self.past_chat_used = 0

    @property
    def used_up(self) -> bool:
        return self.used >= self.budget

    @property
    def past_chat_used_up(self) -> bool:
        return self.past_chat_used >= self.past_chat_budget

    def offer(self, tools: Optional[List[Any]]) -> Optional[List[Any]]:
        """The tools to offer on the next model call: without the look-up tools once their budget is used up."""
        if not tools:
            return tools
        out = tools
        if self.used_up:
            out = [t for t in out if getattr(t, "name", None) not in WIKI_LOOKUP_TOOLS]
        if self.past_chat_used_up:
            out = [t for t in out if getattr(t, "name", None) != PAST_CHATS_TOOL_NAME]
        return out

    def check(self, tc: ToolCall) -> Optional[ToolResult]:
        """None when the call may run (and counts it, even if it then errors or is a repeat); else "Not run"."""
        if tc.name == PAST_CHATS_TOOL_NAME:
            if self.past_chat_used >= self.past_chat_budget:
                self.refused += 1
                return ToolResult(
                    call_id=tc.id,
                    tool_name=tc.name,
                    success=True,
                    output=answer_now(self.past_chat_used),
                    duration_ms=0.0,
                )
            self.past_chat_used += 1
            return None

        if tc.name not in WIKI_LOOKUP_TOOLS:
            return None
        if self.used >= self.budget:
            self.refused += 1
            return ToolResult(
                call_id=tc.id,
                tool_name=tc.name,
                success=True,
                output=WIKI_BUDGET_RESULT.format(n=self.used),
                duration_ms=0.0,
            )
        self.used += 1
        return None
