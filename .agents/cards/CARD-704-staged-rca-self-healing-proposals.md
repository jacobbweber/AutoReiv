---
id: CARD-704
title: "Staged RCA self-healing proposals on recurring tool or routine failures"
type: feature
status: In Review
priority: P3
milestone: M30
needs_decision: none
proof:
  journeys: [card-704-staged-rca-self-healing-proposals]
  checks: [tests/unit/telemetry/test_card704_staged_rca_proposals.py]
branch: feat/card-704-staged-rca-self-healing-proposals
log: {minutes: 23, qa_runs: 1, findings: 0}
created: 2026-10-17
---

# CARD-704 Staged RCA self-healing proposals on recurring tool or routine failures

## Intent
Adapted from `Crucible` (`ADR-0008`, `ADR-0014`, `src/agent_os/kernel/rca_stager.py`, `docs/architecture-comparison-crucible-agent-os.md` §2, §5 & §7.2): when a user tool, Agora skill tool, or routine fails repeatedly, AutoReiv should stage a structured Root Cause Analysis (RCA) proposal with telemetry evidence (trace IDs, error details, failure count) and a one-click "Repair in Chat" action that dispatches `AutoReiv` to inspect and fix the user tool via `update_user_tool` / `write_skill_file` — never silently mutating code in the background.

## Goal
Detect recurring tool or routine failures, stage structured RCA proposals (`GET /api/telemetry/rca-proposals`), and surface a "Repair in Chat" button that opens an `AutoReiv` chat pre-seeded with the failing tool's trace evidence and repair instructions.

## Change
- Add `RcaProposalService` (`src/application/telemetry/rca_proposals.py`) that aggregates recurring tool and job/routine failures and stages structured RCA items (`id`, `severity`, `kind`, `target_name`, `skill_id`, `file_path`, `failure_count`, `latest_error`, `trace_ids`, `suggested_remediation`, `repair_prompt`), and auto-resolves proposals when a newer execution succeeds or `save_skill_file` saves a verified repair.
- Expose `GET /api/telemetry/rca-proposals` and `POST /api/telemetry/rca-proposals/{id}/dismiss` in `src/web/routers/observability.py`.
- Surface staged RCA proposals in Capabilities Studio (`#capabilitiesRcaProposalsPanel` / `src/web/static/modules/studios/rca_proposals_panel.js`) with a one-click "Repair in Chat" action (`[data-rca-repair]`) that opens a new `AutoReiv` chat session and dispatches the repair prompt, plus a "Dismiss" action (`[data-rca-dismiss]`).

## What dies
- Nothing.

## Proof
- Journey `card-704-staged-rca-self-healing-proposals`:
  1. Trigger a failing user tool call, verify a staged RCA proposal appears with the failure evidence and trace reference, click "Repair in Chat", and verify `AutoReiv` repairs the tool via `write_skill_file` on desktop and phone.
- Checks:
  - `tests/unit/telemetry/test_card704_staged_rca_proposals.py`
  - `tests/unit/frontend/card_704_rca_proposals_panel.test.js`

## Plan and decisions
- Approved by Jacob under `CARD-698` Option 2 (2026-10-17).

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-704-staged-rca-self-healing-proposals` | desktop | PASS | Staged `rca:tool:calc_ratio_desktop` with trace `0d3f496a-1d78-41b0-89b1-4c5c4a144dd4` and `ZeroDivisionError`; rendered in `#view-capabilities`; "Repair in Chat" launched `AutoReiv` which repaired `qa-rca-desktop/tools/calc_ratio_desktop.py` via `write_skill_file` and resolved the proposal |
| `card-704-staged-rca-self-healing-proposals` | phone | PASS | Staged `rca:tool:calc_ratio_phone` with trace `7a32bc5f-4ebb-48a3-b454-035440797c0c` and `ZeroDivisionError`; rendered in `#view-capabilities` with zero horizontal overflow (`390 <= 390`); "Repair in Chat" launched `AutoReiv` which repaired `qa-rca-phone/tools/calc_ratio_phone.py` via `write_skill_file` and resolved the proposal |

Screenshots:
- `/tmp/autoreiv-qa/card-704/card-704-staged-rca-self-healing-proposals-desktop-02-open-capabilities-studio-and-verify-staged-rca-p.png`
- `/tmp/autoreiv-qa/card-704/card-704-staged-rca-self-healing-proposals-desktop-03-click-repair-in-chat-and-verify-autoreiv-repairs.png`
- `/tmp/autoreiv-qa/card-704/card-704-staged-rca-self-healing-proposals-phone-02-open-capabilities-studio-and-verify-staged-rca-p.png`

## Release note
- Added staged RCA self-healing proposals for recurring tool and routine failures with one-click repair in Chat [CARD-704].
