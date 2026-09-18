"""
Unit tests for Telemetry Friction Analyzer [CARD-354 / REQ-OBS-010].
"""

import json
from typing import List

from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.domain.observability.friction_analyzer import TelemetryFrictionAnalyzer
from src.domain.observability.models import FrictionSignatureType


def _make_msg(role: Role, content: str = "", tool_calls: List[ToolCall] = None, name: str = None, tool_call_id: str = None) -> ChatMessage:
    return ChatMessage(
        role=role,
        content=content,
        tool_calls=tool_calls,
        name=name,
        tool_call_id=tool_call_id,
    )


def test_detect_redundant_verification():
    """Mutating tool followed immediately by a redundant read/list tool should be flagged."""
    analyzer = TelemetryFrictionAnalyzer()

    messages = [
        _make_msg(Role.USER, "Create a template for weekly notes."),
        _make_msg(
            Role.ASSISTANT,
            content="Creating template...",
            tool_calls=[ToolCall(id="tc_1", name="wiki_template_create", arguments={"title": "Weekly Note", "content": "# Weekly"})],
        ),
        _make_msg(Role.TOOL, content=json.dumps({"success": True, "id": "tpl_weekly", "title": "Weekly Note"}), name="wiki_template_create", tool_call_id="tc_1"),
        _make_msg(
            Role.ASSISTANT,
            content="Verifying template list...",
            tool_calls=[ToolCall(id="tc_2", name="list_wiki_templates", arguments={})],
        ),
        _make_msg(Role.TOOL, content=json.dumps([{"id": "tpl_weekly", "title": "Weekly Note"}]), name="list_wiki_templates", tool_call_id="tc_2"),
        _make_msg(Role.ASSISTANT, "Template created and confirmed."),
    ]

    incidents = analyzer.analyze_messages(session_id="sess_123", agent_id="autoreiv", messages=messages)

    assert len(incidents) >= 1
    rv = [inc for inc in incidents if inc.signature == FrictionSignatureType.REDUNDANT_VERIFICATION]
    assert len(rv) == 1
    assert rv[0].tool_name in ("list_wiki_templates", "wiki_template_create")
    assert "wiki_template_create" in rv[0].evidence
    assert rv[0].session_id == "sess_123"
    assert rv[0].agent_id == "autoreiv"


def test_detect_payload_bloat():
    """Tool outputs exceeding the payload threshold (>8 KB) should be flagged."""
    analyzer = TelemetryFrictionAnalyzer(payload_bloat_threshold_bytes=8192)

    bloated_data = "x" * 12000
    messages = [
        _make_msg(Role.USER, "Read the large log file."),
        _make_msg(
            Role.ASSISTANT,
            content="Reading log...",
            tool_calls=[ToolCall(id="tc_1", name="repo_file_read", arguments={"path": "large.log"})],
        ),
        _make_msg(Role.TOOL, content=bloated_data, name="repo_file_read", tool_call_id="tc_1"),
        _make_msg(Role.ASSISTANT, "I have read the logs."),
    ]

    incidents = analyzer.analyze_messages(session_id="sess_456", agent_id="autoreiv", messages=messages)

    bloat = [inc for inc in incidents if inc.signature == FrictionSignatureType.PAYLOAD_BLOAT]
    assert len(bloat) == 1
    assert bloat[0].tool_name == "repo_file_read"
    assert bloat[0].payload_bytes >= 12000
    assert "exceeds" in bloat[0].evidence.lower()


def test_detect_search_thrashing():
    """3 or more consecutive search tool calls in a turn without reading results should flag thrashing."""
    analyzer = TelemetryFrictionAnalyzer(search_thrash_threshold=3)

    messages = [
        _make_msg(Role.USER, "Find notes about authentication."),
        _make_msg(
            Role.ASSISTANT,
            content="Searching for auth notes...",
            tool_calls=[ToolCall(id="tc_1", name="wiki_note_search", arguments={"query": "auth"})],
        ),
        _make_msg(Role.TOOL, content=json.dumps([]), name="wiki_note_search", tool_call_id="tc_1"),
        _make_msg(
            Role.ASSISTANT,
            content="No results, searching with different keyword...",
            tool_calls=[ToolCall(id="tc_2", name="wiki_note_search", arguments={"query": "authentication"})],
        ),
        _make_msg(Role.TOOL, content=json.dumps([]), name="wiki_note_search", tool_call_id="tc_2"),
        _make_msg(
            Role.ASSISTANT,
            content="Still nothing, trying login...",
            tool_calls=[ToolCall(id="tc_3", name="wiki_note_search", arguments={"query": "login"})],
        ),
        _make_msg(Role.TOOL, content=json.dumps([]), name="wiki_note_search", tool_call_id="tc_3"),
        _make_msg(Role.ASSISTANT, "Could not find any auth notes."),
    ]

    incidents = analyzer.analyze_messages(session_id="sess_789", agent_id="autoreiv", messages=messages)

    thrash = [inc for inc in incidents if inc.signature == FrictionSignatureType.SEARCH_THRASHING]
    assert len(thrash) == 1
    assert thrash[0].tool_name == "wiki_note_search"
    assert "consecutive search" in thrash[0].evidence.lower()


def test_clean_session_no_friction():
    """Standard productive interaction should produce zero friction incidents."""
    analyzer = TelemetryFrictionAnalyzer()

    messages = [
        _make_msg(Role.USER, "Find and read the database guide."),
        _make_msg(
            Role.ASSISTANT,
            content="Searching...",
            tool_calls=[ToolCall(id="tc_1", name="wiki_note_search", arguments={"query": "database"})],
        ),
        _make_msg(Role.TOOL, content=json.dumps([{"path": "notes/db.md", "title": "Database Guide"}]), name="wiki_note_search", tool_call_id="tc_1"),
        _make_msg(
            Role.ASSISTANT,
            content="Reading note...",
            tool_calls=[ToolCall(id="tc_2", name="wiki_note_read", arguments={"path": "notes/db.md"})],
        ),
        _make_msg(Role.TOOL, content="# Database Guide\nPostgres is used.", name="wiki_note_read", tool_call_id="tc_2"),
        _make_msg(Role.ASSISTANT, "The database guide states Postgres is used."),
    ]

    incidents = analyzer.analyze_messages(session_id="sess_clean", agent_id="autoreiv", messages=messages)
    assert len(incidents) == 0
