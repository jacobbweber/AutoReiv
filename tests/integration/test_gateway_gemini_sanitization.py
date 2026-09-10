"""
Tests for CARD-213: Google Gemini Provider Compatibility and Tool Message Sanitization.
Verifies that:
1. Orphan or unlinked tool messages are converted to user context notes to comply with OpenAI/Gemini strict function calling rules.
2. Formatted messages never start with a 'tool' role.
3. Presets for Gemini recommend active, responsive models (gemini-3.6-flash, etc.).
"""

from src.application.settings.presets import get_preset_by_id
from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter


def test_gemini_tool_message_sanitization_converts_orphan_tools():
    """Unlinked tool messages must be converted to user context notes instead of raw 'tool' role."""
    adapter = OpenAIProviderAdapter(provider_id="gemini", base_url="https://generativelanguage.googleapis.com/v1beta/openai")

    # Sequence where an assistant calls tool 'call_1', but we have an extra orphan tool 'call_orphan'
    # followed by another orphan tool with no tool_call_id
    messages = [
        ChatMessage(role=Role.USER, content="Run the test"),
        ChatMessage(
            role=Role.ASSISTANT,
            content="Running...",
            tool_calls=[ToolCall(id="call_1", name="search", arguments={"q": "test"})],
        ),
        ChatMessage(role=Role.TOOL, name="search", tool_call_id="call_1", content="Result 1"),
        # Orphan tool 1: Not in preceding assistant call
        ChatMessage(role=Role.TOOL, name="wiki_note_create", tool_call_id="call_orphan_999", content="Created note"),
        # Orphan tool 2: No tool_call_id at all (e.g. approval park)
        ChatMessage(role=Role.TOOL, name="handoff_to_agent", content='{"status": "approval_required"}'),
        ChatMessage(role=Role.USER, content="What is the result?"),
    ]

    formatted = adapter._format_messages(messages)

    # 1. First tool call was valid and paired
    assert formatted[1]["role"] == "assistant"
    assert formatted[2]["role"] == "tool"
    assert formatted[2]["tool_call_id"] == "call_1"
    assert formatted[2]["name"] == "search"

    # 2. Orphan tool 1 must be converted to user context note
    assert formatted[3]["role"] == "user"
    assert "[Tool Output: wiki_note_create]" in formatted[3]["content"]

    # 3. Orphan tool 2 must also be converted to user context note
    assert formatted[4]["role"] == "user"
    assert "[Tool Output: handoff_to_agent]" in formatted[4]["content"]

    # 4. Final user message is intact
    assert formatted[5]["role"] == "user"
    assert formatted[5]["content"] == "What is the result?"


def test_gemini_tool_message_sanitization_leading_tool_message():
    """If a conversation history starts with a tool message, it must not be formatted as role 'tool'."""
    adapter = OpenAIProviderAdapter(provider_id="gemini", base_url="https://generativelanguage.googleapis.com/v1beta/openai")

    messages = [
        ChatMessage(role=Role.TOOL, name="init_tool", tool_call_id="call_init", content="Init result"),
        ChatMessage(role=Role.USER, content="Hello"),
    ]

    formatted = adapter._format_messages(messages)
    assert formatted[0]["role"] != "tool"
    assert formatted[0]["role"] == "user"


def test_gemini_preset_recommended_models():
    """Presets for Google Gemini must recommend active, responsive models."""
    preset = get_preset_by_id("gemini")
    assert preset is not None
    recommended = preset.get("recommended_models", [])
    assert "gemini-3.6-flash" in recommended
    assert "gemini-3.7-flash" in recommended
    assert "gemini-3.5-flash" not in recommended
    assert "gemini-3.8-flash" not in recommended
