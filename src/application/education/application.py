"""Education Application: Exercise Job + binary external verify [CARD-246].

Score is NEVER an LLM self-score. Prefer standing Exercise Job mint.
Fail -> bounded replan or HITL park (CARD-232) and/or mastery miss + resurface.
Pass -> advance mastery ledger. Outcomes write back to Wiki and/or memory.db.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.application.education.quiz_engine import grade_answer_binary
from src.application.orchestration.bounded_auto_replan import (
    MAX_REPLAN_ATTEMPTS,
    apply_bounded_replan_on_failed,
    should_auto_replan,
)

APPLICATION_ENTITY = "education_application"
APPLICATION_CATEGORY = "education_application"
APPLICATION_KIND = "application_exercise"

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
        "apply",
        "exercise",
        "task",
    }
)

_SECTION_RE = re.compile(
    r"^##\s+(Application|Exercise|Exercises|Apply)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Bullet forms:
# - Task: ...
#   Expected: ...
#   Concepts: a, b, c
# - Prompt: ...
#   Reference: ...
#   Concepts: ...
_TASK_BLOCK_RE = re.compile(
    r"^[-\*]\s*(?:Task|Prompt|Exercise):\s*(?P<prompt>.+?)\s*"
    r"(?:\n[ \t]+(?:Expected|Reference|Verify):\s*(?P<reference>.+?)\s*)?"
    r"(?:\n[ \t]+Concepts:\s*(?P<concepts>.+?)\s*)?"
    r"(?=(?:\n[-\*])|\n##|\Z)",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)


def _normalize(text: str) -> str:
    s = (text or "").strip().casefold()
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,;:!?\"'`")


def _tokens(text: str) -> List[str]:
    return [
        t
        for t in re.findall(r"[a-z0-9][a-z0-9_\-]{1,}", _normalize(text))
        if t not in _STOPWORDS
    ]


def _item_id_for(wiki_path: str, prompt: str) -> str:
    digest = hashlib.sha1(f"app|{wiki_path}|{prompt}".encode("utf-8")).hexdigest()[:12]
    return f"app_{digest}"


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


def grade_application_binary(
    given: str,
    *,
    reference: Optional[str] = None,
    required_concepts: Optional[Sequence[str]] = None,
) -> bool:
    """Binary external Application grade. Never LLM self-score.

    Pass when:
    - required_concepts all appear as tokens in given, OR
    - reference soft-equals / token-containment against given (reuse quiz normalize).
    """
    concepts = [c for c in (required_concepts or []) if _normalize(str(c))]
    if concepts:
        got = set(_tokens(given))
        need = []
        for c in concepts:
            parts = _tokens(c) or [_normalize(c)]
            need.append(parts)
        return all(any(p in got for p in parts) for parts in need)

    ref = (reference or "").strip()
    if not ref:
        return False
    if grade_answer_binary(ref, given):
        return True
    # Soft containment: enough reference tokens present in the attempt
    ref_toks = _tokens(ref)
    if not ref_toks:
        return False
    got = set(_tokens(given))
    hits = sum(1 for t in ref_toks if t in got)
    return hits >= max(1, (len(ref_toks) + 1) // 2)


def extract_application_items_from_note(
    content: str,
    *,
    wiki_path: str,
    topic: str = "",
) -> List[Dict[str, Any]]:
    """Extract Application / Exercise tasks from a Wiki note body."""
    text = content or ""
    section = text
    m = _SECTION_RE.search(text)
    if m:
        rest = text[m.end() :]
        nxt = re.search(r"^##\s+\S", rest, re.MULTILINE)
        section = rest[: nxt.start()] if nxt else rest

    items: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for match in _TASK_BLOCK_RE.finditer(section):
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
                "kind": APPLICATION_KIND,
            }
        )
    return items


def application_from_mastery_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt a mastery row into an Application exercise item."""
    prompt = str(row.get("prompt") or "").strip()
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
        "kind": APPLICATION_KIND,
        "grade": row.get("grade"),
        "miss_count": row.get("miss_count"),
        "pass_count": row.get("pass_count"),
        "next_due": row.get("next_due"),
        "pending_job_id": row.get("pending_job_id"),
    }


