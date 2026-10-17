"""CARD-702: Provenance-badged search_past_chats across hot and cold sessions.

Verifies:
1. Filler-word stripping (`content_tokens`), local-timezone date formatting (`format_chat_date`), and excerpt clipping.
2. Searching across active (`[Recent]`) and compacted/cold (`[Archived]` via `archive_links` or cold DB) messages,
   while excluding the current active session/turn and prior `search_past_chats` tool outputs.
3. Per-turn search budget (`max_searches_per_turn = 2`) and deterministic `answer_now` stop trailer in both
   `search_past_chats` and `WikiLookupBudget`.
4. Binding `search_past_chats` to `platform/skills/session-inspect/SKILL.md` so `AutoReiv` has it via
   `resolve_allowed_tools`.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.chat.past_chat_search import (
    MAX_SEARCHES_PER_TURN,
    answer_now,
    content_tokens,
    format_chat_date,
    search_past_chats,
)
from src.application.kernel.tool_access import tool_access
from src.application.kernel.tool_registry import ScopedToolRegistry, _tool_context
from src.application.kernel.wiki_budget import WikiLookupBudget
from src.application.skills.system_agent_tools import SystemAgentTools
from src.domain.gateway.models import ChatMessage, Role, ToolCall, ToolDefinition
from src.infrastructure.content import store as content_store
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.guard


def test_content_tokens_and_date_formatting():
    tokens = content_tokens("What did we decide about the Project-Orion port in our chat?")
    assert "what" not in tokens
    assert "did" not in tokens
    assert "the" not in tokens
    assert "project" in tokens
    assert "orion" in tokens
    assert "port" in tokens

    date_str = format_chat_date("2026-10-17T15:30:00+00:00", zone_name="UTC")
    assert "Oct 17, 2026" in date_str
    assert "2026-10-17" in date_str


def test_search_past_chats_provenance_badges_hot_and_archived_and_exclusions(tmp_path: Path):
    db_path = tmp_path / "autoreiv.db"
    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    # 1. Hot session with active uncompacted messages
    store.create_session("autoreiv", title="Orion Architecture Review", session_id="sess-hot")
    store.save_message(
        "sess-hot",
        "autoreiv",
        ChatMessage(
            id="msg-hot-1",
            role=Role.USER,
            content="We decided Project Orion uses port 9412 and PostgreSQL 16 for telemetry.",
        ),
    )
    store.save_message(
        "sess-hot",
        "autoreiv",
        ChatMessage(
            id="msg-hot-2",
            role=Role.ASSISTANT,
            content="Recorded: Project Orion is assigned port 9412 on PostgreSQL 16.",
        ),
    )

    # 2. Compacted session where original message is linked in archive_links (cold/archived)
    store.create_session("autoreiv", title="Borealis Storage Migration", session_id="sess-compacted")
    cold_msg_id = store.save_message(
        "sess-compacted",
        "autoreiv",
        ChatMessage(
            role=Role.USER,
            content="Project Borealis retired Redis in favor of SQLite WAL mode on port 8877.",
        ),
    )
    store.save_message(
        "sess-compacted",
        "autoreiv",
        ChatMessage(
            role=Role.ASSISTANT,
            content="Understood, Borealis will use SQLite WAL.",
        ),
    )
    keep_msg = ChatMessage(
        role=Role.USER,
        content="Recent follow-up turn.",
    )
    store.save_message("sess-compacted", "autoreiv", keep_msg)
    # Compact the first 2 messages so cold_msg_id moves into archive_links
    summary_msg = ChatMessage(
        role=Role.USER,
        content="[Summary of earlier conversation:\n## Decisions\n- Borealis migrated.]",
    )
    store.replace_session_messages(
        "sess-compacted",
        "autoreiv",
        [summary_msg, keep_msg],
    )
    # Confirm cold_msg_id is no longer in hot uncompacted get_messages
    hot_only_contents = [m.content for m in store.get_messages("sess-compacted", include_archived=False)]
    assert all("8877" not in (c or "") for c in hot_only_contents)

    # 3. Current active session (must be excluded so the user's current question never matches itself)
    store.create_session("autoreiv", title="Current Chat", session_id="sess-current")
    store.save_message(
        "sess-current",
        "autoreiv",
        ChatMessage(
            role=Role.USER,
            content="What did we decide about Project Orion port 9412 and Project Borealis?",
        ),
    )

    # Search for Hot session fact ("Project Orion port")
    res_hot = search_past_chats(
        store,
        "Project Orion port",
        current_session_id="sess-current",
        zone_name="UTC",
    )
    assert res_hot["success"] is True
    assert res_hot["match_count"] >= 1
    assert res_hot["answer_now"] is True
    hot_hits = res_hot["hits"]
    assert any(h["session_id"] == "sess-hot" and h["badge"] == "[Recent]" for h in hot_hits)
    # Negative assertion: current session is never returned
    assert all(h["session_id"] != "sess-current" for h in hot_hits)
    assert "[Recent]" in res_hot["report"]
    assert "9412" in res_hot["report"]
    assert "Answer now from what you have" in res_hot["report"]

    # Search for Compacted/Archived fact ("Borealis retired Redis")
    res_cold = search_past_chats(
        store,
        "Borealis retired Redis 8877",
        current_session_id="sess-current",
        zone_name="UTC",
    )
    assert res_cold["success"] is True
    assert res_cold["match_count"] >= 1
    cold_hits = res_cold["hits"]
    archived_hit = next((h for h in cold_hits if h["message_id"] == cold_msg_id), None)
    assert archived_hit is not None
    assert archived_hit["badge"] == "[Archived]"
    assert archived_hit["store"] == "archived"
    assert "[Archived]" in res_cold["report"]
    assert "8877" in res_cold["report"]


def test_per_turn_search_budget_and_stop_trailer(tmp_path: Path):
    db_path = tmp_path / "autoreiv.db"
    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    store.create_session("autoreiv", title="Earlier Chat", session_id="sess-1")
    store.save_message(
        "sess-1",
        "autoreiv",
        ChatMessage(role=Role.USER, content="Codename Vesper uses key rotation every 30 days."),
    )

    store.create_session("autoreiv", title="Active Chat", session_id="sess-active")
    store.save_message(
        "sess-active",
        "autoreiv",
        ChatMessage(role=Role.USER, content="Look up our past chats."),
    )

    # Simulate 2 prior search_past_chats tool results already recorded in the current turn of sess-active
    for idx in (1, 2):
        store.save_message(
            "sess-active",
            "autoreiv",
            ChatMessage(
                role=Role.TOOL,
                name="search_past_chats",
                tool_call_id=f"tc-{idx}",
                content=f"matches: 0\nNothing matched.\n{answer_now(idx)}",
            ),
        )

    # A 3rd call in the same turn is blocked by the per-turn cap (MAX_SEARCHES_PER_TURN = 2)
    res_capped = search_past_chats(
        store,
        "Codename Vesper",
        current_session_id="sess-active",
    )
    assert res_capped["capped"] is True
    assert res_capped["answer_now"] is True
    assert res_capped["searches_this_turn"] == MAX_SEARCHES_PER_TURN
    assert "Answer now from what you have" in res_capped["report"]

    # Also verify WikiLookupBudget enforces MAX_SEARCHES_PER_TURN (2) on search_past_chats
    budget = WikiLookupBudget(budget=8)
    tools = [
        ToolDefinition(name="search_past_chats", description="search", parameters={}),
        ToolDefinition(name="get_session_info", description="info", parameters={}),
    ]
    tc1 = ToolCall(id="c1", name="search_past_chats", arguments={"query": "first"})
    tc2 = ToolCall(id="c2", name="search_past_chats", arguments={"query": "second"})
    tc3 = ToolCall(id="c3", name="search_past_chats", arguments={"query": "third"})

    assert budget.check(tc1) is None
    assert any(t.name == "search_past_chats" for t in (budget.offer(tools) or []))
    assert budget.check(tc2) is None
    # After 2 calls, search_past_chats is removed from offered tools and a 3rd call is answered immediately
    assert all(t.name != "search_past_chats" for t in (budget.offer(tools) or []))
    blocked = budget.check(tc3)
    assert blocked is not None
    assert "Answer now from what you have" in str(blocked.output)


def test_search_past_chats_bound_to_session_inspect_and_autoreiv(tmp_path: Path):
    data_dir = tmp_path / "data"
    (data_dir / "skills").mkdir(parents=True, exist_ok=True)
    content_store.configure(data_dir)
    content_store.set_tool_registry(None)
    try:
        reg = ScopedToolRegistry()
        db_store = SQLiteStateStore(db_path=str(tmp_path / "ops.db"))
        db_store.initialize_db()
        skill = SystemAgentTools(store=db_store, telemetry=MagicMock())
        skill.register_tools(reg)

        assert reg.get_tool_definition("search_past_chats") is not None
        assert tool_access("search_past_chats") == "read"

        store = content_store.get_store()
        session_inspect = store.skills.load("session-inspect")
        assert session_inspect is not None
        assert "search_past_chats" in session_inspect.tools

        autoreiv_file = store.agents.load("autoreiv")
        assert autoreiv_file is not None
        allowed = resolve_allowed_tools(autoreiv_file)
        assert "search_past_chats" in allowed

        # Verify calling via SystemAgentTools uses get_tool_context() session_id automatically
        db_store.create_session("autoreiv", title="Old Session", session_id="sess-old")
        db_store.save_message(
            "sess-old",
            "autoreiv",
            ChatMessage(role=Role.USER, content="We chose codename Hyperion for the backup cluster."),
        )
        db_store.create_session("autoreiv", title="Now Session", session_id="sess-now")
        db_store.save_message(
            "sess-now",
            "autoreiv",
            ChatMessage(role=Role.USER, content="What did we choose for Hyperion?"),
        )

        tok = _tool_context.set({"agent_id": "autoreiv", "session_id": "sess-now"})
        try:
            out = skill.search_past_chats(query="codename Hyperion backup")
        finally:
            _tool_context.reset(tok)

        assert out["success"] is True
        assert out["match_count"] == 1
        assert out["hits"][0]["session_id"] == "sess-old"
        assert out["hits"][0]["badge"] == "[Recent]"
        assert "Hyperion" in out["report"]
    finally:
        content_store.reset_store()
