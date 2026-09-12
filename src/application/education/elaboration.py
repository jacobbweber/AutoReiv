"""Education Elaboration: explain-it-back graded by binary external check [CARD-244].

Score is NEVER an LLM self-score. Miss updates the mastery ledger and can
schedule Routine->Job resurface via the CARD-242 retention path. Outcomes
write back to Wiki and/or agent memory.db.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.application.education.quiz_engine import grade_answer_binary

ELABORATION_ENTITY = "education_elaboration"
ELABORATION_CATEGORY = "education_elaboration"

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "for",
        "is",
        "are",
        "was",
        "were",
        "be",
        "as",
        "at",
        "by",
        "with",
        "that",
        "this",
        "it",
        "from",
        "into",
        "about",
        "your",
        "own",
        "words",
        "explain",
    }
)

_SECTION_RE = re.compile(
    r"^##\s+(Elaboration|Explain-it-back|Explain it back)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Bullet form:
# - Prompt: ...
#   Reference: ...
#   Concepts: a, b, c
_PROMPT_BLOCK_RE = re.compile(
    r"^[-\*]\s*Prompt:\s*(?P<prompt>.+?)\s*"
    r"(?:\n[ \t]+Reference:\s*(?P<reference>.+?)\s*)?"
    r"(?:\n[ \t]+Concepts:\s*(?P<concepts>.+?)\s*)?"
    r"(?=(?:\n[-\*])|\n##|\Z)",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)


def _normalize(text: str) -> str:
    s = (text or "").strip().casefold()
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,;:!?\"'`")


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9][a-z0-9_\-]{1,}", _normalize(text)) if t not in _STOPWORDS]


def _item_id_for(wiki_path: str, prompt: str) -> str:
    digest = hashlib.sha1(f"elab|{wiki_path}|{prompt}".encode("utf-8")).hexdigest()[:12]
    return f"elab_{digest}"


def _parse_concepts(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    parts = re.split(r"[,;|/]+", raw)
    out: List[str] = []
    for p in parts:
        c = _normalize(p)
        if c and c not in out:
            out.append(c)
    return out


def grade_elaboration_binary(
    given: str,
    *,
    reference: Optional[str] = None,
    required_concepts: Optional[Sequence[str]] = None,
) -> bool:
    """Binary external grade for explain-it-back.

    Precedence:
    1. Structured rubric: ALL required_concepts must appear (casefold substring).
    2. Reference: normalized equality OR all significant reference tokens appear in given.
    Never calls an LLM.
    """
    got = _normalize(given)
    if not got:
        return False

    concepts = [_normalize(c) for c in (required_concepts or []) if _normalize(c)]
    if concepts:
        return all(c in got for c in concepts)

    ref = (reference or "").strip()
    if not ref:
        return False

    # Exact / soft normalize equality first (reuse quiz grader)
    if grade_answer_binary(ref, given):
        return True

    # Token containment: every significant reference token must appear in given
    need = _tokens(ref)
    if not need:
        return False
    return all(tok in got for tok in need)


def extract_elaboration_items_from_note(
    content: str,
    *,
    wiki_path: str,
    topic: str = "",
) -> List[Dict[str, Any]]:
    """Extract explain-it-back items from ## Elaboration / ## Explain-it-back sections."""
    text = content or ""
    section = text
    m = _SECTION_RE.search(text)
    if m:
        rest = text[m.end() :]
        nxt = re.search(r"^##\s+\S", rest, re.MULTILINE)
        section = rest[: nxt.start()] if nxt else rest
    elif not re.search(r"(?im)^[-\*]\s*Prompt:", text):
        return []

    items: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for match in _PROMPT_BLOCK_RE.finditer(section):
        prompt = re.sub(r"\s+", " ", (match.group("prompt") or "").strip())
        reference = re.sub(r"\s+", " ", (match.group("reference") or "").strip())
        concepts = _parse_concepts(match.group("concepts"))
        if not prompt:
            continue
        if not reference and not concepts:
            continue
        iid = _item_id_for(wiki_path, prompt)
        if iid in seen:
            continue
        seen.add(iid)
        items.append(
            {
                "item_id": iid,
                "topic": topic or wiki_path,
                "wiki_path": wiki_path,
                "prompt": prompt,
                "expected_answer": reference,
                "required_concepts": concepts,
                "kind": "elaboration",
            }
        )
    return items


