# ADR-0011: Ephemeral Subprocess Sandboxing, Dangerous Command Guardrails, and HITL State Parking

## Status
Accepted

## Date
2026-08-23

## Context
Executing autonomous agent commands and tools carries risks:
1. Destructive system commands (e.g. `rm -rf /`, `mkfs`, raw database drops) could be invoked inadvertently.
2. Long-running or unbounded script executions could pollute the host filesystem.
3. Operators lack a mechanism to inspect, approve, or reject high-risk actions before execution occurs without killing the entire agent session context.

## Decision Drivers
- **Deterministic Blast-Radius Mitigation**: Run volatile filesystem tasks inside ephemeral scratch directories.
- **Safety Pre-Filtering**: Statically analyze shell commands against known high-risk destructive patterns.
- **Human-In-The-Loop (HITL) State Machine**: Park agent turn execution in SQLite when high-risk actions are proposed, await explicit operator decision (`APPROVED` / `REJECTED`), and resume without state loss.
- **Real-Time Cancellation**: Allow client connections to abort in-flight agent streaming loops immediately.

## Decision Outcome
Adopt a 3-layer safety architecture:
1. `DangerousCommandFilter`: Intercepts destructive Linux/Windows shell commands.
2. `SandboxedSubprocessWorker`: Runs commands inside isolated `tempfile.TemporaryDirectory` with strict timeouts.
3. `HITLApprovalEngine` & SQLite `pending_approvals`: Emits `APPROVAL_REQUIRED` event, persists execution state as `PAUSED_AWAITING_APPROVAL`, and provides resume endpoints.

## Consequences
- **Positive**: Zero risk of accidental system bricking; operator maintains sovereign control; turns can be safely resumed asynchronously.
- **Negative**: High-risk tool calls require manual operator intervention before completion.
