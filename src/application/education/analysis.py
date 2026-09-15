"""Education Analysis: error log + metacog facts in memory.db [CARD-247].

On miss/fail, classify a deterministic miss_reason (no LLM) and persist
error_log + metacog semantic facts. Quiz selection consumes those miss
reasons to deepen CARD-243 weak-item pressure.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

ANALYSIS_ENTITY = "education_analysis"
ANALYSIS_CATEGORY = "education_analysis"

# Deterministic miss-reason taxonomy (binary / external — never LLM-authored).
MISS_REASON_EMPTY = "empty_answer"
MISS_REASON_WRONG = "wrong_answer"
MISS_REASON_PARTIAL = "partial_recall"
MISS_REASON_CONCEPT_GAP = "concept_gap"
MISS_REASON_UNKNOWN = "unknown_miss"

MISS_REASONS = (
    MISS_REASON_EMPTY,
    MISS_REASON_WRONG,
    MISS_REASON_PARTIAL,
    MISS_REASON_CONCEPT_GAP,
    MISS_REASON_UNKNOWN,
)


def _iso_now(now: Optional[datetime] = None) -> str:
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize(text: str) -> str:
    s = (text or "").strip().casefold()
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,;:!?\"'`")


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9][a-z0-9_\-]{1,}", _normalize(text)) if t]


def classify_miss_reason(
    *,
    expected: str = "",
    given: str = "",
    required_concepts: Optional[Sequence[str]] = None,
    correct: bool = False,
) -> str:
    """Binary/deterministic miss_reason — no LLM self-score."""
    if correct:
        return "pass"
    got = (given or "").strip()
    if not got:
        return MISS_REASON_EMPTY

    concepts = [c.strip() for c in (required_concepts or []) if str(c).strip()]
    if concepts:
        missing = [c for c in concepts if _normalize(c) not in _normalize(got)]
        if missing:
            return MISS_REASON_CONCEPT_GAP

    exp_toks = set(_tokens(expected))
    got_toks = set(_tokens(got))
    if exp_toks and got_toks:
        overlap = len(exp_toks & got_toks) / max(1, len(exp_toks))
        if 0 < overlap < 1.0 and _normalize(expected) != _normalize(got):
            return MISS_REASON_PARTIAL
        if overlap >= 1.0 and _normalize(expected) != _normalize(got):
            return MISS_REASON_PARTIAL
    if expected and _normalize(expected) != _normalize(got):
        return MISS_REASON_WRONG
    return MISS_REASON_UNKNOWN


def _safe_id_part(raw: str, n: int = 40) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in (raw or "")[:n])


def _error_fact_id(item_id: str, stamp: str) -> str:
    digest = hashlib.sha1(f"{item_id}|{stamp}".encode("utf-8")).hexdigest()[:10]
    return f"edu_err_{_safe_id_part(item_id, 24)}_{digest}"


def _metacog_fact_id(item_id: str, miss_reason: str) -> str:
    return f"edu_mc_{_safe_id_part(item_id, 24)}_{_safe_id_part(miss_reason, 20)}"


def _reason_pattern_fact_id(miss_reason: str) -> str:
    return f"edu_mc_pattern_{_safe_id_part(miss_reason, 24)}"


def _upsert_fact(
    repo: Any,
    *,
    fact_id: str,
    attribute: str,
    value: str,
    confidence: float = 1.0,
) -> str:
    existing = None
    try:
        existing = repo.get_semantic_fact(fact_id)
    except Exception:  # noqa: BLE001
        existing = None
    if existing:
        try:
            with repo.get_connection() as conn:
                conn.execute(
                    "UPDATE semantic_facts SET is_active = 1, value = ?, category = ?, confidence = ?, "
                    "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
                    (value, ANALYSIS_CATEGORY, confidence, fact_id),
                )
            return fact_id
        except Exception:  # noqa: BLE001
            pass
    try:
        return repo.add_semantic_fact(
            entity=ANALYSIS_ENTITY,
            attribute=attribute,
            value=value,
            category=ANALYSIS_CATEGORY,
            confidence=confidence,
            decay_half_life_days=120.0,
            fact_id=fact_id,
        )
    except Exception:  # noqa: BLE001
        try:
            repo.update_semantic_fact(
                fact_id,
                value=value,
                category=ANALYSIS_CATEGORY,
                confidence=confidence,
            )
        except Exception:  # noqa: BLE001
            pass
        return fact_id


def record_error_and_metacog(
    repo: Any,
    *,
    item: Dict[str, Any],
    given: str = "",
    correct: bool = False,
    required_concepts: Optional[Sequence[str]] = None,
    now: Optional[datetime] = None,
    source: str = "quiz",
) -> Dict[str, Any]:
    """On miss/fail, write error_log + metacog facts. Passes are no-ops for error log."""
    item_id = str(item.get("item_id") or "").strip()
    topic = str(item.get("topic") or "").strip() or "unknown"
    prompt = str(item.get("prompt") or "").strip()
    expected = str(item.get("expected_answer") or "").strip()
    concepts = list(required_concepts or item.get("required_concepts") or [])
    if isinstance(concepts, str):
        concepts = [c.strip() for c in concepts.split(",") if c.strip()]

    miss_reason = classify_miss_reason(
        expected=expected,
        given=given,
        required_concepts=concepts,
        correct=correct,
    )
    out: Dict[str, Any] = {
        "miss_reason": miss_reason,
        "error_fact_id": None,
        "metacog_fact_id": None,
        "pattern_fact_id": None,
        "recorded": False,
    }
    if correct or not item_id:
        return out

    stamp = _iso_now(now)
    given_snip = re.sub(r"\s+", " ", (given or "").strip())[:180]
    expected_snip = re.sub(r"\s+", " ", expected)[:180]
    missing_concepts = []
    if concepts:
        missing_concepts = [c for c in concepts if _normalize(c) not in _normalize(given or "")]

    error_value = (
        f"error_log item_id={item_id} topic={topic} source={source} "
        f"miss_reason={miss_reason} prompt={prompt[:120]} "
        f"expected={expected_snip or '(none)'} given={given_snip or '(empty)'} "
        f"missing_concepts={','.join(missing_concepts) or '(none)'} at={stamp}"
    )
    eid = _error_fact_id(item_id, stamp)
    out["error_fact_id"] = _upsert_fact(
        repo, fact_id=eid, attribute="error_log", value=error_value, confidence=1.0
    )

    metacog_value = (
        f"metacog item_id={item_id} topic={topic} miss_reason={miss_reason} "
        f"source={source} — learner failed via {miss_reason}; "
        f"prefer next quiz items sharing this miss_reason / topic over random strong items"
    )
    mid = _metacog_fact_id(item_id, miss_reason)
    out["metacog_fact_id"] = _upsert_fact(
        repo, fact_id=mid, attribute="metacog", value=metacog_value, confidence=1.0
    )

    pattern_value = (
        f"miss_reason_pattern reason={miss_reason} last_item_id={item_id} "
        f"topic={topic} — pressure weak items tied to {miss_reason}"
    )
    pid = _reason_pattern_fact_id(miss_reason)
    out["pattern_fact_id"] = _upsert_fact(
        repo, fact_id=pid, attribute="miss_reason_pattern", value=pattern_value, confidence=1.0
    )
    out["recorded"] = True
    return out


def list_error_log(repo: Any, *, limit: int = 50) -> List[Dict[str, Any]]:
    facts = list(repo.list_facts_for_entity(ANALYSIS_ENTITY, limit=max(limit * 3, 50)) or [])
    errors = [
        f
        for f in facts
        if f.get("attribute") == "error_log" and int(f.get("is_active") or 0) == 1
    ]
    errors.sort(key=lambda f: str(f.get("updated_at") or f.get("created_at") or ""), reverse=True)
    return errors[: max(1, int(limit or 1))]


def list_metacog_patterns(repo: Any, *, limit: int = 50) -> List[Dict[str, Any]]:
    facts = list(repo.list_facts_for_entity(ANALYSIS_ENTITY, limit=max(limit * 3, 50)) or [])
    pats = [
        f
        for f in facts
        if f.get("attribute") in ("metacog", "miss_reason_pattern")
        and int(f.get("is_active") or 0) == 1
    ]
    pats.sort(key=lambda f: str(f.get("updated_at") or f.get("created_at") or ""), reverse=True)
    return pats[: max(1, int(limit or 1))]


def active_miss_reasons(repo: Any) -> List[str]:
    """Miss reasons currently represented in analysis metacog / error facts."""
    reasons: List[str] = []
    seen: set[str] = set()
    for fact in list_metacog_patterns(repo, limit=100) + list_error_log(repo, limit=100):
        val = str(fact.get("value") or "")
        m = re.search(r"miss_reason=([a-z_]+)", val)
        if not m:
            m = re.search(r"reason=([a-z_]+)", val)
        if m:
            r = m.group(1)
            if r in MISS_REASONS and r not in seen:
                seen.add(r)
                reasons.append(r)
    return reasons


def item_ids_for_miss_reasons(repo: Any, reasons: Optional[Sequence[str]] = None) -> List[str]:
    """Item ids mentioned in error_log / metacog for the given miss reasons."""
    want = set(reasons or active_miss_reasons(repo))
    if not want:
        return []
    ids: List[str] = []
    seen: set[str] = set()
    for fact in list_error_log(repo, limit=200) + list_metacog_patterns(repo, limit=200):
        val = str(fact.get("value") or "")
        rm = re.search(r"miss_reason=([a-z_]+)", val) or re.search(r"reason=([a-z_]+)", val)
        if not rm or rm.group(1) not in want:
            continue
        im = re.search(r"item_id=([A-Za-z0-9_\-]+)", val)
        if not im:
            im = re.search(r"last_item_id=([A-Za-z0-9_\-]+)", val)
        if im:
            iid = im.group(1)
            if iid not in seen:
                seen.add(iid)
                ids.append(iid)
    return ids


def select_quiz_with_miss_reason_pressure(
    repo: Any,
    *,
    limit: int = 5,
    as_of: Optional[datetime] = None,
    topic: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """CARD-243 weak preference + CARD-247 miss-reason pressure."""
    from src.application.education.learner_model import _priority_key, select_quiz_items

    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    base = select_quiz_items(repo, limit=max(50, limit * 10), as_of=now, topic=topic)
    hot_ids = set(item_ids_for_miss_reasons(repo))
    reasons = active_miss_reasons(repo)

    def _key(row: Dict[str, Any]) -> tuple:
        iid = str(row.get("item_id") or "")
        reason_band = 0 if iid in hot_ids else 1
        return (reason_band,) + _priority_key(row, now)

    ranked = sorted(base, key=_key)
    lim = max(1, int(limit or 1))
    out = ranked[:lim]
    for row in out:
        if str(row.get("item_id") or "") in hot_ids:
            row["analysis_pressure"] = True
            row["active_miss_reasons"] = list(reasons)
        else:
            row["analysis_pressure"] = False
    return out


def write_analysis_wiki_outcome(
    wiki_store: Any,
    *,
    wiki_path: str,
    item: Dict[str, Any],
    miss_reason: str,
    given: str = "",
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Append Analysis outcomes heading to the Wiki note (optional write-back)."""
    path = (wiki_path or "").strip()
    if not path or wiki_store is None:
        return {"success": False, "error": "no_wiki_path"}
    stamp = _iso_now(now)
    snip = re.sub(r"\s+", " ", (given or "").strip())[:240]
    chunk = (
        f"- [{stamp}] item_id={item.get('item_id')} miss_reason={miss_reason}\n"
        f"  Prompt: {str(item.get('prompt') or '').strip()}\n"
        f"  Given: {snip or '(empty)'}\n"
    )
    try:
        result = wiki_store.append_note(path, chunk, heading="Analysis outcomes")
        if isinstance(result, dict):
            return result
        return {"success": True, "path": path}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc), "path": path}


