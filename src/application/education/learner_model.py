"""Education learner model: strengths/weaknesses/patterns in memory.db [CARD-243].

Deepens the thin CARD-242 mastery ledger into durable second-mind facts.
Does NOT invent a second tutor runtime - selection + semantic facts only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

LEARNER_ENTITY = "education_learner"
LEARNER_CATEGORY = "education_learner"


def _iso_now(now: Optional[datetime] = None) -> str:
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_due(value: Any) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _fact_id(attr: str, item_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (item_id or "")[:40])
    return f"edu_lm_{attr}_{safe}"


def _deactivate_conflicting(repo: Any, *, attribute: str, item_id: str) -> None:
    """When miss becomes pass (or vice versa), deactivate the opposite fact for that item."""
    opposite = "strength" if attribute == "weakness" else "weakness" if attribute == "strength" else None
    if not opposite:
        return
    fid = _fact_id(opposite, item_id)
    try:
        existing = repo.get_semantic_fact(fid)
        if existing and int(existing.get("is_active") or 0) == 1:
            repo.delete_semantic_fact(fid)  # soft or hard depending on impl
    except Exception:  # noqa: BLE001
        pass


def _upsert_learner_fact(
    repo: Any,
    *,
    attribute: str,
    item_id: str,
    value: str,
    confidence: float = 1.0,
) -> str:
    fid = _fact_id(attribute, item_id)
    # Prefer update-in-place when fact exists so kill/resume stays stable
    existing = None
    try:
        existing = repo.get_semantic_fact(fid)
    except Exception:  # noqa: BLE001
        existing = None
    if existing:
        try:
            # Reactivate if soft-deleted
            with repo.get_connection() as conn:
                conn.execute(
                    "UPDATE semantic_facts SET is_active = 1, value = ?, category = ?, confidence = ?, "
                    "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
                    (value, LEARNER_CATEGORY, confidence, fid),
                )
            return fid
        except Exception:  # noqa: BLE001
            pass
    try:
        return repo.add_semantic_fact(
            entity=LEARNER_ENTITY,
            attribute=attribute,
            value=value,
            category=LEARNER_CATEGORY,
            confidence=confidence,
            decay_half_life_days=90.0,
            fact_id=fid,
        )
    except Exception:  # noqa: BLE001
        try:
            repo.update_semantic_fact(
                fid,
                value=value,
                category=LEARNER_CATEGORY,
                confidence=confidence,
            )
        except Exception:  # noqa: BLE001
            pass
        return fid


def record_learner_from_grade(
    repo: Any,
    *,
    item: Dict[str, Any],
    correct: bool,
) -> Dict[str, Optional[str]]:
    """Write/update strength or weakness + pattern facts from a graded mastery row."""
    item_id = str(item.get("item_id") or "").strip()
    topic = str(item.get("topic") or "").strip() or "unknown"
    prompt = str(item.get("prompt") or "").strip()
    miss_count = int(item.get("miss_count") or 0)
    pass_count = int(item.get("pass_count") or 0)
    grade = str(item.get("grade") or ("pass" if correct else "miss"))

    out: Dict[str, Optional[str]] = {
        "weakness_fact_id": None,
        "strength_fact_id": None,
        "pattern_fact_id": None,
    }
    if not item_id:
        return out

    if correct:
        _deactivate_conflicting(repo, attribute="strength", item_id=item_id)
        value = (
            f"strength item_id={item_id} topic={topic} "
            f"prompt={prompt[:120]} pass_count={pass_count} grade={grade}"
        )
        out["strength_fact_id"] = _upsert_learner_fact(
            repo, attribute="strength", item_id=item_id, value=value, confidence=min(1.0, 0.5 + 0.1 * pass_count)
        )
        pattern = (
            f"pattern item_id={item_id} topic={topic}: recent_pass "
            f"(pass_count={pass_count}, miss_count={miss_count})"
        )
    else:
        _deactivate_conflicting(repo, attribute="weakness", item_id=item_id)
        value = (
            f"weakness item_id={item_id} topic={topic} "
            f"prompt={prompt[:120]} miss_count={miss_count} grade={grade}"
        )
        out["weakness_fact_id"] = _upsert_learner_fact(
            repo, attribute="weakness", item_id=item_id, value=value, confidence=min(1.0, 0.6 + 0.1 * miss_count)
        )
        pattern = (
            f"pattern item_id={item_id} topic={topic}: repeated_miss "
            f"(miss_count={miss_count}, pass_count={pass_count}) - prefer this over random strong items"
        )

    out["pattern_fact_id"] = _upsert_learner_fact(
        repo, attribute="pattern", item_id=item_id, value=pattern, confidence=1.0
    )
    return out


def _priority_key(item: Dict[str, Any], as_of: datetime) -> tuple:
    """Lower tuple sorts first: due -> weak/miss -> unseen -> pass/strong."""
    due = _parse_due(item.get("next_due"))
    is_due = 0 if (due is not None and due <= as_of) else 1
    grade = (item.get("grade") or "unseen").strip().lower()
    miss_count = int(item.get("miss_count") or 0)
    pass_count = int(item.get("pass_count") or 0)

    if grade == "miss" or miss_count > 0:
        band = 0 if is_due == 0 else 1
    elif grade in ("", "unseen"):
        band = 2
    else:  # pass / strong
        band = 3

    # Within band: more misses first; earlier due first; fewer passes first
    due_ts = due.timestamp() if due is not None else float("inf")
    return (is_due if band == 0 else 0, band, -miss_count, due_ts, pass_count, str(item.get("item_id") or ""))


def select_quiz_items(
    repo: Any,
    *,
    limit: int = 5,
    as_of: Optional[datetime] = None,
    topic: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Prefer due / weak / missed items over random or first-extracted order."""
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    rows = list(repo.list_education_mastery(limit=500) or [])
    if topic:
        t = topic.strip().casefold()
        rows = [r for r in rows if t in str(r.get("topic") or "").casefold()]

    ranked = sorted(rows, key=lambda r: _priority_key(r, now))
    lim = max(1, int(limit or 1))
    return ranked[:lim]


