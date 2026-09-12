"""Education Retrieval + Retention Routine -> standing Job mint [CARD-242].

When mastery ledger items are due (1-3-7-30), this routine fires and mints a
standing Job for each due review. Chat toast / remind-me-later is NOT Done.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.application.education.quiz_engine import build_review_job_intent
from src.domain.routines.models import Routine

EDUCATION_RETENTION_ROUTINE_ID = "education-retrieval-retention"


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_education_retention(
    *,
    memory_repo: Any,
    orch: Any = None,
    routine: Optional[Routine] = None,
    agent_id: str = "assistant",
    session_id: Optional[str] = None,
    now: Optional[datetime] = None,
    max_items: int = 5,
) -> Dict[str, Any]:
    """List due mastery items and mint standing Jobs via catalog resolve.

    Returns dict with status, due_count, minted_job_ids. Skips items that already
    have a pending_job_id so the scheduler tick cannot spam Jobs.
    """
    as_of = now or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)

    due = list(memory_repo.list_due_education_mastery(as_of=as_of) or [])
    # Skip already-resurfaced pending jobs
    actionable = [r for r in due if not (r.get("pending_job_id") or "").strip()]
    actionable = actionable[: max(1, int(max_items))]

    if not actionable:
        return {
            "status": "ok",
            "due_count": 0,
            "minted_job_ids": [],
            "reason": "nothing_due" if not due else "all_pending",
        }

    if orch is None or not hasattr(orch, "create_job_from_catalog_resolve"):
        return {
            "status": "failed",
            "due_count": len(actionable),
            "minted_job_ids": [],
            "reason": "no_orchestrator",
        }

    sid = session_id or f"edu-retention-{uuid.uuid4().hex[:10]}"
    minted: List[str] = []
    details: List[Dict[str, Any]] = []

    for item in actionable:
        intent = build_review_job_intent(item)
        success_rule = (
            f"Education review resurfaced for item {item.get('item_id')} "
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
            continue
        jid = str(jid)
        memory_repo.mark_education_mastery_resurfaced(
            item_id=item["item_id"],
            job_id=jid,
            now=as_of,
        )
        minted.append(jid)
        details.append({"item_id": item["item_id"], "job_id": jid})

    if routine is not None:
        meta = dict(routine.metadata or {})
        meta["last_retention_at"] = _iso(as_of)
        meta["last_minted_job_ids"] = list(minted)
        meta["last_retention_details"] = details
        routine.metadata = meta

    return {
        "status": "ok",
        "due_count": len(actionable),
        "minted_job_ids": minted,
        "details": details,
        "session_id": sid,
    }


def job_output_text(result: Dict[str, Any]) -> str:
    return json.dumps(
        {
            "status": result.get("status"),
            "due_count": result.get("due_count"),
            "minted_job_ids": result.get("minted_job_ids") or [],
            "reason": result.get("reason"),
        },
        indent=2,
    )
