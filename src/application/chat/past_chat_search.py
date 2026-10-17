"""Provenance-badged search_past_chats across hot and cold sessions [CARD-702].

Adapted from Crucible (ADR-0009) and Agent-OS (`agent_os/search.py`, `agent_os/recipes.py`):
- Searches across active (hot) and compacted/archived (`archive_links` + optional cold SQLite DB) chat messages.
- Excludes the current active session/turn and prior `search_past_chats` tool outputs so the model never matches
  its own in-flight question or previous search reports.
- Tags every hit with an explicit provenance badge (`[Recent]` vs `[Archived]`), local-timezone date, session title/id,
  and role label, ranking user/tool messages before assistant replies and `[Recent]` before `[Archived]`.
- Enforces a per-turn search budget (`MAX_SEARCHES_PER_TURN = 2`) and appends the deterministic `answer_now`
  stop directive so the model answers immediately from what it found.
"""

from __future__ import annotations

import re
import sqlite3
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_SEARCHES_PER_TURN = 2
DEFAULT_MAX_RESULTS = 8
DEFAULT_MAX_CHARS = 2400
PAST_CHATS_TOOL_NAME = "search_past_chats"
NOTHING_MATCHED = "Nothing matched."

_DASHES = re.compile(r"[\u2010-\u2015\u2212]")
_TOKEN = re.compile(r"[^\W_]+")
_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
_MISSING_MOMENT = datetime(1, 1, 1, tzinfo=timezone.utc)

FILLER_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "of",
        "to",
        "for",
        "in",
        "on",
        "at",
        "by",
        "with",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "we",
        "they",
        "he",
        "she",
        "me",
        "my",
        "our",
        "your",
        "what",
        "where",
        "when",
        "who",
        "why",
        "how",
        "did",
        "do",
        "does",
        "about",
        "into",
        "than",
        "then",
        "so",
        "not",
        "no",
        "yes",
        "just",
        "please",
        "decide",
        "decided",
        "discuss",
        "discussed",
        "talk",
        "talked",
        "said",
        "earlier",
        "past",
        "chat",
        "chats",
        "session",
        "sessions",
        "conversation",
        "conversations",
    }
)


@dataclass(frozen=True)
class PastChatHit:
    message_id: str
    session_id: str
    session_title: str
    agent_id: str
    store: str  # "recent" | "archived"
    badge: str  # "[Recent]" | "[Archived]"
    created_at: str
    date_label: str
    role_label: str
    excerpt: str
    matched: int
    sequence_num: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "session_title": self.session_title,
            "agent_id": self.agent_id,
            "store": self.store,
            "badge": self.badge,
            "created_at": self.created_at,
            "date_label": self.date_label,
            "role_label": self.role_label,
            "excerpt": self.excerpt,
            "matched": self.matched,
        }


def searchable_text(text: str) -> str:
    """Fold Unicode dashes to ASCII '-' and lowercase for consistent matching."""
    return _DASHES.sub("-", str(text or "")).lower()


def search_tokens(text: str) -> list[str]:
    """Extract unique lowercase word tokens in order (splitting on hyphens and punctuation)."""
    seen: set[str] = set()
    tokens: list[str] = []
    for token in _TOKEN.findall(searchable_text(text)):
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def content_tokens(text: str) -> list[str]:
    """Search words with filler words removed. Empty when nothing identifiable remains."""
    raw = search_tokens(text)
    filtered = [t for t in raw if t not in FILLER_WORDS]
    return filtered


def answer_now(count: int) -> str:
    """Tell the model to stop searching and answer from what this turn already has."""
    unit = "time" if count == 1 else "times"
    return f"searched {count} {unit}. Answer now from what you have, or say nothing was found."


def _resolve_zone(zone_name: str | None = None):
    if zone_name:
        try:
            return ZoneInfo(zone_name)
        except ZoneInfoNotFoundError:
            return timezone.utc
    local_tz = datetime.now().astimezone().tzinfo
    return local_tz or timezone.utc


