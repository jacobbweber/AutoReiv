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
            tone_str = str(tone_raw).strip().lower()
            if not tone_str:
                tone = AgentTone.DEFAULT
            else:
                try:
                    tone = AgentTone(tone_str)
                except ValueError:
                    tone = tone_str

        # 6. Validate Max Turns Bound
        max_turns = int(payload.get("max_turns", 10))
        if max_turns < 1 or max_turns > 50:
            raise AgentValidationError(
                f"Invalid max_turns '{max_turns}'. Must be between 1 and 50 turns to prevent runaway loops."
            )

        raw_retention = payload.get("history_retention_days", 30)
        if raw_retention is None or str(raw_retention).strip() == "":
            history_retention_days = 30
        else:
            history_retention_days = int(raw_retention)
        if history_retention_days < 0:
            raise AgentValidationError("history_retention_days must be >= 0 (0 means never delete).")

        # 7. Validate Allowed Tools against Catalog (Defensive anti-hallucination check)
        raw_tools = payload.get("allowed_tools") or payload.get("allowed_tool_names") or []
        allowed_tools = [str(t).strip() for t in raw_tools if str(t).strip()]

        if available_tools is not None:
            for tool_name in allowed_tools:
                if tool_name not in available_tools:
                    raise AgentValidationError(f"Tool '{tool_name}' does not exist in the available tool catalog.")

        raw_skills = payload.get("allowed_skill")
        if raw_skills is None:
            raw_skills = payload.get("allowed_skills") or []
        allowed_skill = [str(s).strip() for s in raw_skills if str(s).strip()]

        raw_pack_tools = payload.get("pack_tool_names") or []
        pack_tool_names = [str(t).strip() for t in raw_pack_tools if str(t).strip()]

        if "show_in_chat" not in payload or payload.get("show_in_chat") is None:
            show_in_chat = True
        else:
            show_in_chat = bool(payload.get("show_in_chat"))

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
            allowed_skill=allowed_skill,
            pack_tool_names=pack_tool_names,
            show_in_chat=show_in_chat,
            max_turns=max_turns,
            history_retention_days=history_retention_days,
            is_builtin=is_builtin,
        )