def build_ask_pressure_clause(items: List[Dict[str, Any]]) -> str:
    """Outcome clause so Education Ask pressures known misses, not random strong items."""
    if not items:
        return (
            " No known weak quiz items in the learner model yet - "
            "teach normally without inventing random drills."
        )
    parts = []
    for it in items[:3]:
        iid = it.get("item_id") or ""
        topic = it.get("topic") or ""
        prompt = it.get("prompt") or ""
        misses = it.get("miss_count") or 0
        parts.append(
            f'- item_id={iid} topic="{topic}" prompt="{prompt}" (miss_count={misses})'
        )
    joined = "\n".join(parts)
    return (
        " Pressure known miss(es) from the durable learner model in memory.db "
        "(do NOT quiz random strong items when a miss is known):\n"
        f"{joined}\n"
        "Re-ask or reteach those weak prompts first, then confirm recall."
    )


def summarize_learner_model(repo: Any, *, limit: int = 50) -> Dict[str, Any]:
    facts = list(repo.list_facts_for_entity(LEARNER_ENTITY, limit=limit) or [])
    weak = [f for f in facts if f.get("attribute") == "weakness" and int(f.get("is_active") or 0) == 1]
    strong = [f for f in facts if f.get("attribute") == "strength" and int(f.get("is_active") or 0) == 1]
    patterns = [f for f in facts if f.get("attribute") == "pattern" and int(f.get("is_active") or 0) == 1]
    mastery = list(repo.list_education_mastery(limit=limit) or [])
    missed = [m for m in mastery if (m.get("grade") or "") == "miss" or int(m.get("miss_count") or 0) > 0]
    return {
        "entity": LEARNER_ENTITY,
        "category": LEARNER_CATEGORY,
        "weakness_count": len(weak),
        "strength_count": len(strong),
        "pattern_count": len(patterns),
        "missed_mastery_count": len(missed),
        "facts": facts,
        "items": select_quiz_items(repo, limit=min(10, limit)),
    }