def elaboration_from_mastery_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt a mastery/quiz row into an elaboration explain-back item."""
    prompt = str(row.get("prompt") or "").strip()
    if prompt and not prompt.lower().startswith("explain"):
        prompt = f"Explain in your own words: {prompt}"
    concepts_raw = row.get("required_concepts")
    if isinstance(concepts_raw, str):
        concepts = _parse_concepts(concepts_raw)
    elif isinstance(concepts_raw, (list, tuple)):
        concepts = [_normalize(str(c)) for c in concepts_raw if _normalize(str(c))]
    else:
        concepts = []
    return {
        "item_id": row.get("item_id"),
        "topic": row.get("topic") or row.get("wiki_path") or "",
        "wiki_path": row.get("wiki_path") or "",
        "prompt": prompt,
        "expected_answer": row.get("expected_answer") or "",
        "required_concepts": concepts,
        "kind": "elaboration",
        "grade": row.get("grade"),
        "miss_count": row.get("miss_count"),
        "pass_count": row.get("pass_count"),
        "next_due": row.get("next_due"),
    }


def _fact_id(item_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (item_id or "")[:40])
    return f"edu_elab_{safe}"


def write_elaboration_memory_fact(
    repo: Any,
    *,
    item: Dict[str, Any],
    correct: bool,
    given: str,
) -> Optional[str]:
    """Persist elaboration outcome as a semantic fact in agent memory.db."""
    item_id = str(item.get("item_id") or "").strip()
    if not item_id:
        return None
    topic = str(item.get("topic") or "").strip() or "unknown"
    grade = "pass" if correct else "miss"
    snip = re.sub(r"\s+", " ", (given or "").strip())[:160]
    value = (
        f"elaboration item_id={item_id} topic={topic} grade={grade} "
        f"kind=explain_it_back given={snip}"
    )
    fid = _fact_id(item_id)
    try:
        existing = repo.get_semantic_fact(fid)
    except Exception:  # noqa: BLE001
        existing = None
    if existing:
        try:
            with repo.get_connection() as conn:
                conn.execute(
                    "UPDATE semantic_facts SET is_active = 1, value = ?, category = ?, confidence = ?, "
                    "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
                    (value, ELABORATION_CATEGORY, 1.0 if correct else 0.85, fid),
                )
            return fid
        except Exception:  # noqa: BLE001
            pass
    try:
        return repo.add_semantic_fact(
            entity=ELABORATION_ENTITY,
            attribute="elaboration_outcome",
            value=value,
            category=ELABORATION_CATEGORY,
            confidence=1.0 if correct else 0.85,
            decay_half_life_days=90.0,
            fact_id=fid,
        )
    except Exception:  # noqa: BLE001
        try:
            repo.update_semantic_fact(
                fid,
                value=value,
                category=ELABORATION_CATEGORY,
                confidence=1.0 if correct else 0.85,
            )
        except Exception:  # noqa: BLE001
            return None
        return fid


def write_elaboration_wiki_outcome(
    wiki_store: Any,
    *,
    wiki_path: str,
    item: Dict[str, Any],
    correct: bool,
    given: str,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Append elaboration outcome under ## Elaboration outcomes on the source Wiki note."""
    path = (wiki_path or item.get("wiki_path") or "").strip()
    if not path or wiki_store is None:
        return {"success": False, "error": "no_wiki_path"}
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    stamp = base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    grade = "pass" if correct else "miss"
    snip = re.sub(r"\s+", " ", (given or "").strip())[:240]
    prompt = str(item.get("prompt") or "").strip()
    chunk = (
        f"- [{stamp}] item_id={item.get('item_id')} grade={grade}\n"
        f"  Prompt: {prompt}\n"
        f"  Explain-back: {snip or '(empty)'}\n"
    )
    try:
        result = wiki_store.append_note(path, chunk, heading="Elaboration outcomes")
        if isinstance(result, dict):
            return result
        return {"success": True, "path": path}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc), "path": path}


