"""Reply honesty rules for agent turns [CARD-599, CARD-600].

- CARD-599: a platform rule in the generated instructions: do every part of a multi-part request, and end by
  naming any part that was not done and why.
- CARD-600 item 5: ``ask_clarification`` ends the turn; the question is the reply and the next user message
  answers it.
- CARD-600 item 7: when the turn's last failed tool call is not mentioned in the final reply, one plain line is
  appended: "Note: <tool> failed: <short error>." No re-prompt.
- CARD-615: the "You can use Ask Developer to add this." ending is added here, not by the prompt: only when a
  tool is truly missing (a call refused as unknown or not the agent's, and nothing else ran OK) or the reply
  turns the request down without using any tool. The model's own copy is dropped otherwise.
"""

from __future__ import annotations

import re
from typing import Any, Collection, Optional, Sequence, Tuple

from src.application.kernel.tool_registry import NO_SUCH_TOOL, is_self_correcting_refusal
from src.domain.capabilities.missing_tool import find_missing_tool, names_own_tool

CLARIFICATION_TOOL = "ask_clarification"

# CARD-615
ASK_DEVELOPER_LINE = "You can use Ask Developer to add this."
_ASK_DEVELOPER_TEXT = re.compile(r"\b(?:use|try|via|through|with)\s+(?:the\s+)?[*_`\"']*Ask Developer\b", re.IGNORECASE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_MISSING_TOOL_MARKERS = (NO_SUCH_TOOL, "not found in system registry", "is not authorized for agent")
_FAILED_TOOL_PREFIXES = ("Tool Error:", "Rejected. Tool did not run.")
# CARD-663: "the reply admits a missing tool" is the shared matcher in src.domain.capabilities.missing_tool.
_NO_AGENT_COVERS = re.compile(r"\bno (?:other )?agent\b[^.\n]{0,60}?\bcover", re.IGNORECASE)
_POINTS_TO_AGENT = re.compile(r"\bopen [\w' -]{1,40}? in Chat\b", re.IGNORECASE)


def is_toolsmith(agent: Any) -> bool:
    return str(getattr(agent, "id", "") or "").strip().lower() == "toolsmith"


def _role(message: Any) -> str:
    return str(getattr(message, "role", "") or "").lower()


def turn_tool_rows(history: Sequence[Any]) -> list:
    """CARD-615: tool result texts since the latest user message (this request, incl. a resumed approval)."""
    rows: list = []
    for message in reversed(list(history or [])):
        role = _role(message)
        if role.endswith("user"):
            break
        if role.endswith("tool"):
            rows.append(str(getattr(message, "content", "") or ""))
    return rows


def _strip_ask_developer(text: str) -> str:
    """Drop each sentence that sends the user to Ask Developer; a line left empty goes too."""
    lines = []
    for line in text.split("\n"):
        if not _ASK_DEVELOPER_TEXT.search(line):
            lines.append(line)
            continue
        kept = " ".join(s for s in _SENTENCE_END.split(line.strip()) if not _ASK_DEVELOPER_TEXT.search(s))
        if kept.strip(" *_-"):
            lines.append(kept)
    return "\n".join(lines)


def _gap_sentence(body: str, gap_text: str) -> str:
    """The sentence saying a capability is missing (CapabilityDetector's text, or the shared matcher [CARD-663])."""
    if gap_text:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", body):
            if gap_text in sentence:
                return sentence
    found = find_missing_tool(body)
    return found.sentence if found else gap_text


def ask_developer_ending(
    reply: str,
    history: Sequence[Any],
    gap_text: Optional[str] = None,
    own_tools: Collection[str] = (),
    offer: bool = True,
) -> str:
    """CARD-615: the final reply with the Ask Developer line only when a tool is truly missing.

    The line is added when (a) a call was refused because no such tool exists / it is not the agent's and nothing
    else ran OK, (b) the reply says it lacks a capability (gap_text, from CapabilityDetector) that is not one of the
    agent's own tools and nothing was rejected, or (c) no tool was used and the reply turns the request down
    ("No agent covers ...") without pointing at another agent. Otherwise the model's own copy is dropped.
    offer=False (Toolsmith, the developer itself) only drops the model's copy.
    """
    text = reply or ""
    body = _strip_ask_developer(text).rstrip()
    had_line = body != text.rstrip()
    rows = turn_tool_rows(history)
    missing = any(marker in row for row in rows for marker in _MISSING_TOOL_MARKERS)
    succeeded = any(not row.lstrip().startswith(_FAILED_TOOL_PREFIXES) for row in rows)
    rejected = any(row.lstrip().startswith(_FAILED_TOOL_PREFIXES[1]) for row in rows)
    gap_sentence = _gap_sentence(body, gap_text or "")
    gap_is_own_tool = bool(gap_sentence) and names_own_tool(gap_sentence, own_tools)
    real_gap = bool(gap_sentence) and not gap_is_own_tool and not rejected
    said_no = real_gap or had_line or bool(_NO_AGENT_COVERS.search(body))
    turned_down = not rows and said_no and not gap_is_own_tool and not _POINTS_TO_AGENT.search(body)
    if offer and ((missing and not succeeded) or turned_down or (rows and real_gap)):
        return f"{body}\n\n{ASK_DEVELOPER_LINE}" if body else ASK_DEVELOPER_LINE
    return body if had_line else text

REPLY_RULES_BLOCK = (
    "## Answering\n"
    "- If the request has several parts, do each one. End by listing any part you did not do and why.\n"
    "- If you call ask_clarification, that ends your turn: wait for the user's answer before doing anything else.\n"
    "- When asked to remember something, save it with memorize_fact in the same reply. Never say it is saved "
    "without that call."
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
    """A real failure: not an approval park, not the clarification stop, and not a refused call that ran
    nothing and told the model how to fix it (wrong tool, not offered, bad arguments) [CARD-607/610]."""
    if tool_name == CLARIFICATION_TOOL:
        return False
    if success:
        return output_failure(output) is not None
    text = str(error or "")
    return not text.startswith("approval_required:") and not is_self_correcting_refusal(text)


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
    text = re.sub(r"^[a-z]+(?:_[a-z]+)+:\s*", "", text)  # machine codes such as tool_not_offered:
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
# CARD-612: a platform-written brief (Ask Developer) carries this line before its working notes. A brief is one work
# order (build and register the tool), not a multi-part request: its fields, notes and the example question copied
# from a capability gap read as separate asks and gave false "Not done" lines (live QA 2026-10-03).
BRIEF_NOTES_MARKER = "Notes for this work (not separate asks):"


def request_parts(text: str) -> int:
    """Rough count of separate asks in a user message (numbered items, commas, "then", questions)."""
    parts = [p.strip() for p in _PART_SPLIT.split(str(text or "")) if p and p.strip()]
    return sum(1 for p in parts if len(p.split()) >= 2)


def needs_parts_check(user_text: str, reply: str) -> bool:
    """Only multi-part requests (3+ asks) whose reply does not already name a skipped part; never a platform brief."""
    if BRIEF_NOTES_MARKER in str(user_text or ""):
        return False
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
        "that action and did not fail; a reply that only says it was done does not count. Remembering or saving a "
        "fact is done only by memorize_fact (recall_agent_memory does not save anything); recalling or looking up "
        "memory is done by recall_agent_memory. Registering a tool is done by register_native_tool; with target_agent_id it "
        "also proposes the tool for that agent. A question is done when the reply answers it. Details such as a name, "
        "a hint or a path are not separate parts. For each part write exactly one line:\n"
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


def describe_tool_run(tool_name: str, arguments: Any, failed: bool, output: Any = None) -> str:
    """One line for the skipped-parts checker; a result that reports a failure counts as failed [CARD-612]."""
    failed = failed or output_failure(output) is not None
    args = ""
    if isinstance(arguments, dict) and arguments:
        # CARD-612: short values first, so a target_agent_id is not hidden behind a long code argument.
        items = sorted(arguments.items(), key=lambda kv: len(str(kv[1])))[:6]
        args = ", ".join(f"{k}={str(v)[:60]}" for k, v in items)
    return f"{tool_name}({args}) {'failed' if failed else 'ok'}"


# ---------------- CARD-604: memory asks in multi-part requests ----------------

MEMORIZE_TOOL = "memorize_fact"
RECALL_TOOL = "recall_agent_memory"
REGISTER_TOOL = "register_native_tool"  # CARD-612
_TOOL_WORK = re.compile(r"\b(tool|register\w*|attach\w*|target agent)\b", re.IGNORECASE)
_MEMORY_RECALL = re.compile(r"\b(recall|look ?up (?:my |the |your )?memor(?:y|ies)|what (?:do )?you remember)\b", re.IGNORECASE)
_MEMORY_SAVE = re.compile(r"\b(remember|memori[sz]e|keep in mind)\b", re.IGNORECASE)


def _memory_kind(part: str) -> str:
    """"recall", "save" or "" for one "Not done: ..." line."""
    if _MEMORY_RECALL.search(part or ""):
        return "recall"
    if _MEMORY_SAVE.search(part or ""):
        return "save"
    return ""


def _tool_ok(tools_ran: list, tool_name: str) -> bool:
    return any(str(t).startswith(f"{tool_name}(") and str(t).endswith(" ok") for t in (tools_ran or []))


def drop_false_not_done(not_done: str, tools_ran: list) -> str:
    """Drop a "Not done" line when the tool that does it ran and succeeded (checker false positive):
    memory lines after memorize_fact / recall_agent_memory, tool lines after register_native_tool [CARD-604/612]."""
    keep = []
    for line in str(not_done or "").splitlines():
        kind = _memory_kind(line)
        if kind == "recall" and _tool_ok(tools_ran, RECALL_TOOL):
            continue
        if kind == "save" and _tool_ok(tools_ran, MEMORIZE_TOOL):
            continue
        if _TOOL_WORK.search(line) and _tool_ok(tools_ran, REGISTER_TOOL):  # CARD-612: the tool was registered
            continue
        if line.strip():
            keep.append(line)
    return "\n".join(keep)


def memory_not_done_lines(not_done: str) -> list:
    """The "Not done" lines that ask to remember something (a memorize_fact call was missing)."""
    return [line for line in str(not_done or "").splitlines() if _memory_kind(line) == "save"]


def memory_retry_prompt(lines: list) -> str:
    asks = "; ".join(line[len(NOT_DONE_PREFIX):].strip().rstrip(".") for line in lines if line.strip())
    return (
        f"(AutoReiv check) This part of my request was not done: {asks}. Call {MEMORIZE_TOOL} now to save it. "
        "Then reply in one short sentence saying what you saved."
    )


def settle_memory_retry(pending_not_done: str, tools_since_retry: list) -> str:
    """After the retry step: the memory lines go away when memorize_fact ran and succeeded; other lines stay."""
    if not _tool_ok(tools_since_retry, MEMORIZE_TOOL):
        return pending_not_done
    return "\n".join(line for line in str(pending_not_done or "").splitlines() if _memory_kind(line) != "save")
