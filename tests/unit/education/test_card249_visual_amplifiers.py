"""CARD-249: Education Visual Amplifiers - Mermaid/step-through on Retrieval path."""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.application.education.visual_amplifiers import (
    AMPLIFIER_CATEGORY,
    AMPLIFIER_ENTITY,
    VisualsOnlyRejected,
    amplify_quiz_items,
    assert_amplifier_does_not_touch_srs,
    attach_amplifier_to_retrieval,
    build_amplifier_ask_clause,
    build_step_through,
    extract_amplifiers_from_note,
    extract_mermaid_blocks,
    get_amplifier_for_item,
    refuse_visuals_only,
    require_retrieval_path,
    summarize_amplifiers,
)
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


DUAL_NOTE = """---
title: CARD-249 Dual Coding Visual Amplifiers
tags: [education, dual-coding, mermaid]
---

# Retrieval path

Prose: amplifiers without Retrieval are edutainment.

```mermaid
flowchart TD
  A[Quiz item on mastery ledger] --> B[Attach Mermaid amplifier]
  B --> C[Step-through reveal]
  C --> D[Learner retrieves answer]
```

## Quiz
- Q: What must a visual amplifier attach to?
  A: Retrieval quiz mastery item
- Q: What are amplifiers without Retrieval?
  A: Edutainment

## Step-through
- 1. Start from a mastery ledger quiz item
- 2. Attach Dual Coding Mermaid
- 3. Reveal steps then retrieve the answer
"""


def _repo(tmp_path: Path) -> AgentMemoryRepository:
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    return repo


def _seed(repo, item_id="edu_va_1", topic="Visual Amplifiers", prompt="What must a visual amplifier attach to?", expected="Retrieval quiz mastery item"):
    repo.upsert_education_mastery(
        item_id=item_id,
        topic=topic,
        wiki_path="00_Inbox/card249_visual_amplifiers_smoke.md",
        prompt=prompt,
        expected_answer=expected,
        grade="unseen",
        next_due=None,
    )
    return item_id


def test_extract_mermaid_blocks_from_dual_coding_note():
    blocks = extract_mermaid_blocks(DUAL_NOTE)
    assert len(blocks) == 1
    assert "flowchart TD" in blocks[0]
    assert "Quiz item on mastery ledger" in blocks[0]


def test_build_step_through_prefers_explicit_section():
    steps = build_step_through("flowchart TD\n  X[Ignore] --> Y[Me]", note_content=DUAL_NOTE)
    assert len(steps) >= 3
    assert steps[0]["label"].lower().startswith("start from")
    assert steps[0]["source"] == "step_through_section"


def test_build_step_through_from_flowchart_when_no_section():
    mermaid = "flowchart LR\n  A[Prime schema] --> B[Dual code]\n  B --> C[Retrieve]"
    steps = build_step_through(mermaid)
    labels = [s["label"] for s in steps]
    assert labels == ["Prime schema", "Dual code", "Retrieve"]


def test_extract_amplifiers_not_shippable_until_retrieval():
    amps = extract_amplifiers_from_note(
        DUAL_NOTE,
        wiki_path="00_Inbox/card249_visual_amplifiers_smoke.md",
        topic="Visual Amplifiers",
    )
    assert len(amps) == 1
    amp = amps[0]
    assert amp["kind"] == "mermaid"
    assert amp["shippable"] is False
    assert amp["item_id"] is None
    assert amp["retrieval_required"] is True
    assert amp["lumina_film"] is False
    assert amp["step_count"] >= 3


def test_require_retrieval_path_rejects_missing_and_unknown(tmp_path):
    repo = _repo(tmp_path)
    with pytest.raises(VisualsOnlyRejected):
        require_retrieval_path(None, repo)
    with pytest.raises(VisualsOnlyRejected):
        require_retrieval_path("edu_missing", repo)
    with pytest.raises(VisualsOnlyRejected):
        refuse_visuals_only({"visuals_only": True, "mermaid": "flowchart TD\\n A[x]"})
    with pytest.raises(VisualsOnlyRejected):
        refuse_visuals_only({"item_id": ""})


def test_attach_amplifier_requires_mastery_and_persists(tmp_path):
    repo = _repo(tmp_path)
    item_id = _seed(repo)
    amps = extract_amplifiers_from_note(
        DUAL_NOTE,
        wiki_path="00_Inbox/card249_visual_amplifiers_smoke.md",
        topic="Visual Amplifiers",
    )
    with pytest.raises(VisualsOnlyRejected):
        attach_amplifier_to_retrieval(amps[0], "edu_nope", repo=repo)

    attached = attach_amplifier_to_retrieval(amps[0], item_id, repo=repo)
    assert attached["shippable"] is True
    assert attached["item_id"] == item_id
    assert attached["retrieval_path"] == "mastery_ledger_quiz"
    assert attached["mermaid"]
    assert attached["steps"]

    loaded = get_amplifier_for_item(repo, item_id)
    assert loaded is not None
    assert loaded["item_id"] == item_id
    assert "flowchart" in (loaded.get("mermaid") or "")

    summary = summarize_amplifiers(repo)
    assert summary["count"] >= 1
    assert summary["retrieval_required"] is True
    assert summary["lumina_film"] is False
    assert summary["entity"] == AMPLIFIER_ENTITY
    assert summary["category"] == AMPLIFIER_CATEGORY


def test_amplify_quiz_items_attaches_without_mutating_ledger(tmp_path):
    repo = _repo(tmp_path)
    item_id = _seed(repo)
    amps = extract_amplifiers_from_note(
        DUAL_NOTE,
        wiki_path="00_Inbox/card249_visual_amplifiers_smoke.md",
        topic="Visual Amplifiers",
    )
    attach_amplifier_to_retrieval(amps[0], item_id, repo=repo)
    before = repo.get_education_mastery(item_id)
    result = amplify_quiz_items(
        [
            {
                "item_id": item_id,
                "prompt": before["prompt"],
                "grade": before.get("grade"),
                "next_due": before.get("next_due"),
                "interval_stage": before.get("interval_stage"),
            },
            {"item_id": "edu_other_unamplified", "prompt": "plain"},
        ],
        repo,
    )
    assert result["amplified_count"] == 1
    top = result["items"][0]
    assert top["has_visual_amplifier"] is True
    assert top["amplifier_mermaid"]
    assert top["amplifier_steps"]
    assert top["next_due"] == before.get("next_due")
    assert top["grade"] == before.get("grade")
    after = repo.get_education_mastery(item_id)
    assert after.get("next_due") == before.get("next_due")
    assert after.get("grade") == before.get("grade")
    assert result["items"][1]["has_visual_amplifier"] is False


def test_amplifier_module_does_not_own_srs_or_lumina():
    import src.application.education.visual_amplifiers as mod

    assert assert_amplifier_does_not_touch_srs(inspect.getsource(mod)) is True


def test_ask_clause_pairs_visual_with_retrieval():
    clause = build_amplifier_ask_clause(
        {
            "amplifier_id": "amp_x",
            "item_id": "edu_va_1",
            "kind": "mermaid",
            "steps": [{"order": 1, "label": "Retrieve first"}],
        }
    )
    assert "edu_va_1" in clause
    assert "Retrieval" in clause
    assert "Lumina" in clause
    bare = build_amplifier_ask_clause(None)
    assert "edutainment" in bare.lower() or "Retrieval-backed" in bare
