---
id: CARD-701
title: "Live ApprovalMode in Settings UI with read_only and state_change tool effect tiers"
type: feature
status: Ready
priority: P2
milestone: M30
needs_decision: none
proof:
  journeys: [card-701-live-approval-mode-and-effect-tiers]
  checks: [tests/unit/architecture/test_card701_live_approval_mode.py]
branch: feat/card-701-live-approval-mode-and-effect-tiers
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-17
---

# CARD-701 Live ApprovalMode in Settings UI with read_only and state_change tool effect tiers

## Intent
Adapted from `Crucible` (`ADR-0015` §4.6, `docs/architecture-comparison-crucible-agent-os.md` §5 & §7.1): `CARD-691` added `AUTOREIV_APPROVAL_MODE` (`strict` vs `hands_off`) via environment variable. Operators should be able to switch `ApprovalMode` (`strict` / `balanced` / `hands_off`) live in Settings Studio without restarting the server, where `balanced` auto-mounts smoke-verified `read_only` tools and skills while gating `state_change` and `destructive` capabilities.

## Goal
Persist `approval_mode` (`strict`, `balanced`, `hands_off`) in live runtime settings (`DB > env > default`), surface it in Settings Studio, and enforce `read_only` vs `state_change`/`destructive` tool effect gating across tool authoring and execution.

## Change
- Extend runtime approval mode resolution (`strict`, `balanced`, `hands_off`) to read from persisted settings (`settings` table) with fallback to `AUTOREIV_APPROVAL_MODE` and `balanced`/`strict` default.
- In `balanced` mode, auto-enable newly authored/updated tools and skills whose AST/check classification is `read_only`, while holding `state_change` / outside-access tools for operator approval.
- Add the live Approval Mode selector in Settings Studio (`#view-settings`) and `GET/POST /api/settings/matrix`.

## What dies
- Env-only approval mode lookup that required a server restart to switch between `strict` and `hands_off`.

## Proof
- Journey `card-701-live-approval-mode-and-effect-tiers`:
  1. Switch Approval Mode in Settings Studio to `balanced`, verify a `read_only` tool auto-mounts while an outside-access (`state_change`) tool creates a pending approval, and verify switching to `hands_off` takes effect immediately without restart on desktop and phone.
- Checks:
  - `tests/unit/architecture/test_card701_live_approval_mode.py`

## Plan and decisions
- Approved by Jacob under `CARD-698` Option 2 (2026-10-17).

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
- Added live `ApprovalMode` (`strict` / `balanced` / `hands_off`) selector in Settings Studio with `read_only` vs `state_change` tool effect gating [CARD-701].
