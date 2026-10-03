"""CARD-616: a job step whose final reply asks Jacob something in plain text waits for his answer.

Only a reply whose last line ends with "?" is checked, with one short yes/no call on the same model
(CARD-613 rejected a bare "?" rule: "Anything else?" after finished work is still done). Any failure
of the check keeps the old behaviour (the step is done).
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Optional

from src.application.kernel.reply_limits import helper_call_seconds
from src.domain.gateway.models import ChatMessage, CompletionRequest, Role

logger = logging.getLogger(__name__)

QUESTION_CHECK_PROMPT = (
    "You read the last reply of an assistant that was working on a task step. Answer with one word: yes or no.\n"
    "yes: the assistant stopped and needs the user's answer before the task can continue or be finished "
    "(it asks for a choice, a missing detail, or permission to go ahead).\n"
    "no: the work is done and the closing question is only an offer or a courtesy "
    "(for example 'Anything else?' or 'Want me to expand it?' after the result was delivered)."
)
_TRAILING = " \t*_`)\"'\u201d"


def ends_with_question(reply: str) -> bool:
    """True when the last non-empty line of the reply ends with a question mark."""
    for line in reversed((reply or "").splitlines()):
        line = line.strip().rstrip(_TRAILING)
        if line:
            return line.endswith("?")
    return False


async def reply_needs_answer(gateway: Any, model: Optional[str], reply: str, task: str = "") -> bool:
    """One no-tools yes/no call: does this reply need the user's answer before the work can go on?"""
    if gateway is None or not ends_with_question(reply):
        return False
    user = (f"Task: {task.strip()[:600]}\n\n" if task and task.strip() else "") + f"Reply:\n{reply.strip()[-2000:]}"
    try:
        req = CompletionRequest(
            model=model or getattr(gateway, "default_model_id", None) or "default",
            messages=[ChatMessage(role=Role.SYSTEM, content=QUESTION_CHECK_PROMPT), ChatMessage(role=Role.USER, content=user)],
            temperature=0.0,
            max_tokens=600,  # a reasoning model spends some on thinking
            think=False,
            background=True,
        )
        resp = await asyncio.wait_for(gateway.complete(req), timeout=helper_call_seconds())
        text = getattr(resp, "text", None) or ""
    except Exception as exc:  # noqa: BLE001 - the check is advisory; the step stays done
        logger.info("CARD-616 question check skipped: %s", exc)
        return False
    text = re.sub(r"<think>.*?(</think>|$)", "", str(text), flags=re.S | re.I).strip().lower()
    m = re.search(r"\b(yes|no)\b", text)
    return bool(m and m.group(1) == "yes")