def build_exercise_job_intent(item: Dict[str, Any]) -> str:
    """Outcome-shaped standing ask for an Application Exercise Job."""
    topic = item.get("topic") or "Education"
    prompt = item.get("prompt") or ""
    path = item.get("wiki_path") or ""
    iid = item.get("item_id") or ""
    return (
        f"[Education Studio] [Mode: Application] Exercise Job for item {iid} "
        f'on topic "{topic}" (Wiki: {path}). '
        f"Prompt the learner to apply: {prompt}. "
        "Grade with binary external reference/concepts verify only - never LLM self-score. "
        "On fail: bounded replan or HITL park (never silent advance). On pass: advance mastery. "
        "This is a standing Exercise Job - not a chat toast. "
        "Use only wiki_note_search/wiki_note_read when grounding (never wiki_overview). "
        f'Done-when: the learner has submitted a binary-verified attempt for "{topic}" item {iid}.'
    )


def mint_exercise_job(
    *,
    orch: Any,
    memory_repo: Any,
    item: Dict[str, Any],
    agent_id: str = "assistant",
    session_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Mint a standing Exercise Job via catalog resolve; stamp mastery pending_job_id."""
    item_id = str(item.get("item_id") or "").strip()
    if not item_id:
        return {"success": False, "error": "item_id_required"}
    if orch is None or not hasattr(orch, "create_job_from_catalog_resolve"):
        return {"success": False, "error": "no_orchestrator"}

    as_of = now or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)

    existing = memory_repo.get_education_mastery(item_id)
    if existing and (existing.get("pending_job_id") or "").strip():
        return {
            "success": True,
            "job_id": existing["pending_job_id"],
            "skipped": True,
            "reason": "already_pending",
            "item_id": item_id,
        }

    ensure_mastery_for_application(memory_repo, item)
    sid = session_id or f"edu-app-{uuid.uuid4().hex[:10]}"
    intent = build_exercise_job_intent(item)
    success_rule = (
        f"Education Application exercise verified for item {item_id} "
        f"topic={item.get('topic')}"
    )
    job = orch.create_job_from_catalog_resolve(
        intent=intent,
        session_id=sid,
        agent_id=agent_id,
        success_rule=success_rule,
        verify_checker=None,
    )
    jid = getattr(job, "id", None) or (job.get("id") if isinstance(job, dict) else None)
    if not jid:
        return {"success": False, "error": "job_mint_failed", "item_id": item_id}
    jid = str(jid)
    memory_repo.mark_education_mastery_resurfaced(
        item_id=item_id,
        job_id=jid,
        now=as_of,
    )
    return {
        "success": True,
        "job_id": jid,
        "session_id": sid,
        "item_id": item_id,
        "kind": APPLICATION_KIND,
        "intent": intent,
    }


def _fact_id(item_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (item_id or "")[:40])
    return f"edu_app_{safe}"


def write_application_memory_fact(
    repo: Any,
    *,
    item: Dict[str, Any],
    correct: bool,
    given: str,
    fail_action: str = "",
) -> Optional[str]:
    """Persist application outcome as a semantic fact in agent memory.db."""
    item_id = str(item.get("item_id") or "").strip()
    if not item_id:
        return None
    topic = str(item.get("topic") or "").strip() or "unknown"
    grade = "pass" if correct else "miss"
    snip = re.sub(r"\s+", " ", (given or "").strip())[:160]
    action = (fail_action or ("advance_mastery" if correct else "ledger_miss")).strip()
    value = (
        f"application item_id={item_id} topic={topic} grade={grade} "
        f"kind=exercise action={action} given={snip}"
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
                    (value, APPLICATION_CATEGORY, 1.0 if correct else 0.85, fid),
                )
            return fid
        except Exception:  # noqa: BLE001
            pass
    try:
        return repo.add_semantic_fact(
            entity=APPLICATION_ENTITY,
            attribute="application_outcome",
            value=value,
            category=APPLICATION_CATEGORY,
            confidence=1.0 if correct else 0.85,
            decay_half_life_days=90.0,
            fact_id=fid,
        )
    except Exception:  # noqa: BLE001
        try:
            repo.update_semantic_fact(
                fid,
                value=value,
                category=APPLICATION_CATEGORY,
                confidence=1.0 if correct else 0.85,
            )
        except Exception:  # noqa: BLE001
            return None
        return fid


def write_application_wiki_outcome(
    wiki_store: Any,
    *,
    wiki_path: str,
    item: Dict[str, Any],
    correct: bool,
    given: str,
    fail_action: str = "",
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Append application outcome under ## Application outcomes on the source Wiki note."""
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
    action = (fail_action or ("advance_mastery" if correct else "ledger_miss")).strip()
    chunk = (
        f"- [{stamp}] item_id={item.get('item_id')} grade={grade} action={action}\n"
        f"  Task: {prompt}\n"
        f"  Attempt: {snip or '(empty)'}\n"
    )
    try:
        result = wiki_store.append_note(path, chunk, heading="Application outcomes")
        if isinstance(result, dict):
            return result
        return {"success": True, "path": path}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc), "path": path}


