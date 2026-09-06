"""LLM phase-context helper for Agent Training Factory."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

from src.domain.gateway.models import ChatMessage, CompletionRequest, Role

logger = logging.getLogger(__name__)


async def phase_llm_json(
    gateway: Any,
    *,
    system: str,
    user: str,
    temperature: float = 0.3,
    max_tokens: int = 1200,
    timeout: float = 45.0,
    fallback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Call gateway with phase-specific context; parse JSON object from reply."""
    if gateway is None:
        return dict(fallback or {})

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
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
    except Exception as exc:
        logger.warning("Agent Training Factory LLM call failed: %s", exc)

    return dict(fallback or {})


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
    """Call gateway and return raw text (with fallback)."""
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
        logger.warning("Agent Training Factory LLM text call failed: %s", exc)
        return fallback
