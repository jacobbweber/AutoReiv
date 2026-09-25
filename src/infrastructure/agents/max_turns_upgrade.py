"""One-time agent turn-budget upgrade: stored max_turns 10 -> 50 [CARD-445].

Runs at startup after platform pack promotion (``install_platform_agent_packs``).
Only rows stored at exactly the legacy default are raised; every other value is an
operator choice and is kept. Completion is recorded under
``AGENT_MAX_TURNS_DEFAULT_50_SETTING`` so the upgrade never runs twice, even when
bootstrap runs twice (CARD-459) or an operator later saves 10 on purpose.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from src.domain.kernel.models import DEFAULT_AGENT_MAX_TURNS

logger = logging.getLogger(__name__)

AGENT_MAX_TURNS_DEFAULT_50_SETTING = "agent_max_turns_default_50_applied"
LEGACY_DEFAULT_AGENT_MAX_TURNS = 10


def apply_default_max_turns_upgrade(store: Any) -> Optional[dict[str, Any]]:
    """Raise legacy-default agents once and record it. Returns the record, or None if skipped."""
    if store is None or not hasattr(store, "raise_agent_max_turns") or not hasattr(store, "set_setting"):
        return None
    if store.get_setting(AGENT_MAX_TURNS_DEFAULT_50_SETTING) is not None:
        return None
    raised = store.raise_agent_max_turns(LEGACY_DEFAULT_AGENT_MAX_TURNS, DEFAULT_AGENT_MAX_TURNS)
    record = {
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "from": LEGACY_DEFAULT_AGENT_MAX_TURNS,
        "to": DEFAULT_AGENT_MAX_TURNS,
        "raised": raised,
    }
    store.set_setting(AGENT_MAX_TURNS_DEFAULT_50_SETTING, record)
    logger.info(
        "CARD-445: raised max_turns %s -> %s for %s",
        LEGACY_DEFAULT_AGENT_MAX_TURNS,
        DEFAULT_AGENT_MAX_TURNS,
        raised or "no agents",
    )
    return record
