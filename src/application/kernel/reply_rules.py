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
    r"\b(fail(ed|s|ure)?|error(ed|s)?|could ?n[o']?t|unable|did ?n[o']?t work|was ?n[o']?t able|not able"
    r"|not found|does ?n[o']?t exist|no such)\b",
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


def output_failure(output: Any) -> Optional[str]:
    """The error of a tool that ran but reported a failure in its result ({"success": false, "error": ...})."""
    if not isinstance(output, dict):
        return None
    status = str(output.get("status") or "").lower()
    if output.get("success") is False or status in ("error", "failed"):
        return str(output.get("error") or output.get("message") or status or "failed")
    return None


def counts_as_failure(tool_name: str, success: bool, error: Optional[str], output: Any = None) -> bool:
    """A real failure: not an approval park and not the clarification stop."""
    if tool_name == CLARIFICATION_TOOL:
        return False
    if success:
        return output_failure(output) is not None
    return not str(error or "").startswith("approval_required:")


def track_failure(
    last: Optional[Tuple[str, str]], tool_name: str, success: bool, error: Optional[str], output: Any = None
) -> Optional[Tuple[str, str]]:
    """Update the turn's last failed tool call; a later success of the same tool clears it."""
    if counts_as_failure(tool_name, success, error, output):
        return (tool_name, str(error or output_failure(output) or "unknown error"))
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


# ---------------- CARD-599 (b): a short no-tools check for skipped parts ----------------

NOT_DONE_PREFIX = "Not done:"
_MAX_NOT_DONE_LINES = 6
_PART_SPLIT = re.compile(
    r"\n\s*(?:\d+[.)]|[-*•])\s+|;|\?|,\s*(?:and\s+|then\s+|also\s+)?|\s+and then\s+|\s+then\s+|\s+and also\s+|\s+plus\s+",
    re.IGNORECASE,
)
_ALREADY_SAID_SKIPPED = re.compile(r"\b(not done|skipped|did ?n[o']?t do|could ?n[o']?t do|was ?n[o']?t able to)\b", re.IGNORECASE)


def request_parts(text: str) -> int:
    """Rough count of separate asks in a user message (numbered items, commas, "then", questions)."""
    parts = [p.strip() for p in _PART_SPLIT.split(str(text or "")) if p and p.strip()]
    return sum(1 for p in parts if len(p.split()) >= 2)


def needs_parts_check(user_text: str, reply: str) -> bool:
    """Only multi-part requests (3+ asks) whose reply does not already name a skipped part."""
    if request_parts(user_text) < 3 or not str(reply or "").strip():
        return False
    return not _ALREADY_SAID_SKIPPED.search(reply)


def parts_check_prompt(user_text: str, tools_ran: list, reply: str) -> str:
    ran = "\n".join(f"- {t}" for t in tools_ran) if tools_ran else "- none"
    return (
        "You check whether an assistant's reply covered every part of the user's request. Do not call tools. "
        "Keep your thinking short.\n\n"
        f"User's request:\n{user_text.strip()}\n\n"
        f"Tools that ran this turn:\n{ran}\n\n"
        f"Assistant's reply:\n{reply.strip()}\n\n"
        "Split the request into its separate parts and go through them in order. A part that asks for an action "
        "(remember, save, create, update, send, search, read, list, look up) is done only when a tool above did "
        "that action and did not fail; recalling something is not remembering it, and a reply that only says it was "
        "done does not count. A question is done when the reply answers it. For each part write exactly one line:\n"
        "Done: <the part in a few words> - <the tool that did it, or: answered>\n"
        f"{NOT_DONE_PREFIX} <the part in a few words>.\n"
        "Write nothing else."
    )


def parse_parts_check(text: str) -> str:
    """The "Not done: ..." lines from the checker, or "" when it found nothing skipped."""
    lines = []
    for raw in str(text or "").splitlines():
        line = raw.strip().lstrip("-*• ").strip()
        if line.lower().startswith(NOT_DONE_PREFIX.lower()):
            body = line[len(NOT_DONE_PREFIX):].strip().rstrip(".").strip()
            if body:
                lines.append(f"{NOT_DONE_PREFIX} {body[:160]}.")
    return "\n".join(lines[:_MAX_NOT_DONE_LINES])


def describe_tool_run(tool_name: str, arguments: Any, failed: bool) -> str:
    args = ""
    if isinstance(arguments, dict) and arguments:
        args = ", ".join(f"{k}={str(v)[:60]}" for k, v in list(arguments.items())[:4])
    return f"{tool_name}({args}) {'failed' if failed else 'ok'}"