def summarize_analysis(repo: Any, *, limit: int = 50) -> Dict[str, Any]:
    errors = list_error_log(repo, limit=limit)
    patterns = list_metacog_patterns(repo, limit=limit)
    reasons = active_miss_reasons(repo)
    hot = item_ids_for_miss_reasons(repo, reasons)
    return {
        "entity": ANALYSIS_ENTITY,
        "category": ANALYSIS_CATEGORY,
        "error_count": len(errors),
        "metacog_count": len(patterns),
        "active_miss_reasons": reasons,
        "pressured_item_ids": hot,
        "errors": errors,
        "patterns": patterns,
        "next_quiz": select_quiz_with_miss_reason_pressure(repo, limit=min(10, limit)),
    }


def build_analysis_ask_clause(summary: Dict[str, Any]) -> str:
    reasons = summary.get("active_miss_reasons") or []
    hot = summary.get("pressured_item_ids") or []
    if not reasons and not hot:
        return " No Analysis error-log miss reasons yet — teach normally."
    return (
        " Analysis miss reasons from durable memory.db must pressure the next quiz set "
        f"(reasons={', '.join(reasons) or 'none'}; items={', '.join(hot[:5]) or 'none'}). "
        "Do NOT quiz random strong items while these error patterns are active."
    )


