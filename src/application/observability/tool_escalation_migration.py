"""One-time rename of the pre-CARD-520 remedy name to ``tool_escalation`` [CARD-520 REQ-520-005, D2].

Rewrites, idempotently and by parsing JSON (never a text replace):
- ``skill_proposal`` chat messages whose JSON has the old key (Teach distill results);
- proposals whose payload has the old ``remedy_kind`` (friction recommendations);
- the same field in ``<data>/skills/_friction_recommendations.json``.
Malformed rows are left alone. Reader fallbacks stay for one release (removed by CARD-498).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.domain.observability.models import LEGACY_TOOL_ESCALATION, TOOL_ESCALATION

logger = logging.getLogger(__name__)


def _rename_key(data: Any) -> bool:
    if not isinstance(data, dict) or LEGACY_TOOL_ESCALATION not in data:
        return False
    old = data.pop(LEGACY_TOOL_ESCALATION)
    if data.get(TOOL_ESCALATION) is None:
        data[TOOL_ESCALATION] = old
    return True


def _rename_remedy(data: Any) -> bool:
    if isinstance(data, dict) and data.get("remedy_kind") == LEGACY_TOOL_ESCALATION:
        data["remedy_kind"] = TOOL_ESCALATION
        return True
    return False


def _migrate_db(store: Any) -> Dict[str, int]:
    counts = {"messages": 0, "proposals": 0}
    getter = getattr(store, "_get_connection", None)
    if not callable(getter):
        return counts
    conn = getter()
    like = f"%{LEGACY_TOOL_ESCALATION}%"
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, content FROM messages WHERE role = 'skill_proposal' AND content LIKE ?", (like,))
        for msg_id, content in cur.fetchall():
            try:
                data = json.loads(content)
            except (TypeError, ValueError):
                continue
            if _rename_key(data):
                conn.execute("UPDATE messages SET content = ? WHERE id = ?", (json.dumps(data), msg_id))
                counts["messages"] += 1
        cur.execute("SELECT id, payload_json FROM proposals WHERE payload_json LIKE ?", (like,))
        for prop_id, payload in cur.fetchall():
            try:
                data = json.loads(payload)
            except (TypeError, ValueError):
                continue
            if _rename_remedy(data):
                conn.execute("UPDATE proposals SET payload_json = ? WHERE id = ?", (json.dumps(data), prop_id))
                counts["proposals"] += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if getattr(store, "_mem_conn", None) is None:
            conn.close()
    return counts


def _migrate_ledger(data_dir: Optional[Union[str, Path]]) -> int:
    if not data_dir:
        return 0
    ledger = Path(data_dir) / "skills" / "_friction_recommendations.json"
    if not ledger.is_file():
        return 0
    try:
        recs = json.loads(ledger.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if not isinstance(recs, list):
        return 0
    changed = sum(1 for rec in recs if _rename_remedy(rec))
    if changed:
        ledger.write_text(json.dumps(recs, indent=2), encoding="utf-8")
    return changed


def migrate_tool_escalation_names(store: Any, data_dir: Optional[Union[str, Path]]) -> Dict[str, int]:
    """Rename stored old values to ``tool_escalation``. Returns rows/entries changed; 0s on the next run."""
    counts = _migrate_db(store)
    counts["ledger"] = _migrate_ledger(data_dir)
    if any(counts.values()):
        logger.info("CARD-520 tool_escalation migration changed %s", counts)
    else:
        logger.info("CARD-520 tool_escalation migration: nothing to change")
    return counts
