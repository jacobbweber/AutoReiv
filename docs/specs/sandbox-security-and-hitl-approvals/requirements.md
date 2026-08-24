# Requirements Specification: Sandbox Security Guardrails & HITL Approvals

> **Spec Status**: Approved  
> **Target Release**: Milestone 10 (v0.10.0)  
> **Primary Component**: `AutoReiv.Safety` & `AutoReiv.Kernel`  
> **Applicable ADRs**: `docs/adr/0011-ephemeral-sandbox-dangerous-command-guardrails-and-hitl-state-parking.md`  
> **Linked Work Card**: `.github/cards/CARD-010-sandbox-security-guardrails-and-hitl-approvals.md`

---

## 1. Executive Summary & User Story
As a system operator supervising autonomous agent operations on my host or server,  
I want dangerous commands to be filtered and high-risk actions to park execution awaiting my explicit approval,  
So that destructive operations can never execute without authorization, scripts run in ephemeral sandboxes, and in-flight executions can be cancelled anytime.

---

## 2. EARS Functional Requirements

### `[REQ-SAFE-001]` Dangerous Command Pattern Analyzer
- **Event-driven**: WHEN a shell command is submitted to `SysadminSkill`, THE `DangerousCommandFilter` SHALL inspect the command against prohibited destructive regex patterns (`rm -rf /`, `dd`, `mkfs`, `fdisk`, `:(){ :|:& };:`, `drop database`, `format c:`) and reject it immediately if flagged.

### `[REQ-SAFE-002]` Ephemeral Temporary Directory Sandbox
- **Ubiquitous**: THE `SandboxedSubprocessWorker` SHALL execute file generation and shell scripts within an isolated `tempfile.TemporaryDirectory` with execution timeout limits and automated resource cleanup.

### `[REQ-SAFE-003]` High-Risk Tool Tagging & Approval Gating
- **State-driven**: WHILE evaluating tool calls, IF a tool is flagged with `is_high_risk=True` or triggers safety inspection, THE `AgentKernel` SHALL halt execution and transition the session into `PAUSED_AWAITING_APPROVAL`.

### `[REQ-SAFE-004]` SQLite Pending Approvals Store
- **Ubiquitous**: THE `SQLiteStateStore` SHALL maintain a `pending_approvals` table storing `(id, session_id, agent_id, tool_name, arguments_json, status, created_at, resolved_at)` tracking pending operator decisions.

### `[REQ-SAFE-005]` REST Approval & Rejection Workflow
- **Event-driven**: WHEN an operator calls `POST /api/approvals/{approval_id}/decision` with `APPROVED` or `REJECTED`, THE `HITLApprovalEngine` SHALL resolve the pending approval record and resume or terminate the paused turn.

### `[REQ-SAFE-006]` Real-Time Stream Abort & Cancellation
- **Event-driven**: WHEN a client sends a cancellation signal via `POST /api/chat/stream/{session_id}/abort`, THE streaming session loop SHALL immediately abort token generation and disconnect cleanly.
