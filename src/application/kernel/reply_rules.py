"""Reply honesty rules for agent turns [CARD-599, CARD-600].

- CARD-599: a platform rule in the generated instructions: do every part of a multi-part request, and end by
  naming any part that was not done and why.
- CARD-600 item 5: ``ask_clarification`` ends the turn; the question is the reply and the next user message
  answers it.
- CARD-600 item 7: when the turn's last failed tool call is not mentioned in the final reply, one plain line is
  appended: "Note: <tool> failed: <short error>." No re-prompt.
"""

from __future__ import annotations

import re
from typing import Any, Optional, Tuple

CLARIFICATION_TOOL = "ask_clarification"

REPLY_RULES_BLOCK = (
    "## Answering\n"
    "- If the request has several parts, do each one. End by listing any part you did not do and why.\n"
    "- If you call ask_clarification, that ends your turn: wait for the user's answer before doing anything else."
)

CLARIFICATION_SKIPPED_RESULT = "Not run: the turn ended to wait for the user's answer to the clarification question."

_NOTE_ERROR_MAX = 160
# Words that already tell the user a step did not work.
_FAILURE_WORDS = re.compile(
    r"\b(fail(ed|s|ure)?|error(ed|s)?|could ?n[o']?t|unable|did ?n[o']?t work|was ?n[o']?t able|not able)\b",
    re.IGNORECASE,
)


def clarification_question(tool_name: str, success: bool, output: Any, arguments: Any = None) -> Optional[str]:
    """The question when this tool call asked the user to clarify, else None."""
    if tool_name != CLARIFICATION_TOOL or not success:
        return None
    question = ""
    if isinstance(output, dict):
        question = str(output.get("question") or "").strip()
    if not question and isinstance(arguments, dict):
        question = str(arguments.get("question") or "").strip()
    return question or None


def clarification_reply(question: str, streamed_text: str = "") -> str:
    """The text shown for a clarification stop; the question once, even when the model already wrote it."""
    q = (question or "").strip()
    if q and q in (streamed_text or ""):
        return ""
    return q


def counts_as_failure(tool_name: str, success: bool, error: Optional[str]) -> bool:
    """A real failure: not an approval park and not the clarification stop."""
    if success or tool_name == CLARIFICATION_TOOL:
        return False
    return not str(error or "").startswith("approval_required:")


def track_failure(last: Optional[Tuple[str, str]], tool_name: str, success: bool, error: Optional[str]) -> Optional[Tuple[str, str]]:
    """Update the turn's last failed tool call; a later success of the same tool clears it."""
    if counts_as_failure(tool_name, success, error):
        return (tool_name, str(error or "unknown error"))
    if success and last and last[0] == tool_name:
        return None
    return last


def short_error(error: str) -> str:
    text = re.sub(r"^\s*(tool error:\s*)+", "", str(error or ""), flags=re.IGNORECASE).strip()
    text = (text.splitlines() or [""])[0].strip() or "unknown error"
    if len(text) > _NOTE_ERROR_MAX:
        text = text[: _NOTE_ERROR_MAX - 3].rstrip() + "..."
    return text.rstrip(". ")


def mentions_failure(reply: str, tool_name: str, error: str) -> bool:
    """True when the reply already tells the user about the failed call."""
    text = (reply or "").lower()
    if not text.strip():
        return False
    name = (tool_name or "").lower()
    if name and (name in text or name.replace("_", " ") in text):
        return True
    err = short_error(error).lower()
    if len(err) >= 12 and err[:40] in text:
        return True
    return bool(_FAILURE_WORDS.search(text))


def failed_tool_note(reply: str, last_failure: Optional[Tuple[str, str]]) -> str:
    """The one-line note to append, or "" when there is no failure or the reply already mentions it."""
    if not last_failure:
        return ""
    tool_name, error = last_failure
    if mentions_failure(reply, tool_name, error):
        return ""
    return f"Note: {tool_name} failed: {short_error(error)}."
