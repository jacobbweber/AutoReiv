"""Unit tests for CARD-337: Granular Token & Timing Telemetry Attribution [REQ-TEL-002, REQ-TEL-003]."""

from src.application.kernel.telemetry_attribution import (
    TimingBreakdown,
    TokenBreakdown,
    calculate_timing_attribution,
    calculate_token_attribution,
    estimate_tokens,
)
from src.domain.gateway.models import ChatMessage, Role, ToolDefinition


def test_estimate_tokens_fast_approximation():
    """[REQ-TEL-002] estimate_tokens approximates 1 token per ~4 chars with a floor of 1."""
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello") == 1
    assert estimate_tokens("a" * 40) == 10


def test_calculate_token_attribution_discrete_slices():
    """[REQ-TEL-002] Attribution isolates user, persona, tools, skills, memory, history, and completion."""
    user_prompt = "What is the capital of France?"
    persona = "You are a helpful geography assistant."
    tools = [
        ToolDefinition(
            name="get_weather",
            description="Get weather for a city",
            parameters={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        )
    ]
    skills = ["# Skill: Geography\nUse standard ISO names."]
    memory = ["User prefers metric units."]
    history = [
        ChatMessage(role=Role.USER, content="Hello"),
        ChatMessage(role=Role.ASSISTANT, content="Hi! How can I help you today?"),
    ]
    tool_results = ["Paris weather: 22C, sunny"]
    completion = "The capital of France is Paris."
    reasoning = "Thinking: Capital is Paris."

    breakdown = calculate_token_attribution(
        user_prompt=user_prompt,
        agent_persona=persona,
        tool_definitions=tools,
        progressive_skills=skills,
        episodic_memory=memory,
        compacted_history=history,
        tool_results_injected=tool_results,
        completion=completion,
        reasoning=reasoning,
    )

    assert isinstance(breakdown, TokenBreakdown)
    assert breakdown.user_prompt > 0
    assert breakdown.agent_persona > 0
    assert breakdown.tool_schemas > 0
    assert breakdown.progressive_skills > 0
    assert breakdown.episodic_memory > 0
    assert breakdown.compacted_history > 0
    assert breakdown.tool_results_injected > 0
    assert breakdown.completion > 0
    assert breakdown.reasoning > 0

    # Verification of totals
    expected_prompt = (
        breakdown.user_prompt
        + breakdown.agent_persona
        + breakdown.tool_schemas
        + breakdown.progressive_skills
        + breakdown.episodic_memory
        + breakdown.compacted_history
        + breakdown.tool_results_injected
    )
    assert breakdown.total_prompt_tokens == expected_prompt
    assert breakdown.scaffold_tokens == expected_prompt - breakdown.user_prompt
    assert breakdown.scaffold_ratio > 1.0


def test_direct_agent_token_attribution_has_zero_tools_and_skills():
    """[REQ-TEL-002] Direct agent turns have 0 tool schema tokens and 0 skill tokens."""
    breakdown = calculate_token_attribution(
        user_prompt="Say hi",
        agent_persona="You are a direct, concise assistant.",
        tool_definitions=None,
        progressive_skills=None,
        episodic_memory=None,
        compacted_history=None,
        completion="Hi!",
    )

    assert breakdown.tool_schemas == 0
    assert breakdown.progressive_skills == 0
    assert breakdown.episodic_memory == 0
    assert breakdown.tool_results_injected == 0
    assert breakdown.scaffold_tokens == breakdown.agent_persona
    assert breakdown.user_prompt > 0
    assert breakdown.completion > 0


def test_calculate_timing_attribution():
    """[REQ-TEL-003] Timing attribution calculates prep, TTFT, generation, and tokens/sec."""
    timing = calculate_timing_attribution(
        harness_prep_ms=12.5,
        ttft_ms=1500.0,
        total_round_trip_ms=5500.0,
        completion_tokens=40,
        inter_step_latency_ms=80.0,
    )

    assert isinstance(timing, TimingBreakdown)
    assert timing.harness_prep_ms == 12.5
    assert timing.ttft_ms == 1500.0
    assert timing.generation_ms == 4000.0  # 5500 - 1500
    assert timing.inter_step_latency_ms == 80.0
    assert timing.tokens_per_second == 10.0  # 40 tokens / 4.0s
    assert timing.total_round_trip_ms == 5500.0
