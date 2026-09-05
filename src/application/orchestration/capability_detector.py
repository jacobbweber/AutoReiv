"""
Capability Gap Detection [REQ-FACT-024, REQ-FACT-027].
Identifies turn-time missing tools or capability deficiencies from agent responses.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field


class CapabilityGapDetection(BaseModel):
    """Structured detection of a missing tool or capability gap."""
    detected: bool = True
    missing_capability: str = Field(..., description="Description of the missing capability")
    suggested_tool_name: str = Field(..., description="Suggested identifier for the synthesized tool")
    user_prompt: str = Field(default="", description="Original user prompt that triggered the gap")
    context_summary: str = Field(default="", description="Relevant context or error summary")


class CapabilityDetector:
    """
    Analyzes user prompts and assistant responses to detect turn-time capability gaps.
    """

    PATTERNS = [
        re.compile(r"(?:don't|do not|cannot|can't|unable to|lack(?:s)?)\s+(?:have|find|access|possess)?\s*(?:the\s+)?(?:tools?|capability|capabilities|ability|command|permission)\s+(?:to|for)?\s*(.+?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"I don't have (?:a|any|the)?\s*tools?\s*(?:to|for)?\s*(.+?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"I cannot directly (?:create|manage|execute|run|provision|delete|modify)\s+(.+?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"no tool available to (.+?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"unable to (.+?) without a tool", re.IGNORECASE),
        re.compile(r"without a tool to (.+?)(?:\.|$)", re.IGNORECASE),
    ]

    GREETINGS = {"hi", "hello", "hey", "thanks", "thank you", "good morning", "good evening"}

    @classmethod
    def detect(cls, user_prompt: Optional[str], assistant_response: Optional[str]) -> Optional[CapabilityGapDetection]:
        if not user_prompt or not assistant_response:
            return None

        prompt_clean = user_prompt.strip()
        if prompt_clean.lower() in cls.GREETINGS or len(prompt_clean) < 4:
            return None

        for pat in cls.PATTERNS:
            match = pat.search(assistant_response)
            if match:
                extracted = match.group(1).strip().strip(".")
                if not extracted or len(extracted) < 2:
                    extracted = prompt_clean

                # Generate clean suggested tool name
                suggested_tool = cls._suggest_tool_name(extracted, prompt_clean)

                return CapabilityGapDetection(
                    detected=True,
                    missing_capability=extracted,
                    suggested_tool_name=suggested_tool,
                    user_prompt=prompt_clean,
                    context_summary=assistant_response.strip(),
                )

        return None

    @classmethod
    def _suggest_tool_name(cls, capability_text: str, fallback_prompt: str) -> str:
        text = capability_text if len(capability_text) > 3 else fallback_prompt
        # Strip common articles and adverbs
        text = re.sub(r"\b(a|an|the|directly|to|for|in|on|with)\b", "", text, flags=re.IGNORECASE)
        # Convert non-alphanumeric to underscores
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
        parts = [p for p in slug.split("_") if p][:4]
        if not parts:
            return "manage_resource"

        name = "_".join(parts)
        if not name.startswith(("manage_", "create_", "get_", "run_", "delete_")):
            name = f"manage_{name}"
        if name[0].isdigit():
            name = f"tool_{name}"
        return name
