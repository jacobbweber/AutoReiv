"""Friction recommendation identity and dedup rules [CARD-525].

One recommendation per (agent, tool, friction type). A pending or escalated one blocks a new one; a
dismissed or applied one blocks only for a cool-down, so a problem that comes back is raised again.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping, Optional, Tuple

ESCALATE_RE = re.compile(r"Escalate (\S+) to")
BYTES_RE = re.compile(r"\((\d+) bytes\)")

DEFAULT_COOLDOWN_DAYS = 7
BLOCKING_STATUSES = frozenset({"pending", "escalated"})
COOLDOWN_STATUSES = frozenset({"dismissed", "applied"})


def normalize_friction_rec(data: Dict[str, Any]) -> Dict[str, Any]:
    """Records without tool_name/payload_bytes get them derived from the text [CARD-520 REQ-520-004]."""
    text = f"{data.get('summary') or ''} {data.get('proposed_patch') or ''}"
    if not data.get("tool_name"):
        m = ESCALATE_RE.search(text)
        if m:
            data["tool_name"] = m.group(1)
    if not data.get("payload_bytes"):
        m = BYTES_RE.search(text)
        if m:
            data["payload_bytes"] = int(m.group(1))
    return data


def recommendation_status(proposal_status: Any, payload_status: Any = None) -> str:
    """Card status from the proposal row: draft=pending, approved=applied/escalated, rejected=dismissed."""
    value = str(getattr(proposal_status, "value", proposal_status) or "").strip().lower()
    if value == "approved":
        return "escalated" if str(payload_status or "") == "escalated" else "applied"
    if value == "rejected":
        return "dismissed"
    return "pending"


def friction_key(data: Mapping[str, Any]) -> Tuple[str, str, str]:
    """(agent_id, tool, friction_type). The tool name is the identity; old records fall back to the skill."""
    friction = data.get("friction_type")
    friction = str(getattr(friction, "value", friction) or "")
    tool = str(data.get("tool_name") or "").strip()
    if not tool and data.get("skill_path"):
        tool = f"skill:{data.get('skill_path')}"
    return str(data.get("agent_id") or ""), tool, friction


def blocks_new_recommendation(
    status: str,
    decided_at: Optional[datetime],
    *,
    now: Optional[datetime] = None,
    cooldown_days: float = DEFAULT_COOLDOWN_DAYS,
) -> bool:
    """Pending/escalated block; dismissed/applied block until ``cooldown_days`` after the decision."""
    if status in BLOCKING_STATUSES:
        return True
    if status not in COOLDOWN_STATUSES:
        return False
    if decided_at is None:
        return True
    current = now or datetime.now(timezone.utc)
    when = decided_at if decided_at.tzinfo else decided_at.replace(tzinfo=timezone.utc)
    return current - when < timedelta(days=float(cooldown_days))
