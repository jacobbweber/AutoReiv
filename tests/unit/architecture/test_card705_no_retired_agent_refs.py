"""CARD-705 guard: retire stale Developer/Toolsmith/Architect references and remove Chat header role pill."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.kernel.reply_rules import ASK_DEVELOPER_LINE, ask_developer_ending, is_toolsmith
from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.content import store as content_store
from src.infrastructure.content.store import REPO_PLATFORM, ContentStore, join_frontmatter
from tests.unit.agent_skills.catalog import platform_pack_profile

pytestmark = pytest.mark.guard

ROOT = Path(__file__).resolve().parents[3]


def test_chat_header_has_no_active_agent_tone_pill():
    """#activeAgentTone ('Autonomous Multi-Agent Orchestrator' / 'Engine: AutoReiv') is removed from Chat header."""
    index_html = (ROOT / "src" / "web" / "templates" / "index.html").read_text(encoding="utf-8")
    chat_js = (ROOT / "src" / "web" / "static" / "modules" / "studios" / "chat.js").read_text(encoding="utf-8")

    assert 'id="activeAgentTone"' not in index_html
    assert "Engine: AutoReiv" not in index_html
    assert "activeAgentTone" not in chat_js
    assert "Autonomous Multi-Agent Orchestrator" not in chat_js


def test_autoreiv_is_recognized_as_capability_author_and_never_gets_ask_developer_line():
    """AutoReiv owns capability-authoring (CARD-693) and must never append or keep 'You can use Ask Developer to add this.'"""
    autoreiv = platform_pack_profile("autoreiv")
    assert is_toolsmith(autoreiv) is True

    hist = [
        ChatMessage(role=Role.USER, content="check health"),
        ChatMessage(role=Role.TOOL, content="Tool Error: Tool 'cli_exec' not found in system registry.", name="cli_exec"),
    ]
    out = ask_developer_ending(
        "Health check completed with warnings.",
        hist,
        gap_text="run shell commands",
        own_tools=(),
        offer=not is_toolsmith(autoreiv),
    )
    assert ASK_DEVELOPER_LINE not in out
    assert "Ask Developer" not in out

    stripped = ask_developer_ending(
        "Health check completed. You can use Ask Developer to add this.",
        [ChatMessage(role=Role.USER, content="check health")],
        gap_text=None,
        own_tools=(),
        offer=not is_toolsmith(autoreiv),
    )
    assert "Ask Developer" not in stripped
    assert stripped == "Health check completed."


def test_stale_pre_card693_user_autoreiv_copy_and_retired_agent_copies_are_reconciled(tmp_path: Path):
    """A pre-CARD-693 user copy of autoreiv.md (e.g. Ava) upgrades its skills and stale Developer/Toolsmith prompt."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    stale_meta = {
        "name": "Ava",
        "description": "Personal assistant",
        "tone": "warm",
        "purpose": "general",
        "avatar": "bot",
        "show_in_chat": True,
        "max_turns": 25,
        "based_on": "0000000000000000",
        "skills": [
            "wiki",
            "wiki-knowledge",
            "memory-context",
            "platform-health",
            "agent-authoring",
        ],
    }
    stale_body = (
        "You are Ava (AutoReiv). For code changes or new tools, route to Developer/Toolsmith agents "
        "or tell the user to open Developer in Chat."
    )
    (agents_dir / "autoreiv.md").write_text(join_frontmatter(stale_meta, stale_body), encoding="utf-8")

    # Leftover user copy of a retired shipped agent (with based_on set)
    retired_dev_meta = {
        "name": "Developer",
        "based_on": "1111111111111111",
        "skills": ["implement-change"],
    }
    (agents_dir / "developer.md").write_text(join_frontmatter(retired_dev_meta, "Old developer copy."), encoding="utf-8")

    content_store.configure(tmp_path)
    try:
        store = ContentStore(data_root=tmp_path)
        loaded = store.agents.load("autoreiv")
        assert loaded is not None
        assert loaded.meta["name"] == "Ava"
        for required_skill in ("capability-authoring", "project-cards", "software-development", "user:*"):
            assert required_skill in loaded.skills, f"Missing consolidated skill {required_skill} in {loaded.skills}"
        assert "agent-authoring" not in loaded.skills
        assert "Developer/Toolsmith" not in loaded.body
        assert "open Developer in Chat" not in loaded.body

        listed_ids = [a.id for a in store.agents.list()]
        assert "developer" not in listed_ids
        assert store.agents.load("developer") is None

        reg = BuiltinAgentRegistry(profiles=[], state_store=None)
        reg._content = store
        resolved_dev = reg.get_agent("developer")
        assert resolved_dev is not None
        assert "capability-authoring" in (resolved_dev.allowed_skill or [])
    finally:
        content_store.reset_store()


def test_platform_health_skill_does_not_route_to_developer_in_chat():
    """platform/skills/platform-health/SKILL.md must not instruct directing the operator to Developer in Chat."""
    skill_md = (REPO_PLATFORM / "skills" / "platform-health" / "SKILL.md").read_text(encoding="utf-8")
    assert "Developer in Chat" not in skill_md