def build_analysis_scorecard(
    memory_repo: Any,
    topic: str,
) -> Dict[str, Any]:
    """Analyze learner performance and error patterns for a topic [CARD-325]."""
    topic_clean = (topic or "").strip()
    items: List[Dict[str, Any]] = []
    if hasattr(memory_repo, "list_education_mastery"):
        try:
            items = list(memory_repo.list_education_mastery(topic=topic_clean, limit=500) or [])
        except TypeError:
            all_items = list(memory_repo.list_education_mastery(limit=500) or [])
            items = [it for it in all_items if (it.get("topic") or "").strip() == topic_clean]

    passed_items = [it for it in items if str(it.get("grade") or "").lower() == "pass"]
    missed_items = [
        it
        for it in items
        if str(it.get("grade") or "").lower() == "miss"
        or int(it.get("miss_count") or 0) > 0
    ]
    unseen_items = [it for it in items if str(it.get("grade") or "").lower() == "unseen"]

    total = len(items)
    passed_count = len(passed_items)
    missed_count = len(missed_items)
    pass_rate = round((passed_count / total * 100.0), 1) if total > 0 else 0.0

    error_patterns: List[str] = []
    if hasattr(memory_repo, "list_facts_for_entity"):
        facts = memory_repo.list_facts_for_entity(ANALYSIS_ENTITY, limit=100) or []
        for f in facts:
            val = str(f.get("value") or "")
            if topic_clean.lower() in val.lower():
                error_patterns.append(val)

    return {
        "topic": topic_clean,
        "total_items": total,
        "passed_count": passed_count,
        "missed_count": missed_count,
        "unseen_count": len(unseen_items),
        "pass_rate": pass_rate,
        "items": items,
        "weak_items": missed_items,
        "error_patterns": error_patterns,
    }


