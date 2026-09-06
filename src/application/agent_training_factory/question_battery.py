"""Intent Distill question battery (CARD-172). Domain-agnostic Self-Ask style prompts."""

from __future__ import annotations

from typing import Dict, List

# Locked intents from CARD-172; wording may be tuned, ids are stable.
DEFAULT_INTENT_QUESTIONS: List[Dict] = [
    {
        "id": "outcome",
        "text": "What is the operator trying to achieve (outcome)?",
        "implicated_by": ["outcome", "intent unclear", "goal", "achieve", "operator"],
    },
    {
        "id": "constraints",
        "text": "What constraints did they give (paths, env, generation, credentials policy)?",
        "implicated_by": ["constraint", "path", "credential", "policy", "env"],
    },
    {
        "id": "medium",
        "text": "What target medium (cli/api/host/files) should tools use?",
        "implicated_by": [
            "medium",
            "wrong medium",
            "misunderstood medium",
            "medium misunderstanding",
            "cli",
            "api",
            "filesystem",
        ],
    },
    {
        "id": "professional_sop",
        "text": "What would a professional SOP include for this role/task?",
        "implicated_by": [
            "sop",
            "missing sop",
            "professional sop",
            "procedure",
            "unknown procedure",
            "runbook",
            "operating manual",
        ],
    },
    {
        "id": "official_guidance",
        "text": "What official or standard guidance should be consulted?",
        "implicated_by": ["official guidance", "standard guidance", "guidance", "docs"],
    },
    {
        "id": "unknowns",
        "text": "What is still unknown / must be clarified or assumed?",
        "implicated_by": ["unknown", "unclear", "assume", "clarify", "grounding gap"],
    },
    {
        "id": "scenarios",
        "text": "What scenarios prove the capability works (done-whens)?",
        "implicated_by": [
            "scenario",
            "done-when",
            "done when",
            "capability",
            "prove",
            "not grounded",
        ],
    },
]


def implicated_questions(failure_text: str) -> List[Dict]:
    """Return only questions implicated by the failure text; full battery if none match."""
    blob = (failure_text or "").strip().lower()
    if not blob:
        return list(DEFAULT_INTENT_QUESTIONS)
    hit: List[Dict] = []
    for q in DEFAULT_INTENT_QUESTIONS:
        markers = q.get("implicated_by") or []
        if any(str(m).lower() in blob for m in markers):
            hit.append(q)
    return hit if hit else list(DEFAULT_INTENT_QUESTIONS)


def format_questions_for_prompt(questions: List[Dict]) -> str:
    lines = []
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. [{q['id']}] {q['text']}")
    return "\n".join(lines)
