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
    "You decide if a task step must wait for the user. Answer with one word: yes or no.\n"
    "yes = the reply cannot finish the task without the user's answer (a missing detail, a choice, or permission).\n"
    "no = the task's result is already in the reply; a closing question that only offers more help does not count."
)
# Worked examples: without them a no-thinking model reads every closing offer as a question (live, nemotron).
QUESTION_CHECK_EXAMPLES = (
    ("Task: Draft a packing list for my trip.\n\nReply:\nWhere are you travelling, and for how many days?", "yes"),
    ("Task: Summarize the meeting notes.\n\nReply:\nSummary: budget approved, launch moved to May.\n\n"
     "Would you like me to turn this into an email?", "no"),
    ("Task: Rename the report file.\n\nReply:\nI can rename it to 'Q3 report' or 'Report Q3'. Which name do you prefer?", "yes"),
    ("Task: Explain how compost works.\n\nReply:\nCompost is organic matter broken down by microbes...\n\n"
     "Anything else I can help with?", "no"),
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
    messages = [ChatMessage(role=Role.SYSTEM, content=QUESTION_CHECK_PROMPT)]
    for example, answer in QUESTION_CHECK_EXAMPLES:
        messages += [ChatMessage(role=Role.USER, content=example), ChatMessage(role=Role.ASSISTANT, content=answer)]
    messages.append(ChatMessage(role=Role.USER, content=user))
    try:
        req = CompletionRequest(
            model=model or getattr(gateway, "default_model_id", None) or "default",
            messages=messages,
            temperature=0.0,
            max_tokens=600,  # a reasoning model spends some on thinking
            think=False,  # Ollama think=false; vLLM chat_template_kwargs.enable_thinking=false (a reasoning model overthinks)
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