def _parse_moment(stamp: Any) -> datetime:
    raw = str(stamp or "").strip()
    if not raw:
        return _MISSING_MOMENT
    normalized = raw.replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(normalized)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
            try:
                moment = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
        else:
            return _MISSING_MOMENT
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def format_chat_date(stamp: Any, zone_name: str | None = None) -> str:
    """Calendar date of the message in the configured/local time zone, e.g. 'Oct 17, 2026 (2026-10-17)'."""
    moment = _parse_moment(stamp)
    if moment == _MISSING_MOMENT:
        return str(stamp or "unknown date")
    local = moment.astimezone(_resolve_zone(zone_name))
    human = f"{_MONTHS[local.month - 1]} {local.day}, {local.year}"
    iso = local.strftime("%Y-%m-%d")
    return f"{human} ({iso})"


def clip_excerpt(text: str, needle: str, limit: int = 320) -> str:
    """A short piece of the message around the first match, capped at `limit` chars."""
    compact = " ".join(str(text or "").split())
    if limit <= 0 or not compact:
        return ""
    if len(compact) <= limit:
        return compact
    folded = searchable_text(compact)
    at = folded.find(needle) if needle else 0
    if at < 0 or len(folded) != len(compact):
        at = 0
    else:
        at = max(0, at - 40)
    prefix = "..." if at > 0 else ""
    end = min(len(compact), at + limit)
    suffix = "..." if end < len(compact) else ""
    while len(prefix) + (end - at) + len(suffix) > limit and end > at:
        end -= 1
        suffix = "..." if end < len(compact) else ""
    result = prefix + compact[at:end] + suffix
    return result[:limit]


def format_report(hits: Sequence[PastChatHit], total: int) -> str:
    """Format provenance-badged search report for the model."""
    lines = [f"matches: {total}"]
    if not hits:
        lines.append(NOTHING_MATCHED)
        return "\n".join(lines)
    for hit in hits:
        excerpt = hit.excerpt.replace(" | ", " / ")
        sess_info = f"{hit.session_title} ({hit.session_id})" if hit.session_title else hit.session_id
        lines.append(f"{hit.badge} | {hit.date_label} | session: {sess_info} | {hit.role_label} | {excerpt}")
    return "\n".join(lines)


def _searches_this_turn(store: Any, current_session_id: str | None) -> int:
    if not current_session_id or store is None or not hasattr(store, "get_messages"):
        return 0
    try:
        messages = store.get_messages(current_session_id, include_archived=False)
    except Exception:
        return 0
    count = 0
    for msg in reversed(messages):
        role_val = getattr(msg.role, "value", str(msg.role)).lower()
        if role_val == "user":
            break
        if role_val == "tool" and getattr(msg, "name", None) == PAST_CHATS_TOOL_NAME:
            count += 1
    return count


