"""Token-verified context compaction helpers [CARD-699].

Adapted from Agent-OS (`agent_os/compaction.py`):
- Normalizes Unicode look-alike dashes and strips format characters (`normalize_text`).
- Extracts required `KeyTokens` (`paths`, `numbers`, `names`) from user messages and
  earlier compaction summaries while ignoring assistant prose and tool outputs.
- Builds and validates structured 3-section summaries (`Decisions`, `Open tasks`, `Key facts`)
  via `build_verified_summary` and `check_summary`.
- Tracks per-session compaction backoff when summary verification fails twice in a row.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from src.domain.gateway.models import ChatMessage, Role

SUMMARY_MARKER = "[Summary of earlier conversation:"
HEADINGS = ("Decisions", "Open tasks", "Key facts")
LONG_TOOL_LINE = 400
DEFAULT_BACKOFF_TURNS = 2

_DASH_TO_HYPHEN = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2212": "-",
    }
)

_CLOCK = (
    r"\d{4}-\d{2}-\d{2}[T ]\d{1,2}:\d{2}(?::\d{2})?"
    r"|\d{4}[-/]\d{2}[-/]\d{2}"
    r"|\d{1,2}:\d{2}(?::\d{2})?"
)
_UNIT_RE = re.compile(_CLOCK + r"|[A-Za-z0-9_./-]+")
_CLOCK_RE = re.compile(_CLOCK)
_NUMBER_RE = re.compile(r"\d{2,}(?:\.\d+)?|\d+\.\d+")
_TRAILING_PUNCTUATION = ".,;:)!?\"']}>"
_SNAKE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_FILE_RE = re.compile(r"[A-Za-z][\w-]*\.[A-Za-z0-9]{2,8}")

_DECISION_HINT_RE = re.compile(
    r"\b(?:decid\w*|keep|chose|chosen|use|using|set|agreed|policy|must|always|never)\b",
    re.IGNORECASE,
)
_TASK_HINT_RE = re.compile(
    r"\b(?:todo|open|next|please|need\s+to|should|update|deploy|configure|fix|build|verify|check|monitor)\b",
    re.IGNORECASE,
)

# session_id -> remaining non-forced turns to wait before retrying compaction
_SESSION_BACKOFF: dict[str, int] = {}


@dataclass(frozen=True)
class KeyTokens:
    paths: tuple[str, ...]
    numbers: tuple[str, ...]
    names: tuple[str, ...]


def normalize_text(text: str) -> str:
    """Fold look-alike Unicode dashes to '-' and strip format characters (Cf)."""
    folded = unicodedata.normalize("NFKC", text or "").translate(_DASH_TO_HYPHEN)
    return "".join(ch for ch in folded if unicodedata.category(ch) != "Cf")


def _units(text: str) -> list[str]:
    units: list[str] = []
    for token in _UNIT_RE.findall(normalize_text(text)):
        cleaned = token.rstrip(_TRAILING_PUNCTUATION)
        if cleaned:
            units.append(cleaned)
    return units


def _is_path(token: str) -> bool:
    if "/" not in token or token.startswith(("http:", "https:")):
        return False
    if token.startswith(("/", "./", "../")):
        return True
    last = token.rstrip("/").split("/")[-1]
    return "." in last


def _is_number(token: str) -> bool:
    if _CLOCK_RE.fullmatch(token) is not None:
        return True
    return _NUMBER_RE.fullmatch(token) is not None


def _is_name(token: str) -> bool:
    if len(token) < 4:
        return False
    if "_" in token and _SNAKE_RE.fullmatch(token) is not None:
        return True
    return _FILE_RE.fullmatch(token) is not None


def extract_key_tokens(text: str) -> KeyTokens:
    """Extract file paths, numbers/dates/times, and snake_case/file identifiers in order."""
    paths: list[str] = []
    numbers: list[str] = []
    names: list[str] = []
    seen_paths: set[str] = set()
    seen_numbers: set[str] = set()
    seen_names: set[str] = set()
    for token in _units(text):
        if _is_path(token):
            if token not in seen_paths:
                seen_paths.add(token)
                paths.append(token)
            continue
        if _is_number(token):
            if token not in seen_numbers:
                seen_numbers.add(token)
                numbers.append(token)
            continue
        if _is_name(token) and token not in seen_names:
            seen_names.add(token)
            names.append(token)
    return KeyTokens(paths=tuple(paths), numbers=tuple(numbers), names=tuple(names))


def is_summary_message(message: ChatMessage, summary_marker: str = SUMMARY_MARKER) -> bool:
    return bool((message.content or "").lstrip().startswith(summary_marker))


def render_original_messages(messages: Sequence[ChatMessage]) -> str:
    """Render a sequence of ChatMessages into plain transcript lines for size and token checks."""
    lines: list[str] = []
    for msg in messages:
        content = normalize_text(msg.content or "")
        if is_summary_message(msg):
            lines.append(f"summary: {content}")
        elif msg.role == Role.TOOL:
            lines.append(f"tool {msg.name or ''}: {content}".rstrip())
        else:
            lines.append(f"{msg.role.value}: {content}")
    return "\n".join(lines)


def required_fact_text(
    original: Sequence[ChatMessage] | str,
    summary_marker: str = SUMMARY_MARKER,
) -> str:
    """Return text whose paths, numbers, and names the summary must preserve.

    User messages and earlier compaction summaries count. Tool outputs and normal assistant
    replies do not contribute required tokens.
    """
    if isinstance(original, str):
        kept: list[str] = []
        skipping = False
        for line in normalize_text(original).splitlines():
            if line.startswith("tool ") and len(line) > LONG_TOOL_LINE:
                skipping = True
                continue
            if line.startswith(("assistant:", "tool ")):
                skipping = True
                continue
            if line.startswith(("user:", "summary:", "Earlier summary:", "Newer messages:")):
                skipping = False
            if not skipping:
                kept.append(line)
        return "\n".join(kept)

    parts: list[str] = []
    for msg in original:
        if msg.role == Role.USER or is_summary_message(msg, summary_marker):
            text = normalize_text(msg.content or "")
            if text:
                parts.append(text)
    return "\n".join(parts)


def _has_heading(summary: str, heading: str) -> bool:
    for line in summary.splitlines():
        cleaned = line.strip().lstrip("#*-").strip().rstrip(":").strip()
        if cleaned == heading:
            return True
    return False


def _names_still_required(names: Sequence[str], present: set[str]) -> list[str]:
    missing = [name for name in names if name not in present]
    if len(names) <= 4:
        return missing
    allowed_missing = len(names) // 5
    if len(missing) <= allowed_missing:
        return []
    return missing


def check_summary(
    summary: str,
    original: Sequence[ChatMessage] | str,
    *,
    require_shorter: bool = True,
) -> list[str]:
    """Return verification problems for `summary` against `original` (empty list = passed)."""
    problems: list[str] = []
    original_text = original if isinstance(original, str) else render_original_messages(original)
    if require_shorter and original_text and len(summary) >= len(original_text):
        problems.append("The summary is not shorter than the original messages.")
    for heading in HEADINGS:
        if not _has_heading(summary, heading):
            problems.append(f"The summary is missing the {heading} section.")
    tokens = extract_key_tokens(required_fact_text(original))
    present = set(_units(summary))
    missing_paths = [item for item in tokens.paths if item not in present]
    missing_numbers = [item for item in tokens.numbers if item not in present]
    missing_names = _names_still_required(tokens.names, present)
    if missing_paths:
        problems.append("The summary is missing file paths: " + ", ".join(missing_paths))
    if missing_numbers:
        problems.append("The summary is missing numbers: " + ", ".join(missing_numbers))
    if missing_names:
        problems.append("The summary is missing names: " + ", ".join(missing_names))
    return problems


def build_verified_summary(
    messages: Sequence[ChatMessage],
    summary_lines_limit: int = 10,
    summary_marker: str = SUMMARY_MARKER,
) -> str:
    """Build a deterministic 3-section summary that preserves all required user tokens."""
    fact_src = required_fact_text(messages, summary_marker=summary_marker)
    tokens = extract_key_tokens(fact_src)

    decisions: list[str] = []
    open_tasks: list[str] = []
    preview_lines: list[str] = []

    for msg in messages:
        raw = normalize_text(msg.content or "").replace("\n", " ").strip()
        if not raw:
            continue
        snippet = raw[:120] + ("..." if len(raw) > 120 else "")
        if msg.role == Role.USER:
            if _DECISION_HINT_RE.search(raw) and len(decisions) < 3:
                decisions.append(f"- {snippet}")
            if _TASK_HINT_RE.search(raw) and len(open_tasks) < 3:
                open_tasks.append(f"- {snippet}")
        role_label = msg.role.value.capitalize()
        preview_lines.append(f"- {role_label}: {snippet}")

    if not decisions:
        decisions.append("- none")
    if not open_tasks:
        open_tasks.append("- none")

    key_fact_lines: list[str] = []
    if tokens.paths:
        key_fact_lines.append("- Paths: " + ", ".join(tokens.paths))
    if tokens.numbers:
        key_fact_lines.append("- Numbers/dates: " + ", ".join(tokens.numbers))
    if tokens.names:
        key_fact_lines.append("- Identifiers: " + ", ".join(tokens.names))

    limit = max(1, summary_lines_limit)
    kept_previews = preview_lines[-limit:]
    omitted = max(0, len(preview_lines) - len(kept_previews))
    if omitted:
        key_fact_lines.append(f"... ({omitted} older messages omitted)")
    key_fact_lines.extend(kept_previews)

    return (
        f"{summary_marker}\n"
        "Decisions\n"
        + "\n".join(decisions)
        + "\nOpen tasks\n"
        + "\n".join(open_tasks)
        + "\nKey facts\n"
        + "\n".join(key_fact_lines)
        + "]"
    )


def set_compaction_backoff(session_id: str | None, turns: int = DEFAULT_BACKOFF_TURNS) -> None:
    if not session_id:
        return
    _SESSION_BACKOFF[session_id] = max(0, int(turns))


def consume_compaction_backoff(session_id: str | None) -> int:
    """Return remaining backoff turns (>0 means skip non-forced compaction on this turn)."""
    if not session_id:
        return 0
    remaining = _SESSION_BACKOFF.get(session_id, 0)
    if remaining <= 0:
        return 0
    _SESSION_BACKOFF[session_id] = remaining - 1
    return remaining


def reset_compaction_backoff(session_id: str | None = None) -> None:
    if session_id is None:
        _SESSION_BACKOFF.clear()
    else:
        _SESSION_BACKOFF.pop(session_id, None)


def serialize_session_messages(
    store: object,
    session_id: str,
    *,
    include_archived: bool = False,
) -> list[dict[str, object]]:
    """Serialize session messages with optional archived rows and archive_links metadata [CARD-699]."""
    from src.application.kernel.empty_reply import skip_empty_assistant_rows

    get_msgs = getattr(store, "get_messages")
    try:
        raw_msgs = get_msgs(session_id=session_id, include_archived=include_archived)
    except TypeError:
        raw_msgs = get_msgs(session_id=session_id)
    msgs = skip_empty_assistant_rows(raw_msgs)

    link_map: dict[str, str] = {}
    if include_archived and hasattr(store, "get_archive_links"):
        for link in store.get_archive_links(session_id):
            link_map[str(link["message_id"])] = str(link["summary_id"])

    out: list[dict[str, object]] = []
    for m in msgs:
        mid = getattr(m, "id", None)
        row: dict[str, object] = {
            "id": mid,
            "role": m.role.value,
            "content": m.content,
            "name": m.name,
            "tool_calls": [tc.model_dump() for tc in m.tool_calls] if m.tool_calls else None,
            "tool_call_id": m.tool_call_id,
            "reasoning": getattr(m, "reasoning", None),
        }
        if include_archived:
            summary_id = link_map.get(str(mid or ""))
            row["archived"] = summary_id is not None
            row["archived_by_summary_id"] = summary_id
        out.append(row)
    return out


def build_session_context_payload(
    store: object,
    registry: object | None,
    tool_reg: object | None,
    session_id: str,
) -> dict[str, object] | None:
    """Build the `/api/sessions/{session_id}/context` payload [CARD-161, CARD-699]."""
    from src.application.kernel.context_compactor import ContextCompactor, resolve_agent_context_limit

    sess = getattr(store, "get_session")(session_id)
    if not sess:
        return None

    agent = getattr(registry, "get_agent")(sess.agent_id) if registry else None
    msgs = getattr(store, "get_messages")(session_id=session_id)

    system_prompt = agent.system_prompt if agent else ""
    system_msg = ChatMessage(role=Role.SYSTEM, content=system_prompt)
    all_msgs = [system_msg] + list(msgs)
    used_tokens = ContextCompactor.estimate_tokens(all_msgs)

    model_name = agent.model if agent and agent.model else "default"
    max_tokens = resolve_agent_context_limit(agent, state_store=store)
    percent_used = round(min(100.0, (used_tokens / max(1, max_tokens)) * 100.0), 1)

    tool_list = []
    if tool_reg and agent:
        raw_tools = getattr(tool_reg, "get_tools_for_agent")(agent)
        for t in raw_tools:
            tool_list.append({"name": t.name, "description": t.description or ""})
    tool_list.sort(key=lambda x: x["name"])

    archive_links = getattr(store, "get_archive_links")(session_id) if hasattr(store, "get_archive_links") else []

    return {
        "session_id": session_id,
        "agent_id": sess.agent_id,
        "agent_name": agent.name if agent else sess.agent_id,
        "model": model_name,
        "used_tokens": used_tokens,
        "max_tokens": max_tokens,
        "percent_used": percent_used,
        "message_count": len(msgs),
        "archive_links_count": len(archive_links),
        "archive_links": archive_links,
        "tools_count": len(tool_list),
        "tools": tool_list,
    }


def run_session_compaction(
    store: object,
    registry: object | None,
    session_id: str,
) -> dict[str, object] | None:
    """Execute manual session compaction with token verification and archive_links [CARD-161, CARD-699]."""
    from src.application.kernel.context_compactor import ContextCompactor, resolve_agent_context_limit

    sess = getattr(store, "get_session")(session_id)
    if not sess:
        return None

    agent = getattr(registry, "get_agent")(sess.agent_id) if registry else None
    msgs = list(getattr(store, "get_messages")(session_id=session_id))

    if not msgs:
        return {
            "session_id": session_id,
            "success": True,
            "compaction_applied": False,
            "turns_compacted": 0,
            "archive_links_count": 0,
            "archive_links": [],
            "message": "No messages to compact.",
            "used_tokens": 0,
            "max_tokens": 8192,
            "percent_used": 0.0,
            "message_count": 0,
        }

    model_name = agent.model if agent and agent.model else "default"
    max_tokens = resolve_agent_context_limit(agent, state_store=store)

    system_prompt = agent.system_prompt if agent else ""
    system_msg = ChatMessage(role=Role.SYSTEM, content=system_prompt)
    msgs_with_system = [system_msg] + msgs

    compacted_with_system, metrics = ContextCompactor.compact_with_stats(
        msgs_with_system,
        model_name=model_name,
        keep_last_n_turns=2,
        preserve_root_intent=True,
        force=True,
        session_id=session_id,
    )

    if metrics.compaction_applied and len(compacted_with_system) > 1:
        compacted_msgs = [m for m in compacted_with_system if m.role != Role.SYSTEM]
        getattr(store, "replace_session_messages")(session_id, sess.agent_id, compacted_msgs)
        current_msgs = list(getattr(store, "get_messages")(session_id=session_id))
    else:
        current_msgs = msgs

    all_current = [system_msg] + current_msgs
    used_tokens = ContextCompactor.estimate_tokens(all_current)
    percent_used = round(min(100.0, (used_tokens / max(1, max_tokens)) * 100.0), 1)
    archive_links = getattr(store, "get_archive_links")(session_id) if hasattr(store, "get_archive_links") else []

    return {
        "success": True,
        "compaction_applied": metrics.compaction_applied,
        "turns_compacted": metrics.turns_compacted,
        "tools_truncated": metrics.tools_truncated,
        "original_tokens": metrics.original_tokens,
        "compacted_tokens": metrics.compacted_tokens,
        "used_tokens": used_tokens,
        "max_tokens": max_tokens,
        "percent_used": percent_used,
        "message_count": len(current_msgs),
        "archive_links_count": len(archive_links),
        "archive_links": archive_links,
    }