def build_analysis_note_content(
    topic: str,
    scorecard: Dict[str, Any],
    now: Optional[datetime] = None,
) -> str:
    """Format markdown for Analysis scorecard Wiki note using education-score structure [CARD-325]."""
    topic_clean = (topic or "").strip()
    stamp = _iso_now(now)
    total = scorecard.get("total_items", 0)
    passed = scorecard.get("passed_count", 0)
    missed = scorecard.get("missed_count", 0)
    pass_rate = scorecard.get("pass_rate", 0.0)
    weak_items = scorecard.get("weak_items", [])
    patterns = scorecard.get("error_patterns", [])

    weak_lines = "\n".join(
        f"- `{it.get('item_id')}`: {it.get('prompt', '')[:80]} (grade: {it.get('grade')}, misses: {it.get('miss_count', 0)})"
        for it in weak_items[:5]
    ) or "- No active weak items detected for this topic."

    pattern_lines = "\n".join(
        f"- {p[:120]}" for p in patterns[:5]
    ) or "- No recurring metacognitive error patterns logged."

    return (
        f"# Scorecard: {topic_clean}\n\n"
        f"> **Topic:** {topic_clean}\n"
        f"> **Pedagogy Phase:** Analysis & Metacognitive Review\n"
        f"> **Generated:** {stamp}\n\n"
        f"---\n\n"
        f"## 1. Mastery Status\n"
        f"- **Current Step:** analysis\n"
        f"- **Mastery Items Count:** {total}\n"
        f"- **Passed Items:** {passed}\n"
        f"- **Missed Items:** {missed}\n"
        f"- **Pass Rate:** {pass_rate}%\n\n"
        f"## 2. Weakness & Error Patterns\n"
        f"### Weak Items Under Pressure\n"
        f"{weak_lines}\n\n"
        f"### Metacognitive Review\n"
        f"{pattern_lines}\n\n"
        f"## 3. Retention Routine Next Due\n"
        f"- **Retention Handoff:** Handed off to fixed 1-3-7-30 SRS schedule\n"
        f"- **Routine Anchor:** Scheduled via `education_mastery.next_due` into `education-retrieval-retention` routine\n"
    )