def _fetch_store_rows(store: Any, *, cold: bool = False) -> list[dict[str, Any]]:
    if store is None or not hasattr(store, "_get_connection"):
        return []
    conn = store._get_connection()
    try:
        if hasattr(store, "_ensure_archive_links_table"):
            store._ensure_archive_links_table(conn)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                m.id AS message_id,
                m.session_id AS session_id,
                m.agent_id AS agent_id,
                m.role AS role,
                m.content AS content,
                m.name AS tool_name,
                m.sequence_num AS sequence_num,
                COALESCE(m.created_at, s.updated_at, s.created_at, '') AS created_at,
                COALESCE(s.title, '') AS session_title,
                a.summary_id AS archived_summary_id
            FROM messages m
            LEFT JOIN sessions s ON s.id = m.session_id
            LEFT JOIN archive_links a ON a.message_id = m.id
            ORDER BY m.created_at DESC, m.sequence_num DESC
            """
        )
        rows = cur.fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            is_archived = cold or bool(r["archived_summary_id"])
            out.append(
                {
                    "message_id": str(r["message_id"] or ""),
                    "session_id": str(r["session_id"] or ""),
                    "agent_id": str(r["agent_id"] or ""),
                    "role": str(r["role"] or "").lower(),
                    "content": str(r["content"] or ""),
                    "tool_name": str(r["tool_name"] or ""),
                    "sequence_num": int(r["sequence_num"] or 0),
                    "created_at": str(r["created_at"] or ""),
                    "session_title": str(r["session_title"] or ""),
                    "is_archived": is_archived,
                }
            )
        return out
    except Exception:
        return []
    finally:
        if getattr(store, "_mem_conn", None) is None:
            conn.close()


def _fetch_cold_sqlite_rows(cold_path: Path) -> list[dict[str, Any]]:
    if not cold_path.is_file():
        return []
    conn = sqlite3.connect(str(cold_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                m.id AS message_id,
                m.session_id AS session_id,
                m.agent_id AS agent_id,
                m.role AS role,
                m.content AS content,
                m.name AS tool_name,
                m.sequence_num AS sequence_num,
                COALESCE(m.created_at, '') AS created_at,
                '' AS session_title
            FROM messages m
            ORDER BY m.sequence_num DESC
            """
        )
        return [
            {
                "message_id": str(r["message_id"] or ""),
                "session_id": str(r["session_id"] or ""),
                "agent_id": str(r["agent_id"] or ""),
                "role": str(r["role"] or "").lower(),
                "content": str(r["content"] or ""),
                "tool_name": str(r["tool_name"] or ""),
                "sequence_num": int(r["sequence_num"] or 0),
                "created_at": str(r["created_at"] or ""),
                "session_title": str(r["session_title"] or ""),
                "is_archived": True,
            }
            for r in cur.fetchall()
        ]
    except Exception:
        return []
    finally:
        conn.close()


def _rank_hit(hit: PastChatHit) -> tuple[int, int, int, float, int]:
    """Rank by: more matched tokens, user/tool messages before assistant replies, recent before archived, newest first."""
    original = hit.role_label == "user" or hit.role_label.startswith("tool ")
    return (
        -hit.matched,
        0 if original else 1,
        0 if hit.store == "recent" else 1,
        -_parse_moment(hit.created_at).timestamp(),
        -hit.sequence_num,
    )


def _match_rows(
    rows: Sequence[dict[str, Any]],
    tokens: Sequence[str],
    *,
    current_session_id: str | None,
    agent_id: str | None,
    zone_name: str | None,
    require_all: bool,
) -> list[PastChatHit]:
    hits: list[PastChatHit] = []
    for row in rows:
        if current_session_id and row["session_id"] == current_session_id:
            continue
        if agent_id and row["agent_id"] and row["agent_id"] != agent_id:
            continue
        if row["role"] == "tool" and row["tool_name"] == PAST_CHATS_TOOL_NAME:
            continue
        content = row["content"]
        if not content.strip():
            continue
        msg_tokens = set(search_tokens(content))
        folded = searchable_text(content)
        matched = sum(1 for tok in tokens if tok in msg_tokens or tok in folded)
        if require_all and matched < len(tokens):
            continue
        if not require_all and matched == 0:
            continue

        is_arch = bool(row["is_archived"]) or content.lstrip().startswith("[Compacted Summary]")
        store_kind = "archived" if is_arch else "recent"
        badge = "[Archived]" if is_arch else "[Recent]"
        role_label = f"tool {row['tool_name']}" if row["role"] == "tool" and row["tool_name"] else row["role"]
        hits.append(
            PastChatHit(
                message_id=row["message_id"],
                session_id=row["session_id"],
                session_title=row["session_title"],
                agent_id=row["agent_id"],
                store=store_kind,
                badge=badge,
                created_at=row["created_at"],
                date_label=format_chat_date(row["created_at"], zone_name),
                role_label=role_label,
                excerpt=content,
                matched=matched,
                sequence_num=row["sequence_num"],
            )
        )
    return hits


