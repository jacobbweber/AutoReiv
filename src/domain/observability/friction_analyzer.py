"""
Telemetry Friction Analyzer [CARD-354 / REQ-OBS-010].
Diagnoses cognitive and procedural friction from session message histories and spans.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.domain.gateway.models import ChatMessage, Role
from src.domain.observability.models import FrictionIncident, FrictionSignatureType


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TelemetryFrictionAnalyzer:
    """
    Pure domain analyzer that identifies behavioral friction patterns in agent execution traces.
    """

    MUTATING_VERBS = ("create", "update", "write", "patch", "delete", "save", "modify")
    READING_VERBS = ("read", "list", "get", "inspect")

    def __init__(
        self,
        store: Any = None,
        payload_bloat_threshold_bytes: int = 8192,
        search_thrash_threshold: int = 3,
    ) -> None:
        self.store = store
        self.payload_bloat_threshold_bytes = payload_bloat_threshold_bytes
        self.search_thrash_threshold = search_thrash_threshold

    def is_mutating_tool(self, tool_name: str) -> bool:
        norm = (tool_name or "").lower()
        return any(verb in norm for verb in self.MUTATING_VERBS)

    def is_reading_tool(self, tool_name: str) -> bool:
        norm = (tool_name or "").lower()
        return any(verb in norm for verb in self.READING_VERBS)

    def is_search_tool(self, tool_name: str) -> bool:
        norm = (tool_name or "").lower()
        return "search" in norm or "find" in norm or "lookup" in norm

    def are_same_domain_tools(self, tool1: str, tool2: str) -> bool:
        """Heuristic check if two tools operate on the same entity or domain."""
        t1, t2 = tool1.lower(), tool2.lower()
        # Common domain patterns: wiki_template_*, wiki_note_*, repo_file_*, task_*
        for prefix in ("wiki_template", "wiki_note", "repo_file", "note", "task", "tag"):
            if prefix in t1 and prefix in t2:
                return True
        # Split tokens
        parts1 = set(t1.replace("-", "_").split("_"))
        parts2 = set(t2.replace("-", "_").split("_"))
        common = parts1.intersection(parts2)
        # Exclude generic verbs
        common_nouns = common - {"create", "update", "write", "patch", "read", "list", "get", "delete", "file", "note"}
        return len(common_nouns) > 0 or (len(common) >= 2)

    def analyze_messages(
        self,
        session_id: str,
        agent_id: str,
        messages: List[ChatMessage],
    ) -> List[FrictionIncident]:
        """
        Analyze a sequence of messages in a session for friction signatures.
        """
        incidents: List[FrictionIncident] = []
        if not messages:
            return incidents

        # Track tool calls and their outputs
        last_successful_mutation: Optional[Dict[str, Any]] = None
        consecutive_searches: List[Dict[str, Any]] = []

        for idx, msg in enumerate(messages):
            # Check Payload Bloat on tool outputs
            if msg.role == Role.TOOL:
                content_bytes = len((msg.content or "").encode("utf-8"))
                if content_bytes > self.payload_bloat_threshold_bytes:
                    sev = "high" if content_bytes > (self.payload_bloat_threshold_bytes * 2) else "medium"
                    incidents.append(
                        FrictionIncident(
                            id=f"fric_{uuid.uuid4().hex[:12]}",
                            session_id=session_id,
                            turn_index=idx,
                            agent_id=agent_id,
                            tool_name=msg.name or "unknown_tool",
                            signature=FrictionSignatureType.PAYLOAD_BLOAT,
                            evidence=(
                                f"Tool '{msg.name}' returned payload of {content_bytes} bytes, "
                                f"which exceeds the {self.payload_bloat_threshold_bytes} bytes threshold."
                            ),
                            payload_bytes=content_bytes,
                            severity=sev,
                            occurred_at=_utc_now(),
                        )
                    )

                # Check if the tool output was a successful mutation
                if msg.name and self.is_mutating_tool(msg.name):
                    # Check for success in content
                    is_success = True
                    if msg.content:
                        try:
                            parsed = json.loads(msg.content)
                            if isinstance(parsed, dict) and parsed.get("success") is False:
                                is_success = False
                            elif isinstance(parsed, dict) and "error" in parsed and parsed["error"]:
                                is_success = False
                        except Exception:
                            if "error" in msg.content.lower() or "exception" in msg.content.lower():
                                is_success = False
                    if is_success:
                        last_successful_mutation = {
                            "tool_name": msg.name,
                            "index": idx,
                            "content": msg.content,
                        }
                    else:
                        last_successful_mutation = None
                elif msg.name and not self.is_reading_tool(msg.name):
                    # Non-read/non-mutation reset
                    last_successful_mutation = None

            # Check assistant tool calls
            elif msg.role == Role.ASSISTANT and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.name or ""

                    # 1. Signature A: Redundant Verification
                    if last_successful_mutation is not None and self.is_reading_tool(tool_name):
                        prev_tool = last_successful_mutation["tool_name"]
                        if self.are_same_domain_tools(prev_tool, tool_name):
                            incidents.append(
                                FrictionIncident(
                                    id=f"fric_{uuid.uuid4().hex[:12]}",
                                    session_id=session_id,
                                    turn_index=idx,
                                    agent_id=agent_id,
                                    tool_name=tool_name,
                                    signature=FrictionSignatureType.REDUNDANT_VERIFICATION,
                                    evidence=(
                                        f"Redundant verification detected: reading tool '{tool_name}' was executed "
                                        f"immediately after successful mutation '{prev_tool}'."
                                    ),
                                    severity="medium",
                                    occurred_at=_utc_now(),
                                )
                            )
                        # Reset after flagging or checking
                        last_successful_mutation = None
                    elif not self.is_reading_tool(tool_name):
                        last_successful_mutation = None

                    # 2. Signature C: Search Thrashing
                    if self.is_search_tool(tool_name):
                        tc_args = getattr(tc, "arguments", None) or getattr(tc, "args", None) or {}
                        consecutive_searches.append({"tool_name": tool_name, "args": tc_args, "index": idx})
                        if len(consecutive_searches) >= self.search_thrash_threshold:
                            # Flag search thrashing
                            incidents.append(
                                FrictionIncident(
                                    id=f"fric_{uuid.uuid4().hex[:12]}",
                                    session_id=session_id,
                                    turn_index=idx,
                                    agent_id=agent_id,
                                    tool_name=tool_name,
                                    signature=FrictionSignatureType.SEARCH_THRASHING,
                                    evidence=(
                                        f"Search thrashing detected: {len(consecutive_searches)} consecutive search "
                                        f"invocations without reading any returned result."
                                    ),
                                    severity="medium",
                                    occurred_at=_utc_now(),
                                )
                            )
                            # Reset count after flagging to avoid repeated duplicate reports
                            consecutive_searches = []
                    else:
                        # Non-search tool call breaks search streak (e.g. read, execute, etc.)
                        consecutive_searches = []

            elif msg.role == Role.USER:
                # User turn boundary resets state
                last_successful_mutation = None
                consecutive_searches = []

        return incidents

    def scan_recent_sessions(
        self,
        lookback_hours: int = 24,
        limit: int = 50,
    ) -> List[FrictionIncident]:
        """
        Query SQLite store for recent sessions and analyze their messages for friction.
        """
        if not self.store:
            return []

        all_incidents: List[FrictionIncident] = []
        sessions = self.store.list_sessions() if hasattr(self.store, "list_sessions") else []
        cutoff = _utc_now() - timedelta(hours=lookback_hours)

        scanned = 0
        for sess in sessions:
            if scanned >= limit:
                break
            # Check updated_at / created_at
            t = getattr(sess, "updated_at", None) or getattr(sess, "created_at", None)
            if t:
                try:
                    if isinstance(t, str):
                        t_dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                    else:
                        t_dt = t
                    if t_dt.tzinfo is None:
                        t_dt = t_dt.replace(tzinfo=timezone.utc)
                    if t_dt < cutoff:
                        continue
                except Exception:
                    pass

            agent_id = getattr(sess, "agent_id", "autoreiv") or "autoreiv"
            messages = self.store.get_messages(sess.id) if hasattr(self.store, "get_messages") else []
            incidents = self.analyze_messages(session_id=sess.id, agent_id=agent_id, messages=messages)
            all_incidents.extend(incidents)
            scanned += 1

        return all_incidents
