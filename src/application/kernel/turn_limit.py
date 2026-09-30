"""CARD-461: a reply that runs out of steps ends with a short summary, not a bare error."""

from __future__ import annotations

TURN_LIMIT_REASON = "turn_limit"

TURN_LIMIT_INSTRUCTION = (
    "You have reached the step limit for this reply. Do not call any tools. In a few short lines, say what you "
    "finished, what is still left, and that the user can say \"keep going\" to continue."
)


def turn_limit_footer(max_turns: int) -> str:
    return f'(Stopped at the {max_turns}-step limit for one reply. Say "keep going" to continue.)'


def turn_limit_fallback(max_turns: int) -> str:
    return (
        f"I hit the limit of {max_turns} steps for one reply before finishing. "
        "Say \"keep going\" and I'll pick up where I left off."
    )


def turn_limit_reply(summary: str, max_turns: int) -> str:
    """Summary + footer, or the fixed fallback when the final no-tools call gave nothing."""
    summary = (summary or "").strip()
    if not summary:
        return turn_limit_fallback(max_turns)
    return f"{summary}\n\n{turn_limit_footer(max_turns)}"
