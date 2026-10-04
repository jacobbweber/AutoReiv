---
id: CARD-545
title: "Native tools declare risk at registration (ADR-0061 D11, full)"
status: Done
completed: 2026-10-04
created: 2026-09-26
branch: feat/card-525-527-545-friction-dedup-builtin-native-risk
related:
  - CARD-539
labels:
  - type:feature
  - area:tools
  - P3
needs_decision: none
milestone: M25
---

# [CARD-545] Native tools declare risk at registration (ADR-0061 D11, full)

> **Status**: Done (2026-10-04, merged to qa from `feat/card-525-527-545-friction-dedup-builtin-native-risk`). Filed from CARD-539, 2026-09-26.
> **Related**: CARD-539 (ADR-0061)
> **Labels**: `type:feature`, `area:tools`, `P3`

## Why

CARD-539 took D11 as recommended but kept the existing policy for tools with no declared risk. A read-only tool such as `get_weather` built by the Developer therefore asks for approval on every call (live QA: `approval_required` on the first call).

## Change

`register_native_tool` records `risk` (read_only / write / network / destructive); read-only tools run without confirmation, others default to `require_confirm`; operator `tool_policy` still overrides. Generated skills copy the tool's risk into frontmatter.

## Done when

A read-only native tool runs without an approval card; a write tool still asks; unit tests cover both.

## Built (2026-10-04)
- `register_native_tool` (agent tool) and `POST /api/tools/native` take `risk`: `read_only`, `write`, `network` or `destructive`. Anything else is refused, and so is `read_only` with `risk_level: high`. The record stores it, and the tool mounts with it, so ToolPolicyGate asks for write, network and destructive tools (`declared_risk`) and lets read-only ones run.
- `requires_hitl` now defaults from the risk: read_only does not ask; everything else, including tools with no declared risk, asks as before. Destructive always asks.
- Jacob's `tool_policy` still wins. The service records which `require_confirm_tools` entries it added (`native_managed_confirm_tools`) and never removes one he added; `safe_tools` still allows.
- A new skill made for the tool when an attach proposal is accepted copies the risk into frontmatter `safety` (`read_only`, `requires_hitl`). Tools Studio shows the declared risk on each runtime-built tool row.

## Plan and decisions
- D1 (security, taken): Jacob's approval hash covers only the code, so an agent could re-save an approved tool's same code as `read_only` and drop confirmation without review. Re-saving an **enabled** tool so it asks less often (now read_only, or requires_hitl turned off) disables it until Jacob enables it again, and the message says so. Tightening keeps it enabled.

## Results
| Check | Result | Notes |
|---|---|---|
| Unit: read-only runs (gate ALLOW), write/network ask, undeclared/destructive ask, invalid refused, operator override, relax re-approval, tighten stays, frontmatter, delete, schemas | PASS | `tests/unit/tools/test_card545_native_tool_risk.py` (11) |
| Vitest: Tools Studio risk text | PASS | `tests/unit/frontend/card545_runtime_tool_risk.test.js` (3) |
| Live :8770: register (real sandbox check) | PASS | `c545_weather` read_only -> requires_hitl false, not in require_confirm; `c545_note_save` write -> requires_hitl true, in require_confirm (managed) |
| Live: enable + invoke through the kernel gate (approval_mode ask) | PASS | read-only ran, no approval (`ran: true, parked: false`, output Paris 18 C); write parked `approval_required:appr_32445ec68ff0` |
| Live: re-save the enabled write tool as read_only | PASS | approval disabled, "It no longer asks before each call, so Jacob must enable it again"; managed policy entry removed; invoke 409 |
| Live: accepted skills | PASS | `c545-weather` safety read_only true / requires_hitl false; `c545-note-save` false / true |
| Screenshots | PASS | `autoreiv-qa\ui1003l\545-tools-studio-risk-before-*.png` (write asks / read-only runs), `545-tools-studio-risk-after-*.png` (re-saved tool back to Enable) |
| Live chat, Spark Nemotron (fresh session each) | PASS | "Use the c545_weather tool ... Paris": tool card `c545_weather` Complete, reply "The current temperature in Paris is 18°C.", no approval card, nothing pending. "Use the c545_note_save tool to save the note ""buy milk""": `c545_note_save` Waiting for approval, card with Approve/Reject, `GET /api/approvals/pending` has only `appr_9e7f784c8afa` (c545_note_save, text "buy milk"). Screenshots `545-chat-weather-{desktop,phone}.png`, `545-chat-note-{desktop,phone}.png` |

The rows above used the API and UI with no model call (Spark Nemotron returned no token between 12:52 and 1:11 AM ET on 2026-10-04). The live chat row below used Spark Nemotron (`nemotron-3.5-lightning`), set on :8770 from the start, at 3:30 PM ET the same day.

## Findings
- Seen, not filed: the approval card lists the internal `_tool_call_id` with the tool arguments. This is in the shared approval card and was not changed by this card.

## Release note
A tool the Developer builds now declares what it does. A read-only tool runs without asking once you enable it; tools that write, send data out or delete still ask before each call. Your tool policy still overrides.

Full suite on `9d13b9ae`: pytest 2502 passed / 12 skipped; preflight GREEN (vitest 1052, smoke 83/83).
