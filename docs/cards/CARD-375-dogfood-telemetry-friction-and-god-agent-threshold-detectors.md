# [CARD-375] Dogfood Telemetry Friction and God Agent Threshold Detectors

> **Status**: Ready  
> **Created**: 2026-09-19  
> **Spec Reference**: none  
> **Labels**: `type:dogfooding`, `observability`, `architecture`, `adr-0054`, `verification`

---

## 1. Why / Intent
Dogfood and live-validate the God-Agent threshold monitoring and architectural proposal system (ADR-0054, CARD-364, CARD-365). Verify that high-entropy sessions (tool bloat $> 8$ tools, context tax $> 4000$ chars, security boundary collisions, lifecycle mismatches) are reliably detected from telemetry, synthesized into actionable proposals in the durable ledger, surfaced in Agent Studio's Architectural Inbox, and safely executed via one-click remediation.

---

## 2. Three Beats

### Beat 1: What Jacob Means
When an agent or routine drifts toward becoming an unmaintainable "God Agent" by accumulating too many tools, overwhelming the prompt context, or executing repetitive polling loops in chat, the system must detect this architectural friction. Jacob wants proof that the detector flags real high-entropy sessions and generates clear, actionable remedies (such as routine promotion or tool pruning) that can be applied with one click.

### Beat 2: What AutoReiv Does Now
- CARD-364 and CARD-365 introduced the `ArchitecturalThresholdDetector`, evaluator service, and proposal engine backed by `$DATA_DIR/telemetry/architectural_proposals.json`.
- While unit tests verify threshold calculation with synthetic data structures, we have not dogfooded the complete end-to-end loop: capturing friction spans $\rightarrow$ executing the scan API $\rightarrow$ generating proposals $\rightarrow$ applying the remedy (such as registering a new scheduled routine in SQLite) $\rightarrow$ verifying that the proposal ledger and database state stay coherent.

### Beat 3: What Will Change
- Author an automated end-to-end dogfooding test suite (`tests/integration/observability/test_dogfood_architectural_governance.py`).
- Seed realistic telemetry spans demonstrating tool bloat ($>8$ tools) and lifecycle mismatch ($>5$ polling turns in a chat session).
- Execute `POST /api/observability/architectural/scan` and assert that typed alerts are generated and deduplicated.
- Trigger proposal generation via `POST /api/observability/architectural/proposals/generate`.
- Call `POST /api/observability/architectural/proposals/{id}/apply` and verify that the remedy executes cleanly (e.g. creating the routine in SQLite).

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Telemetry sessions exceeding threshold limits generate typed `ArchitecturalAlert` items (`TOOL_BLOAT`, `LIFECYCLE_MISMATCH`, etc.).
- [ ] Scans deduplicate alerts across identical sessions and store them in the durable ledger.
- [ ] Proposal generator synthesizes concrete `ArchitecturalProposal` items with valid remedy parameters.
- [ ] Applying a proposal executes the remedy (e.g. routine registration) and marks the proposal `applied`.
- [ ] Dismissing a proposal updates its status to `dismissed` without mutating state.
- [ ] Automated regression tests pass via `pytest tests/integration/observability/test_dogfood_architectural_governance.py`.
- [ ] Zero lint errors via `ruff check src tests`.
- [ ] All 7 preflight gates pass cleanly.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Ledger files must remain strictly under user data directories.
- Single isolated `feat/card-375-dogfood-architectural-governance` branch cut from `qa` upon Jacob's `build` approval.
