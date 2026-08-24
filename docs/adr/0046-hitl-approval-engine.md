# ADR-0046: Human-In-The-Loop (HITL) Interactive State Parking, Action Approval & Resume Engine

## Context
Autonomous agents executing tool invocations can trigger destructive or irreversible operations. While CARD-045 introduced deterministic guardrails that block clearly dangerous commands, a class of ambiguous or medium-risk actions benefit from human judgment before execution. The system needs a mechanism to pause agent execution, present the pending action to a human operator, and resume or abort based on explicit approval.

## Decision
1. **Domain HITL Models**:
   - Introduced `ApprovalStatus` (`PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`), `PendingAction`, and `ApprovalDecision` domain models.
2. **Approval Manager with asyncio Future Suspension**:
   - `ApprovalManager.park_action` creates a `PendingAction`, stores an `asyncio.Future`, and returns both. The calling agent turn `await`s the future, effectively parking execution.
   - `ApprovalManager.decide` resolves the future with the human's decision, resuming the agent turn.
3. **REST API Surface**:
   - `GET /api/hitl/pending` lists all parked actions.
   - `POST /api/hitl/decide` submits an approval or rejection.

## Status
Accepted

## Consequences
- **Positive**: Human operators retain final authority over ambiguous or high-risk agent actions with zero-latency resume on approval.
- **Negative**: In-memory queue is ephemeral; pending actions are lost on server restart. Durable persistence can be added in a future milestone if needed.
