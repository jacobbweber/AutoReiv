"""Priming ledger seed into memory.db [CARD-317]."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.application.education.priming_schema import PRIMING_LEARNER_ATTR, topic_anchor_id
from src.application.education.quiz_engine import extract_quiz_items_from_note


def record_learner_priming_anchor(
    repo: Any,
    *,
    topic: str,
    wiki_path: str,
    item_id: str = "",
) -> Optional[str]:
    """Optional learner fact tying topic + wiki_path (CARD-317 ledger anchor)."""
    if repo is None:
        return None
    topic_clean = (topic or "").strip() or "unknown"
    path = (wiki_path or "").strip()
    iid = (item_id or "").strip() or topic_anchor_id(topic_clean, path)
    value = f"priming topic={topic_clean} wiki_path={path} item_id={iid}"
    fid = f"edu_lm_{PRIMING_LEARNER_ATTR}_{''.join(c if c.isalnum() or c in '-_' else '_' for c in iid[:40])}"
    try:
        existing = None
        try:
            existing = repo.get_semantic_fact(fid)
        except Exception:  # noqa: BLE001
            existing = None
        if existing:
            with repo.get_connection() as conn:
                conn.execute(
                    "UPDATE semantic_facts SET is_active = 1, value = ?, category = ?, "
                    "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
                    (value, "education_learner", fid),
                )
            return fid
        return repo.add_semantic_fact(
            entity="education_learner",
            attribute=PRIMING_LEARNER_ATTR,
            value=value,
            category="education_learner",
            confidence=1.0,
            decay_half_life_days=90.0,
            fact_id=fid,
        )
    except Exception:  # noqa: BLE001
        return None


def seed_ledger_anchors_from_priming_note(
    repo: Any,
    *,
    content: str,
    wiki_path: str,
    topic: str,
    write_learner_fact: bool = True,
) -> Dict[str, Any]:
    """Upsert education_mastery from Quiz/outline; optional learner priming fact."""
    if repo is None:
        return {"success": False, "error": "no_memory_repo", "items": [], "item_ids": []}
    path = (wiki_path or "").strip()
    topic_clean = (topic or "").strip() or path or "Education"
    items = extract_quiz_items_from_note(content or "", wiki_path=path, topic=topic_clean)

    if not items:
        iid = topic_anchor_id(topic_clean, path)
        items = [
            {
                "item_id": iid,
                "topic": topic_clean,
                "wiki_path": path,
                "prompt": f"What is the Priming schema outline for {topic_clean}?",
                "expected_answer": f"Outline + prerequisites + learning goals in Wiki for {topic_clean}",
            }
        ]

    persisted: List[Dict[str, Any]] = []
    ids: List[str] = []
    for it in items:
        mid = repo.upsert_education_mastery(
            item_id=it["item_id"],
            topic=it.get("topic") or topic_clean,
            wiki_path=it.get("wiki_path") or path,
            prompt=it.get("prompt") or "",
            expected_answer=it.get("expected_answer") or "",
            grade="unseen",
        )
        ids.append(mid)
        row = repo.get_education_mastery(mid)
        if row:
            persisted.append(row)

    learner_fact_id = None
    if write_learner_fact and ids:
        learner_fact_id = record_learner_priming_anchor(
            repo,
            topic=topic_clean,
            wiki_path=path,
            item_id=ids[0],
        )

    return {
        "success": True,
        "items": persisted,
        "item_ids": ids,
        "count": len(ids),
        "learner_fact_id": learner_fact_id,
        "topic": topic_clean,
        "wiki_path": path,
    }
