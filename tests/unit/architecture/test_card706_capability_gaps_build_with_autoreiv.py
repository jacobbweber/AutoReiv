"""CARD-706 guard: Capability gap rows render Build with AutoReiv and route to AutoReiv in Chat."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.tools.developer_mediation import build_packet, format_developer_prompt

pytestmark = pytest.mark.guard

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_capability_gap_row_renders_build_with_autoreiv_and_drops_skill_studio_and_ask_developer():
    tools_js = (REPO_ROOT / "src/web/static/modules/studios/forge/tools.js").read_text(encoding="utf-8")
    fn_start = tools_js.index("export function capabilityGapRowHtml")
    fn_end = tools_js.index("export function openGapInSkillStudio")
    fn_body = tools_js[fn_start:fn_end]

    assert "Build with AutoReiv" in fn_body
    assert "btn-gap-build-autoreiv" in fn_body
    assert "Open in Skill Studio" not in fn_body
    assert "btn-gap-open-skill-studio" not in fn_body
    assert ">Ask Developer<" not in fn_body


def test_developer_prompt_includes_capability_authoring_skill_guidance():
    packet = build_packet(
        "create",
        {
            "tool_name": "fetch_rss_headlines",
            "behavior": "Fetch RSS headlines for a feed URL.\n\nMissing capability: rss_reader\n\nRequested from a capability gap for autoreiv.",
            "target_agent_id": "autoreiv",
        },
    )
    prompt = format_developer_prompt(packet)
    assert 'skill_view(skill_id="capability-authoring")' in prompt
    assert "register_native_tool" in prompt


def test_open_developer_session_resolves_retired_agents_to_autoreiv():
    chat_js = (REPO_ROOT / "src/web/static/modules/studios/chat.js").read_text(encoding="utf-8")
    fn_start = chat_js.index("async function openDeveloperSession")
    fn_end = chat_js.index("async function resumeParkedJob")
    fn_body = chat_js[fn_start:fn_end]
    dev_intent_js = (REPO_ROOT / "src/web/static/modules/studios/chat/developer_intent.js").read_text(encoding="utf-8")

    assert "resolveAuthoringChatAgentId(" in fn_body
    assert "state.agents" in fn_body
    assert "export function resolveAuthoringChatAgentId" in dev_intent_js
    assert "return 'autoreiv';" in dev_intent_js