def ensure_mastery_for_elaboration(repo: Any, item: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert mastery row so elaboration grades reuse the CARD-242 ledger."""
    item_id = str(item.get("item_id") or "").strip()
    if not item_id:
        raise ValueError("elaboration item_id required")
    existing = repo.get_education_mastery(item_id)
    if existing:
        return existing
    concepts = item.get("required_concepts") or []
    expected = str(item.get("expected_answer") or "").strip()
    if not expected and concepts:
        expected = ", ".join(concepts)
    mid = repo.upsert_education_mastery(
        item_id=item_id,
        topic=str(item.get("topic") or item.get("wiki_path") or "Elaboration"),
        wiki_path=str(item.get("wiki_path") or "00_Inbox/elaboration.md"),
        prompt=str(item.get("prompt") or ""),
        expected_answer=expected,
        grade="unseen",
    )
    row = repo.get_education_mastery(mid)
    assert row is not None
    return row


def grade_and_record_elaboration(
    *,
    repo: Any,
    item: Dict[str, Any],
    given: str,
    wiki_store: Any = None,
    now: Optional[datetime] = None,
    write_wiki: bool = True,
    write_memory: bool = True,
) -> Dict[str, Any]:
    """Binary-grade explain-back, update ledger, write Wiki/memory outcomes.

    Miss path updates mastery + next_due (1-3-7-30) so Routine->Job can resurface.
    """
    reference = str(item.get("expected_answer") or "").strip() or None
    concepts = item.get("required_concepts") or []
    if isinstance(concepts, str):
        concepts = _parse_concepts(concepts)
    correct = grade_elaboration_binary(
        given,
        reference=reference,
        required_concepts=concepts or None,
    )
    ensure_mastery_for_elaboration(repo, item)
    row = repo.record_education_grade(
        item_id=str(item["item_id"]),
        correct=correct,
        now=now,
    )
    memory_fact_id = None
    if write_memory:
        memory_fact_id = write_elaboration_memory_fact(
            repo, item=row, correct=correct, given=given
        )
    wiki_result: Dict[str, Any] = {"success": False, "skipped": True}
    if write_wiki and wiki_store is not None:
        wiki_result = write_elaboration_wiki_outcome(
            wiki_store,
            wiki_path=str(item.get("wiki_path") or row.get("wiki_path") or ""),
            item=row,
            correct=correct,
            given=given,
            now=now,
        )
    return {
        "correct": correct,
        "grade": row.get("grade"),
        "next_due": row.get("next_due"),
        "interval_stage": row.get("interval_stage"),
        "item": row,
        "grader": "binary_external_elaboration",
        "memory_fact_id": memory_fact_id,
        "wiki_writeback": wiki_result,
    }


def build_elaboration_ask_clause(items: List[Dict[str, Any]]) -> str:
    if not items:
        return " No elaboration items ready — teach normally without inventing LLM self-scored fluff."
    parts = []
    for it in items[:3]:
        iid = it.get("item_id") or ""
        topic = it.get("topic") or ""
        prompt = it.get("prompt") or ""
        parts.append(f'- item_id={iid} topic="{topic}" prompt="{prompt}"')
    joined = "\n".join(parts)
    return (
        " Ask the learner to **explain it back** (elaboration) for these items. "
        "Grade with binary external reference/concepts check only — never LLM self-score:\n"
        f"{joined}\n"
        "On miss, update the mastery ledger and allow Routine→Job resurface."
    )
