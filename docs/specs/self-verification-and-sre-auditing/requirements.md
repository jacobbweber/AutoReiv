# Requirements Specification: Self-Verification Loops & SRE Health Auditing

> **Spec Status**: Ready for Review  
> **Target Release**: Milestone 13 (v1.1.0)  
> **Primary Component**: `AutoReiv.Kernel` & `AutoReiv.Verification`  
> **Applicable ADRs**: `docs/adr/0014-reflexive-self-verification-loops-and-sre-critic-auditing.md`  
> **Linked Work Card**: `.github/cards/CARD-013-self-verification-loops-and-sre-health-auditing.md`

---

## 1. Executive Summary & User Story
As an operator relying on AutoReiv for critical system diagnostics,  
I want agents to programmatically self-verify their outputs, evaluate assertions, and autonomously self-correct through reflexive critique loops,  
So that high-stakes diagnostics and mutations are guaranteed accurate, consistent, and hallucination-free.

---

## 2. EARS Functional Requirements

### `[REQ-VERIFY-001]` Deterministic Verification Tool & Assertions
- **Ubiquitous**: THE `VerificationSkill` SHALL expose verification tools (`verify_telemetry_consistency`, `assert_json_schema`, `validate_metric_bounds`) that execute deterministic programmatic assertions and return pass/fail statuses with exact discrepancy diagnostics.

### `[REQ-VERIFY-002]` Reflexion State Machine & Loop Engine
- **Event-driven**: WHEN an agent turn operates with `require_verification=True` AND verification assertions fail, THE `ReflexionLoopEngine` SHALL feed the structured error critique back into the agent's context and execute a refinement iteration (up to `max_refinements=3`).

### `[REQ-VERIFY-003]` Kernel Verified Turn API
- **State-driven**: WHILE executing `kernel.run_verified_turn` or `kernel.stream_verified_turn`, THE `AgentKernel` SHALL enforce the Reflexion verification cycle, emitting `VERIFICATION_START` and `VERIFICATION_RESULT` events.

### `[REQ-VERIFY-004]` SRE Health Self-Auditing Protocol
- **Event-driven**: WHEN the `system-agent` executes a platform health inspection or hourly routine, THE agent SHALL invoke `verify_telemetry_consistency` to validate that health scores and error rates match SQLite database ground truth before final output.

### `[REQ-VERIFY-005]` Independent Critic Agent Profile (`auditor-critic`)
- **Ubiquitous**: THE `BuiltinAgentRegistry` SHALL register an `auditor-critic` agent profile specialized in zero-shot adversarial review, schema enforcement, and assumption challenging.

### `[REQ-VERIFY-006]` REST Verified Execution & Audit Endpoint
- **Event-driven**: WHEN a client calls `POST /api/chat/verified` OR `POST /api/agents/audit`, THE platform SHALL execute the request with reflexive verification and return the audit trace.
