"""
Deterministic Guardrails & Invariant Validation for Agent Profiles [REQ-SKIL-003].
"""

import re
from typing import Any, Dict, Optional, Set

from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.settings.models import ModelPurpose


class AgentValidationError(ValueError):
    """Raised when an agent specification violates platform invariants."""

    pass


class AgentProfileGuardrail:
    """
    Deterministic validator enforcing platform invariants on agent specifications.
    """

    SLUG_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")

    @classmethod
    def validate(
        cls,
        payload: Dict[str, Any],
        available_tools: Optional[Set[str]] = None,
    ) -> AgentProfile:
        """
        Validate and normalize an incoming agent specification against platform invariants.
        """
        # 1. Validate ID Slug
        agent_id = str(payload.get("id", "")).strip()
        if not agent_id:
            raise AgentValidationError("Agent 'id' cannot be empty.")
        if not cls.SLUG_PATTERN.match(agent_id):
            raise AgentValidationError(
                f"Agent id '{agent_id}' does not match valid kebab-case slug format (lowercase letters, numbers, hyphens only; no spaces or leading/trailing hyphens)."
            )

        # 2. Validate Name & Description
        name = str(payload.get("name", "")).strip()
        if len(name) < 2:
            raise AgentValidationError("Agent 'name' must be at least 2 characters long.")

        description = str(payload.get("description", "")).strip()

        # 3. Validate System Prompt
        system_prompt = str(payload.get("system_prompt", "")).strip()
        if len(system_prompt) < 10:
            raise AgentValidationError(
                "Agent 'system_prompt' must be at least 10 characters long with clear operating instructions."
            )

        # 4. Validate Model Purpose
        purpose_raw = payload.get("purpose", "general")
        if isinstance(purpose_raw, ModelPurpose):
            purpose = purpose_raw
        else:
            try:
                purpose = ModelPurpose(str(purpose_raw).lower())
            except ValueError:
                valid_purposes = [p.value for p in ModelPurpose]
                raise AgentValidationError(f"Invalid purpose '{purpose_raw}'. Must be one of: {valid_purposes}")

        # 5. Validate Agent Tone
        tone_raw = payload.get("tone", "default")
        if isinstance(tone_raw, AgentTone):
            tone = tone_raw
        else:
            try:
                tone = AgentTone(str(tone_raw).lower())
            except ValueError:
                valid_tones = [t.value for t in AgentTone]
                raise AgentValidationError(f"Invalid tone '{tone_raw}'. Must be one of: {valid_tones}")

        # 6. Validate Max Turns Bound
        max_turns = int(payload.get("max_turns", 10))
        if max_turns < 1 or max_turns > 50:
            raise AgentValidationError(
                f"Invalid max_turns '{max_turns}'. Must be between 1 and 50 turns to prevent runaway loops."
            )

        # 7. Validate Allowed Tools against Catalog (Defensive anti-hallucination check)
        raw_tools = payload.get("allowed_tools") or payload.get("allowed_tool_names") or []
        allowed_tools = [str(t).strip() for t in raw_tools if str(t).strip()]

        if available_tools is not None:
            for tool_name in allowed_tools:
                if tool_name not in available_tools:
                    raise AgentValidationError(f"Tool '{tool_name}' does not exist in the available tool catalog.")

        # 8. Avatar Icon & Model Override
        avatar_icon = str(payload.get("avatar_icon", "bot")).strip() or "bot"
        model_override = str(payload.get("model", "default")).strip() or "default"
        is_builtin = bool(payload.get("is_builtin", False))

        return AgentProfile(
            id=agent_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            purpose=purpose,
            tone=tone,
            avatar_icon=avatar_icon,
            model=model_override,
            allowed_tool_names=allowed_tools,
            max_turns=max_turns,
            is_builtin=is_builtin,
        )