def ensure_mastery_for_application(repo: Any, item: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert mastery row so application grades reuse the CARD-242 ledger."""
    item_id = str(item.get("item_id") or "").strip()
    if not item_id:
        raise ValueError("application item_id required")
    existing = repo.get_education_mastery(item_id)
    if existing:
        return existing
    concepts = item.get("required_concepts") or []
    expected = str(item.get("expected_answer") or "").strip()
    if not expected and concepts:
        expected = ", ".join(concepts)
    mid = repo.upsert_education_mastery(
        item_id=item_id,
        topic=str(item.get("topic") or item.get("wiki_path") or "Application"),
        wiki_path=str(item.get("wiki_path") or "00_Inbox/application.md"),
        prompt=str(item.get("prompt") or ""),
        expected_answer=expected,
        grade="unseen",
    )
    row = repo.get_education_mastery(mid)
    assert row is not None
    return row


def apply_application_fail_path(
    *,
    orch: Any = None,
    phase_id: Optional[str] = None,
    replan_count: int = 0,
    fail_facts: Optional[Sequence[str]] = None,
    memory_repo: Any = None,
    item: Optional[Dict[str, Any]] = None,
    agent_id: str = "assistant",
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Fail path: bounded replan or HITL park when Job/phase present; else mint resurface Job.

    Reuses CARD-232 primitives. Never silent advance.
    """
    facts = list(fail_facts or []) or ["application binary verify failed"]
    # Prefer live Job/phase fail path when available
    if orch is not None and phase_id:
        try:
            out = apply_bounded_replan_on_failed(
                orch,
                phase_id=phase_id,
                fail_facts=facts,
            )
            action = str(out.get("action") or "park")
            return {
                "action": action,
                "replan_count": out.get("replan_count", replan_count),
                "replan_exhausted": bool(out.get("replan_exhausted")),
                "needs_replan": bool(out.get("needs_replan")),
                "last_fail_reason": out.get("last_fail_reason") or facts[0],
                "max_replan_attempts": MAX_REPLAN_ATTEMPTS,
                "phase_id": phase_id,
                "details": out,
            }
        except Exception as exc:  # noqa: BLE001
            fallback = {
                "action": "park" if not should_auto_replan(replan_count) else "replan",
                "error": str(exc),
                "replan_count": replan_count,
                "phase_id": phase_id,
            }
            if (
                memory_repo is not None
                and item is not None
                and hasattr(orch, "create_job_from_catalog_resolve")
            ):
                minted = mint_exercise_job(
                    orch=orch,
                    memory_repo=memory_repo,
                    item=item,
                    agent_id=agent_id,
                    now=now,
                )
                fallback["resurface"] = minted
                if minted.get("success") and not minted.get("skipped"):
                    fallback["action"] = "resurface_job"
                    fallback["job_id"] = minted.get("job_id")
            return fallback

    # No phase: mint standing Exercise Job for resurface when orch present
    if orch is not None and memory_repo is not None and item is not None:
        minted = mint_exercise_job(
            orch=orch,
            memory_repo=memory_repo,
            item=item,
            agent_id=agent_id,
            now=now,
        )
        if minted.get("success"):
            return {
                "action": "resurface_job" if not minted.get("skipped") else "already_pending",
                "job_id": minted.get("job_id"),
                "replan_count": replan_count,
                "last_fail_reason": facts[0],
                "mint": minted,
            }

    # Pure ledger miss - retention Routine can resurface later
    return {
        "action": "ledger_miss",
        "replan_count": replan_count,
        "last_fail_reason": facts[0],
        "max_replan_attempts": MAX_REPLAN_ATTEMPTS,
        "hint": "retention_routine_can_resurface",
    }


def grade_and_record_application(
    *,
    repo: Any,
    item: Dict[str, Any],
    given: str,
    wiki_store: Any = None,
    orch: Any = None,
    phase_id: Optional[str] = None,
    replan_count: int = 0,
    agent_id: str = "assistant",
    now: Optional[datetime] = None,
    write_wiki: bool = True,
    write_memory: bool = True,
    mint_on_fail: bool = True,
) -> Dict[str, Any]:
    """Binary-grade Application attempt, update ledger, fail->park/replan, write-back.

    Pass advances mastery. Fail parks / replans (when Job phase present) or mints
    resurface Exercise Job / leaves ledger miss for retention.
    """
    reference = str(item.get("expected_answer") or "").strip() or None
    concepts = item.get("required_concepts") or []
    if isinstance(concepts, str):
        concepts = _parse_concepts(concepts)
    correct = grade_application_binary(
        given,
        reference=reference,
        required_concepts=concepts or None,
    )
    ensure_mastery_for_application(repo, item)
    row = repo.record_education_grade(
        item_id=str(item["item_id"]),
        correct=correct,
        now=now,
    )
    from src.application.education.analysis import record_error_and_metacog

    analysis = record_error_and_metacog(
        repo,
        item=row,
        given=given,
        correct=correct,
        required_concepts=item.get("required_concepts") or [],
        now=now,
        source="application",
    )

    if correct:
        fail_path: Dict[str, Any] = {"action": "advance_mastery"}
    else:
        fail_path = apply_application_fail_path(
            orch=orch if mint_on_fail or phase_id else None,
            phase_id=phase_id,
            replan_count=replan_count,
            fail_facts=[
                f"application binary verify failed for item {item.get('item_id')}"
            ],
            memory_repo=repo if mint_on_fail else None,
            item=item if mint_on_fail else None,
            agent_id=agent_id,
            now=now,
        )

    action = str(fail_path.get("action") or ("advance_mastery" if correct else "ledger_miss"))
    memory_fact_id = None
    if write_memory:
        memory_fact_id = write_application_memory_fact(
            repo,
            item=row,
            correct=correct,
            given=given,
            fail_action=action,
        )
    wiki_result: Dict[str, Any] = {"success": False, "skipped": True}
    if write_wiki and wiki_store is not None:
        wiki_result = write_application_wiki_outcome(
            wiki_store,
            wiki_path=str(item.get("wiki_path") or row.get("wiki_path") or ""),
            item=row,
            correct=correct,
            given=given,
            fail_action=action,
            now=now,
        )
    return {
        "correct": correct,
        "grade": row.get("grade"),
        "next_due": row.get("next_due"),
        "interval_stage": row.get("interval_stage"),
        "pass_count": row.get("pass_count"),
        "miss_count": row.get("miss_count"),
        "item": row,
        "grader": "binary_external_application",
        "analysis": analysis,
        "action": action,
        "fail_path": fail_path,
        "memory_fact_id": memory_fact_id,
        "wiki_writeback": wiki_result,
        "kind": APPLICATION_KIND,
    }


def build_application_ask_clause(items: List[Dict[str, Any]]) -> str:
    if not items:
        return (
            " No application exercises ready - teach normally without inventing "
            "LLM self-scored fluff. Prefer minting a standing Exercise Job when assigning work."
        )
    parts = []
    for it in items[:3]:
        iid = it.get("item_id") or ""
        topic = it.get("topic") or ""
        prompt = it.get("prompt") or ""
        parts.append(f'- item_id={iid} topic="{topic}" task="{prompt}"')
    joined = "\n".join(parts)
    return (
        " Assign these as **Application Exercise Jobs** (standing Job mint). "
        "Grade with binary external reference/concepts verify only - never LLM self-score:\n"
        f"{joined}\n"
        "On fail: bounded replan or HITL park (CARD-232) and update mastery; on pass: advance mastery."
    )
