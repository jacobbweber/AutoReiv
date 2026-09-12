"""CARD-270: gap↔ATF job linking and honest status transitions."""
from __future__ import annotations

from typing import Any, Optional, Sequence

GAP_META_PREFIX = "gap_id="

# Operator-visible statuses (anti-theatre)
GAP_PENDING = "pending"
GAP_TRAINING = "training"
GAP_TRAINED = "trained"
GAP_CANT = "cant"
GAP_FAILED = "failed"
GAP_DISMISSED = "dismissed"

ALLOWED_GAP_STATUSES = frozenset(
    {GAP_PENDING, GAP_TRAINING, GAP_TRAINED, GAP_CANT, GAP_FAILED, GAP_DISMISSED}
)


def encode_gap_id_objective(gap_id: str) -> str:
    gid = (gap_id or "").strip()
    if not gid:
        raise ValueError("gap_id required")
    return f"{GAP_META_PREFIX}{gid}"


def gap_id_from_objectives(objectives: Optional[Sequence[str]]) -> Optional[str]:
    for item in objectives or ():
        text = str(item or "").strip()
        if text.startswith(GAP_META_PREFIX):
            gid = text[len(GAP_META_PREFIX) :].strip()
            if gid:
                return gid
    return None


def gap_id_from_job(job: Any) -> Optional[str]:
    if job is None:
        return None
    objectives = getattr(job, "objectives", None)
    found = gap_id_from_objectives(objectives)
    if found:
        return found
    # Fallback: seed_intent may carry "gap_id=..." line from older callers
    seed = str(getattr(job, "seed_intent", "") or "")
    for line in seed.splitlines():
        line = line.strip()
        if line.startswith(GAP_META_PREFIX):
            gid = line[len(GAP_META_PREFIX) :].strip()
            if gid:
                return gid
    return None
