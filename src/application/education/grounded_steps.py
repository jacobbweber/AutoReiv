"""Grounded content for the priming, elaboration, lab and environment course steps [CARD-642..646].

Each step is built from the learner's own wiki notes on the topic (and, for elaboration and labs,
what the learner wrote) through one call to the configured model, then checked against those notes.
A reply that is not grounded, or repeats a retired template, is refused. With no notes, no model or
a refused reply the step writes nothing and only records progress. There is no fallback template.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.application.education.grounded import (
    avoid_block,
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
    vocab_of,
)

_RULES = (
    "Use ONLY facts stated in the notes. Do not add outside knowledge, do not write generic study "
    "advice and do not mention this app, wikis, ledgers or study methods. Reply with one JSON object "
    "and nothing else, with these keys: "
)


@dataclass(frozen=True)
class StepSpec:
    step: str
    system: str
    # (key, min items, max items): every list item is a short string; most must use words from the notes.
    lists: Tuple[Tuple[str, int, int], ...] = ()
    # (key, min grounded words): text fields that must use at least that many words from the notes.
    texts: Tuple[Tuple[str, int], ...] = ()
    # The list whose items together must use at least this many distinct words from the notes.
    main_list: str = ""
    main_min_grounded: int = 4
    banned: Tuple[str, ...] = field(default_factory=tuple)
    # Steps built on what the learner wrote (elaboration explanation, lab submission) [CARD-644].
    needs_learner_text: bool = False
    # Text fields that must use words from the learner's own text, not just the notes.
    learner_grounded: Tuple[str, ...] = ()


STEP_SPECS: Dict[str, StepSpec] = {
    "priming": StepSpec(
        step="priming",
        system=(
            "You prime a learner for a topic before they study it in depth, using their own notes. "
            + _RULES
            + '"outline" (3 to 6 short key ideas from the notes, each naming concrete terms from the notes), '
            '"prerequisites" (0 to 3 things the notes rely on that the learner should already know; [] if none), '
            '"question" (one question the learner can answer from the notes), '
            '"answer" (the short answer, taken from the notes).'
        ),
        lists=(("outline", 3, 6), ("prerequisites", 0, 3)),
        texts=(("question", 0), ("answer", 1)),
        main_list="outline",
    ),
    "elaboration": StepSpec(
        step="elaboration",
        system=(
            "You help a learner go deeper on their own explanation of a topic. Use ONLY what the learner "
            "wrote and facts stated in their notes (there may be no notes). "
            + _RULES
            + '"probes" (2 to 4 follow-up questions that push the learner further on what they wrote, '
            "using terms from their explanation or notes), "
            '"question" (one question that the learner\'s explanation answers), '
            '"answer" (the short answer, in words taken from the learner\'s explanation).'
        ),
        lists=(("probes", 2, 4),),
        texts=(("question", 0), ("answer", 1)),
        main_list="probes",
        main_min_grounded=2,
        needs_learner_text=True,
        learner_grounded=("answer",),
    ),
    "environment": StepSpec(
        step="environment",
        system=(
            "You suggest where and how a learner can practise or observe a topic, using only situations, "
            "examples and mechanisms described in their own notes. "
            + _RULES
            + '"practice" (2 to 4 concrete things to try or watch for, each naming terms from the notes), '
            '"question" (one question the learner can answer from the notes), '
            '"answer" (the short answer, taken from the notes).'
        ),
        lists=(("practice", 2, 4),),
        texts=(("question", 0), ("answer", 1)),
        main_list="practice",
        main_min_grounded=3,
    ),
    **{
        lab_step: StepSpec(
            step=lab_step,
            system=(
                (
                    "You design a hands-on construction lab: the learner builds or models the mechanism "
                    "described in their own notes. "
                    if lab_step == "construction"
                    else "You design a hands-on application lab: the learner applies what their own notes "
                    "describe to a concrete situation or failure taken from those notes. "
                )
                + _RULES
                + '"objective" (one sentence using concrete terms from the notes), '
                '"tasks" (3 to 5 short concrete steps the learner does), '
                '"criteria" (2 to 4 checkable statements a correct submission must cover, each naming a '
                "concrete term from the notes), "
                '"question" (one question the learner can answer from the notes), '
                '"answer" (the short answer, taken from the notes).'
            ),
            lists=(("tasks", 3, 5), ("criteria", 2, 4)),
            texts=(("objective", 1), ("question", 0), ("answer", 1)),
            main_list="tasks",
            main_min_grounded=3,
        )
        for lab_step in ("construction", "application")
    },
}

GROUNDED_STEPS = frozenset({"dual_coding", *STEP_SPECS})


def _clean_list(value: Any, max_items: int) -> List[str]:
    if isinstance(value, str):
        value = [value]
    items = [" ".join(str(v).split()) for v in (value or []) if str(v).strip()]
    return [i.lstrip("-*0123456789. ").strip() or i for i in items][:max_items]


def validate_step_content(
    spec: StepSpec,
    payload: Dict[str, Any],
    sources: List[Dict[str, Any]],
    topic: str,
    learner_text: str = "",
) -> Optional[str]:
    """Return why `payload` is not grounded in `sources` (and the learner's text), or None when it is."""
    texts = {key: " ".join(str(payload.get(key) or "").split()) for key, _ in spec.texts}
    lists = {key: _clean_list(payload.get(key), hi) for key, _lo, hi in spec.lists}
    every = [*texts.values(), *(i for items in lists.values() for i in items)]
    if has_banned(every, spec.banned):
        return "generic template text"
    learner_vocab = vocab_of([learner_text]) if learner_text else set()
    vocab = source_vocab(sources) | learner_vocab
    topic_stems = {stem(w) for w in topic_keywords(topic)}
    for key, lo, _hi in spec.lists:
        items = lists[key]
        if len(items) < lo:
            return f"too few {key}"
        grounded_items = sum(1 for i in items if grounded_count(i, vocab, topic_stems) >= 1)
        if items and grounded_items * 2 < len(items):
            return f"{key} are not taken from the notes"
    if spec.main_list:
        if grounded_count(" ".join(lists[spec.main_list]), vocab, topic_stems) < spec.main_min_grounded:
            return f"{spec.main_list} is not taken from the notes"
    for key, min_grounded in spec.texts:
        if not texts[key]:
            return f"missing {key}"
        if grounded_count(texts[key], vocab, topic_stems) < min_grounded:
            return f"{key} is not taken from the notes"
    for key in spec.learner_grounded:
        if grounded_count(texts.get(key, ""), learner_vocab, topic_stems) < 1:
            return f"{key} is not taken from what the learner wrote"
    return None


async def compose_step_content(
    gateway: Any,
    wiki_tools: Any,
    topic: str,
    step: str,
    *,
    learner_text: Optional[str] = None,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
    avoid_questions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Grounded content for course `step` on `topic`, or a skip with its reason (never a template).

    `learner_text` is what the learner wrote for the step (elaboration explanation, lab submission).
    """
    topic = (topic or "").strip()
    step = (step or "").strip().lower()
    spec = STEP_SPECS.get(step)
    if spec is None:
        return skip(topic, "no_writer")
    learner = (learner_text or "").strip()
    if spec.needs_learner_text and not learner:
        return skip(topic, "no_learner_explanation")
    sources = find_sources(wiki_tools, topic)
    if not sources and not learner:
        return skip(topic, "no_wiki_notes")
    if gateway is None:
        return skip(topic, "model_unavailable", sources, "no model gateway")

    parts = [f"Topic: {topic}"]
    if learner:
        parts.append(f"What the learner wrote:\n\n{learner}")
    parts.append(f"The learner's notes:\n\n{notes_block(sources)}" if sources else "The learner has no notes on this topic.")
    avoid = avoid_block(avoid_questions)  # CARD-650: don't ask what the ledger already asks
    if avoid:
        parts.append(avoid)
    user = "\n\n".join(parts) + "\n\nReturn the JSON object now."
    reply = await call_model(gateway, spec.system, user, model=model, timeout=timeout)
    if "error" in reply:
        return skip(topic, "model_unavailable", sources, reply["error"])
    data = parse_reply(reply["text"])
    if data is None:
        return skip(topic, "model_output_invalid", sources, "reply was not a JSON object")
    problem = validate_step_content(spec, data, sources, topic, learner)
    if problem:
        return skip(topic, "model_output_invalid", sources, problem)

    content: Dict[str, Any] = {key: " ".join(str(data.get(key) or "").split()) for key, _ in spec.texts}
    content.update({key: _clean_list(data.get(key), hi) for key, _lo, hi in spec.lists})
    return {
        "ok": True,
        "topic": topic,
        "step": step,
        "skip_reason": None,
        **content,
        "sources": public_sources(sources),
        "model": reply.get("model"),
    }


async def compose_course_step(
    gateway: Any,
    wiki_tools: Any,
    topic: str,
    step: str,
    *,
    learner_explanation: Optional[str] = None,
    lab_submission: Optional[str] = None,  # accepted for symmetry; labs never ground in it
    avoid_questions: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Grounded content for whichever course step is current, or None for steps that need none."""
    step = (step or "").strip().lower()
    if step == "dual_coding":
        from src.application.education.dual_coding import compose_dual_coding

        return await compose_dual_coding(gateway, wiki_tools, topic, avoid_questions=avoid_questions)
    if step in STEP_SPECS:
        # Labs are designed from the notes only; the submission is graded against them, never used to build them.
        learner = learner_explanation if step == "elaboration" else None
        return await compose_step_content(
            gateway, wiki_tools, topic, step, learner_text=learner, avoid_questions=avoid_questions
        )
    return None
