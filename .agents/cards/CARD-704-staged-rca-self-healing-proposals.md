---
id: CARD-704
title: "Staged RCA self-healing proposals on recurring tool or routine failures"
type: feature
status: Ready
priority: P3
milestone: M30
needs_decision: none
proof:
  journeys: [card-704-staged-rca-self-healing-proposals]
  checks: [tests/unit/telemetry/test_card704_staged_rca_proposals.py]
branch: feat/card-704-staged-rca-self-healing-proposals
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-17
---

# CARD-704 Staged RCA self-healing proposals on recurring tool or routine failures

## Intent
Adapted from `Crucible` (`ADR-0008`, `ADR-0014`, `src/agent_os/kernel/rca_stager.py`, `docs/architecture-comparison-crucible-agent-os.md` §2, §5 & §7.2): when a user tool, Agora skill tool, or routine fails repeatedly, AutoReiv should stage a structured Root Cause Analysis (RCA) proposal with telemetry evidence (trace IDs, error details, failure count) and a one-click "Repair in Chat" action that dispatches `AutoReiv` to inspect and fix the user tool via `update_user_tool` / `write_skill_file` — never silently mutating code in the background.

## Goal
Detect recurring tool or routine failures, stage structured RCA proposals (`GET /api/telemetry/rca-proposals`), and surface a "Repair in Chat" button that opens an `AutoReiv` chat pre-seeded with the failing tool's trace evidence and repair instructions.

## Change
- Add `RcaProposalService` that aggregates recurring tool and job/routine failures and stages structured RCA items (severity, failing capability, error detail, trace IDs, suggested remediation).
- Expose `GET /api/telemetry/rca-proposals` and `POST /api/telemetry/rca-proposals/{id}/dismiss`.
- Surface staged RCA proposals in Capabilities / Metrics with a one-click "Repair in Chat" action that launches `AutoReiv` to refactor and dry-run verify the fix.

## What dies
- Nothing.

## Proof
- Journey `card-704-staged-rca-self-healing-proposals`:
  1. Trigger a failing user tool call, verify a staged RCA proposal appears with the failure evidence and trace reference, click "Repair in Chat", and verify `AutoReiv` repairs the tool via `update_user_tool` on desktop and phone.
- Checks:
  - `tests/unit/telemetry/test_card704_staged_rca_proposals.py`

## Plan and decisions
- Approved by Jacob under `CARD-698` Option 2 (2026-10-17).

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
- Added staged RCA self-healing proposals for recurring tool and routine failures with one-click repair in Chat [CARD-704].