def _cap_hits(
    found: Sequence[PastChatHit],
    needle: str,
    *,
    max_results: int,
    max_chars: int,
) -> list[PastChatHit]:
    remaining = max_chars
    chosen: list[PastChatHit] = []
    for hit in found[:max_results]:
        if remaining <= 0:
            break
        per_hit_limit = min(360, remaining)
        excerpt = clip_excerpt(hit.excerpt, needle, per_hit_limit)
        if not excerpt:
            break
        remaining -= len(excerpt)
        chosen.append(
            PastChatHit(
                message_id=hit.message_id,
                session_id=hit.session_id,
                session_title=hit.session_title,
                agent_id=hit.agent_id,
                store=hit.store,
                badge=hit.badge,
                created_at=hit.created_at,
                date_label=hit.date_label,
                role_label=hit.role_label,
                excerpt=excerpt,
                matched=hit.matched,
                sequence_num=hit.sequence_num,
            )
        )
    return chosen


def search_past_chats(
    store: Any,
    query: str,
    *,
    current_session_id: str | None = None,
    agent_id: str | None = None,
    max_results: int = DEFAULT_MAX_RESULTS,
    max_chars: int = DEFAULT_MAX_CHARS,
    max_searches_per_turn: int = MAX_SEARCHES_PER_TURN,
    zone_name: str | None = None,
    cold_db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Search across active (`[Recent]`) and compacted/cold (`[Archived]`) chat sessions with per-turn cap."""
    clean_query = str(query or "").strip()
    if not clean_query:
        return {
            "success": False,
            "query": "",
            "match_count": 0,
            "hits": [],
            "capped": False,
            "answer_now": True,
            "searches_this_turn": 0,
            "report": "The query must be one or more words.",
        }

    already = _searches_this_turn(store, current_session_id)
    if already >= max_searches_per_turn:
        stop_msg = answer_now(already)
        return {
            "success": True,
            "query": clean_query,
            "match_count": 0,
            "hits": [],
            "capped": True,
            "answer_now": True,
            "searches_this_turn": already,
            "report": stop_msg,
        }

    started = time.perf_counter()
    tokens = content_tokens(clean_query)
    if not tokens:
        count = already + 1
        report = f"{format_report([], 0)}\n{answer_now(count)}"
        return {
            "success": True,
            "query": clean_query,
            "match_count": 0,
            "hits": [],
            "capped": count >= max_searches_per_turn,
            "answer_now": True,
            "searches_this_turn": count,
            "search_ms": round((time.perf_counter() - started) * 1000, 3),
            "report": report,
        }

    rows = _fetch_store_rows(store, cold=False)
    if cold_db_path is not None:
        rows.extend(_fetch_cold_sqlite_rows(Path(cold_db_path)))

    found = _match_rows(
        rows,
        tokens,
        current_session_id=current_session_id,
        agent_id=agent_id,
        zone_name=zone_name,
        require_all=True,
    )
    if not found:
        found = _match_rows(
            rows,
            tokens,
            current_session_id=current_session_id,
            agent_id=agent_id,
            zone_name=zone_name,
            require_all=False,
        )

    found.sort(key=_rank_hit)
    total = len(found)
    capped_hits = _cap_hits(found, tokens[0], max_results=max_results, max_chars=max_chars)
    count = already + 1
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)

    report = format_report(capped_hits, total)
    should_stop = bool(capped_hits) or count >= max_searches_per_turn
    if should_stop:
        report = f"{report}\n{answer_now(count)}"

    return {
        "success": True,
        "query": clean_query,
        "match_count": total,
        "hits": [h.to_dict() for h in capped_hits],
        "stores": [h.store for h in capped_hits],
        "capped": count >= max_searches_per_turn,
        "answer_now": should_stop,
        "searches_this_turn": count,
        "search_ms": elapsed_ms,
        "report": report,
    }
