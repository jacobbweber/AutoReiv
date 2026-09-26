"""One-shot LLM text call for Skill Studio runbook drafts [CARD-497 D5].

Moved from the retired Factory's ``llm.py``; only the plain-text helper survived.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.domain.gateway.models import ChatMessage, CompletionRequest, Role

logger = logging.getLogger(__name__)


async def phase_llm_text(
    gateway: Any,
    *,
    system: str,
    user: str,
    temperature: float = 0.4,
    max_tokens: int = 2000,
    timeout: float = 60.0,
    fallback: str = "",
) -> str:
    """Call the gateway once and return its text, or ``fallback`` on no gateway, error or empty reply."""
    if gateway is None:
        return fallback
    try:
        model = getattr(gateway, "default_model_id", None) or "default"
        req = CompletionRequest(
            model=model,
            messages=[
                ChatMessage(role=Role.SYSTEM, content=system),
                ChatMessage(role=Role.USER, content=user),
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        resp = await asyncio.wait_for(gateway.complete(req), timeout=timeout)
        text = (getattr(resp, "text", None) or "").strip()
        return text or fallback
    except Exception as exc:
        logger.warning("Skill Studio LLM text call failed: %s", exc)
        return fallback
