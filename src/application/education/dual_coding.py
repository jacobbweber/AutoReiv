"""Grounded dual coding for the course pipeline [CARD-640].

The dual coding step pairs a short explanation with a Mermaid diagram. It is built only from the
learner's own wiki notes on the topic, through one model call, and checked against those notes.
When there are no notes on the topic, no model, a model error, or a reply that is not grounded in
the notes, the step writes nothing and says why. There is no fallback template. The shared source
search, model call and grounding helpers live in `grounded.py` [CARD-646].
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.application.education.grounded import (
    MAX_SOURCES,
    DuplicateCheck,
    ask_again_if_repeated,
    avoid_block,
    avoid_checker,
    call_model,
    find_sources,
    grounded_count,
    has_banned,
    notes_block,
    parse_reply,
    public_sources,
    skip,
    source_vocab,
    stem,
    topic_keywords,
)

SYSTEM_PROMPT = (
    "You turn a learner's own notes into a dual coding study aid. Use ONLY facts stated in the notes. "
    "Do not add outside knowledge and do not write generic study advice. Reply with one JSON object and "
    "nothing else, with these keys: "
    '"prose" (2 to 4 sentences explaining the topic using the notes), '
    '"mermaid" (a Mermaid flowchart starting with "flowchart TD", 4 to 8 boxes whose labels are concrete '
    "terms from the notes), "
    '"steps" (3 to 5 short strings walking through the diagram), '
    '"question" (one question a learner can answer from the notes), '
    '"answer" (the short answer, taken from the notes).'
)


def find_dual_coding_sources(wiki_tools: Any, topic: str, limit: int = MAX_SOURCES) -> List[Dict[str, Any]]:
    """The learner's own wiki notes that are about `topic` (course- and priming-written notes excluded)."""
    return find_sources(wiki_tools, topic, limit)


def _clean_mermaid(text: str) -> str:
    body = re.sub(r"^```(?:mermaid)?\s*|\s*```$", "", str(text or "").strip())
    return body.strip()


_LABEL = re.compile(r"[\[\(\{]+\"?([^\[\]\(\)\{\}\"]+)\"?[\]\)\}]+")


def validate_dual_coding(payload: Dict[str, Any], sources: List[Dict[str, Any]], topic: str) -> Optional[str]:
    """Return why `payload` is not grounded in `sources`, or None when it is."""
    prose = str(payload.get("prose") or "").strip()
    mermaid = _clean_mermaid(payload.get("mermaid") or "")
    question = str(payload.get("question") or "").strip()
    answer = str(payload.get("answer") or "").strip()
    if has_banned([prose, mermaid, question, answer]):
        return "generic template text"
    if len(prose) < 40 or not question or not answer:
        return "missing explanation, question or answer"
    first = mermaid.splitlines()[0].strip().lower() if mermaid else ""
    if not (first.startswith("flowchart") or first.startswith("graph")):
        return "diagram is not a Mermaid flowchart"
    labels = [lab.strip() for lab in _LABEL.findall(mermaid) if lab.strip()]
    if len(labels) < 3:
        return "diagram has fewer than three boxes"
    vocab = source_vocab(sources)
    topic_stems = {stem(w) for w in topic_keywords(topic)}
    grounded_labels = sum(1 for lab in labels if grounded_count(lab, vocab, topic_stems) >= 1)
    if grounded_labels * 2 < len(labels):
        return "diagram boxes are not taken from the notes"
    if grounded_count(prose, vocab, topic_stems) < 3:
        return "explanation is not taken from the notes"
    if grounded_count(answer, vocab, topic_stems) < 1:
        return "answer is not taken from the notes"
    return None


async def compose_dual_coding(
    gateway: Any,
    wiki_tools: Any,
    topic: str,
    *,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
    avoid_questions: Optional[List[str]] = None,
    duplicate_of: Optional[DuplicateCheck] = None,
    asked: Optional[List[Tuple[str, str]]] = None,
) -> Dict[str, Any]:
    """Build grounded dual coding content for `topic`, or a skip with its reason (never a template)."""
    topic = (topic or "").strip()
    sources = find_dual_coding_sources(wiki_tools, topic)
    if not sources:
        return skip(topic, "no_wiki_notes")
    if gateway is None:
        return skip(topic, "model_unavailable", sources, "no model gateway")

    avoid = avoid_block(avoid_questions)  # CARD-650: don't ask what the ledger already asks
    user = (
        f"Topic: {topic}\n\nThe learner's notes:\n\n{notes_block(sources)}\n\n"
        + (f"{avoid}\n\n" if avoid else "")
        + "Return the JSON object now."
    )
    reply = await call_model(gateway, SYSTEM_PROMPT, user, model=model, timeout=timeout)
    if "error" in reply:
        return skip(topic, "model_unavailable", sources, reply["error"])

    def build(text: str) -> Dict[str, Any]:
        data = parse_reply(text)
        if data is None:
            return {"problem": "reply was not a JSON object"}
        problem = validate_dual_coding(data, sources, topic)
        if problem:
            return {"problem": problem}
        return {
            "prose": str(data["prose"]).strip(),
            "mermaid": _clean_mermaid(data["mermaid"]),
            "steps": [str(s).strip() for s in (data.get("steps") or []) if str(s).strip()][:6],
            "question": str(data["question"]).strip(),
            "answer": str(data["answer"]).strip(),
        }

    content = build(reply["text"])
    if "problem" in content:
        return skip(topic, "model_output_invalid", sources, content["problem"])
    content = await ask_again_if_repeated(  # CARD-654
        gateway, SYSTEM_PROMPT, user, reply["text"], content,
        lambda text: None if "problem" in (c := build(text)) else c,
        duplicate_of or avoid_checker(avoid_questions), sources=sources,
        asked=asked or [(q, "") for q in avoid_questions or []], model=model, timeout=timeout,
    )
    return {
        "ok": True,
        "topic": topic,
        "skip_reason": None,
        **content,
        "sources": public_sources(sources),
        "model": reply.get("model"),
    }
