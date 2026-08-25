"""
Approval Manager — HITL State Parking & Resume Engine [REQ-HITL-002].
Queues pending agent actions for human review and resolves asyncio futures
when a decision is submitted via the REST API.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from src.domain.hitl.models import ApprovalDecision, ApprovalStatus, PendingAction

logger = logging.getLogger(__name__)


class ApprovalManager:
    """
    In-memory HITL approval queue [REQ-HITL-002].

    When an agent action requires human approval, the kernel calls
    ``park_action`` which creates a ``PendingAction``, stores an
    ``asyncio.Future``, and returns both. The agent turn ``await``s
    the future. When the human submits a decision via REST, ``decide``
    resolves the future so the agent can resume or abort.
    """

    def __init__(self) -> None:
        self._pending: Dict[str, PendingAction] = {}
        self._futures: Dict[str, asyncio.Future] = {}
        self._decisions: Dict[str, ApprovalDecision] = {}

    def park_action(
        self,
        description: str,
        risk_level: str,
        agent_id: str,
        session_id: str,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
    ) -> Tuple[PendingAction, "asyncio.Future[ApprovalDecision]"]:
        """
        Park an action for human approval [REQ-HITL-002].

        Returns the ``PendingAction`` and an ``asyncio.Future`` that
        resolves when ``decide()`` is called for this action.
        """
        action = PendingAction(
            description=description,
            risk_level=risk_level,
            agent_id=agent_id,
            session_id=session_id,
            tool_name=tool_name,
            tool_args=tool_args,
        )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        future: asyncio.Future[ApprovalDecision] = loop.create_future()

        self._pending[action.action_id] = action
        self._futures[action.action_id] = future

        logger.info(
            "HITL: Parked action %s for agent %s — %s (risk=%s)",
            action.action_id,
            agent_id,
            description,
            risk_level,
        )

        return action, future

    def decide(
        self,
        action_id: str,
        status: ApprovalStatus,
        reason: Optional[str] = None,
    ) -> ApprovalDecision:
        """
        Resolve a parked action with a human decision [REQ-HITL-002].

        Raises ``KeyError`` if action_id is not found in the pending queue.
        """
        if action_id not in self._pending:
            raise KeyError(f"No pending action with id '{action_id}'.")

        action = self._pending.pop(action_id)
        action.status = status

        decision = ApprovalDecision(
            action_id=action_id,
            status=status,
            decided_at=time.time(),
            reason=reason,
        )

        self._decisions[action_id] = decision

        future = self._futures.pop(action_id, None)
        if future and not future.done():
            future.set_result(decision)

        logger.info(
            "HITL: Action %s decided as %s — %s",
            action_id,
            status.value,
            reason or "(no reason)",
        )

        return decision

    def list_pending(self) -> List[PendingAction]:
        """Return all actions currently awaiting human approval."""
        return list(self._pending.values())

    def get_action(self, action_id: str) -> Optional[PendingAction]:
        """Retrieve a specific pending action by ID."""
        return self._pending.get(action_id)
