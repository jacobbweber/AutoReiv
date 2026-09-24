"""Education Studio active topic/course selection (Projects Studio parallel) [CARD-447].

Persists the operator-selected education context in the durable settings store
(same pattern as ``selected_project`` for Projects Studio → Developer).
Tutor education-mode / Study entry reads this so coaching is grounded on the
Studio-saved topic/course.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

SELECTED_EDUCATION_CONTEXT_KEY = "selected_education_context"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_selected_education_context(store: Any) -> Dict[str, Any]:
    """Return the durable Studio-active education context, or ``{}`` if unset."""
    if store is None or not hasattr(store, "get_setting"):
        return {}
    raw = store.get_setting(SELECTED_EDUCATION_CONTEXT_KEY)
    if not isinstance(raw, dict):
        return {}
    topic = str(raw.get("topic") or "").strip()
    if not topic:
        return {}
    return {
        "topic": topic,
        "course_id": str(raw.get("course_id") or "").strip(),
        "agent_id": str(raw.get("agent_id") or "tutor").strip() or "tutor",
        "updated_at": str(raw.get("updated_at") or "").strip(),
        "source": str(raw.get("source") or "education_studio").strip() or "education_studio",
    }


def set_selected_education_context(
    store: Any,
    *,
    topic: Optional[str] = None,
    course_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    clear: bool = False,
    source: str = "education_studio",
) -> Dict[str, Any]:
    """
    Persist or clear the Studio-active education context.

    Returns ``{"success": True, "selected": {...}}``. Clearing yields empty selected.
    Empty topic (when not clearing) fails with ``success=False``.
    """
    if store is None or not hasattr(store, "set_setting"):
        return {"success": False, "error": "settings store unavailable", "selected": {}}

    if clear:
        store.set_setting(SELECTED_EDUCATION_CONTEXT_KEY, {})
        return {"success": True, "selected": {}}

    clean_topic = str(topic or "").strip()
    if not clean_topic:
        return {
            "success": False,
            "error": "topic is required",
            "selected": get_selected_education_context(store),
        }

    payload = {
        "topic": clean_topic,
        "course_id": str(course_id or "").strip(),
        "agent_id": str(agent_id or "tutor").strip() or "tutor",
        "updated_at": _now_iso(),
        "source": str(source or "education_studio").strip() or "education_studio",
    }
    store.set_setting(SELECTED_EDUCATION_CONTEXT_KEY, payload)
    return {"success": True, "selected": payload}