def execute_analysis_retention_handoff(
    memory_repo: Any,
    *,
    topic: str,
    course_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Schedule missing next_due dates on mastery items and record durable handoff [CARD-325]."""
    from src.application.education.priming_schema import slug_topic
    from src.application.education.srs import next_due_after_grade

    topic_clean = (topic or "").strip()
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    stamp = base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    items: List[Dict[str, Any]] = []
    if hasattr(memory_repo, "list_education_mastery"):
        try:
            items = list(memory_repo.list_education_mastery(topic=topic_clean, limit=500) or [])
        except TypeError:
            all_items = list(memory_repo.list_education_mastery(limit=500) or [])
            items = [it for it in all_items if (it.get("topic") or "").strip() == topic_clean]

    scheduled_item_ids: List[str] = []
    for it in items:
        item_id = it.get("item_id")
        if not item_id:
            continue
        next_due = it.get("next_due")
        if not next_due:
            stage = int(it.get("interval_stage") or 0)
            grade = str(it.get("grade") or "").lower()
            correct = (grade == "pass")
            new_stage, due_dt = next_due_after_grade(correct=correct, interval_stage=stage, now=base)
            due_s = due_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            with memory_repo.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE education_mastery SET
                        next_due = ?,
                        interval_stage = ?,
                        updated_at = ?
                    WHERE item_id = ?
                    """,
                    (due_s, new_stage, stamp, item_id),
                )
            scheduled_item_ids.append(item_id)
        else:
            scheduled_item_ids.append(item_id)

    fact_id = f"edu_handoff_{slug_topic(topic_clean)}"[:64]
    fact_val = (
        f"course_handoff_retention topic={topic_clean} scheduled={len(scheduled_item_ids)} "
        f"course_id={course_id or 'standalone'} at={stamp} — handoff to Routine->Job SRS"
    )
    _upsert_fact(
        memory_repo,
        fact_id=fact_id,
        attribute="course_handoff_retention",
        value=fact_val,
        confidence=1.0,
    )

    return {
        "success": True,
        "topic": topic_clean,
        "course_id": course_id,
        "scheduled_count": len(scheduled_item_ids),
        "scheduled_item_ids": scheduled_item_ids,
        "handoff_at": stamp,
    }

