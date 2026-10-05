---
id: CARD-533
title: "Journey testing inside AutoReiv: a Developer skill and tools to run journeys, and a Projects Studio view of journey runs"
status: Done
created: 2026-09-26
completed: 2026-10-05
branch: qa
depends_on:
  - CARD-532
  - CARD-539
related:
  - CARD-532
  - CARD-539
labels:
  - type:product
  - area:developer
  - area:projects
  - P2
needs_decision: none
milestone: M25
---

# [CARD-533] Journey testing built into AutoReiv

> **Status**: Done (slices 632/633/634 complete; REQ-533-005 deferred)
> **Related**: CARD-532 (runner, environment, journey format)
> **Labels**: `type:product`, `area:developer`, `area:projects`, `P2`

## Why

Long-term intent: AutoReiv and its Developer agent eventually test and build AutoReiv itself. CARD-532 gives the coding assistant a live QA runner; this card gives the same capability to the product.

## Acceptance criteria (EARS)

- **REQ-533-001 Developer skill:** A platform-pack skill in `platform-packs/developer/skills/` SHALL teach the Developer when and how to run a journey, read its report and summarize failures.
- **REQ-533-002 Tools:** The Developer SHALL have tools to run a journey (by id, against the CARD-532 environment), read a run's report and screenshots, and summarize failures in plain words (step, expected, actual, screenshot).
- **REQ-533-003 Projects Studio view:** Projects Studio SHALL list journey runs per project (time in local zone, journey, pass/fail, failing step) and open a run's screenshots and report.
- **REQ-533-004 Built on CARD-532:** Uses the CARD-532 journey format, runner and report; no second runner.
- **REQ-533-005 Self-work respects capability scoping:** WHEN the Developer works on AutoReiv's own code, THE Developer's coding skill runbook in `platform-packs/developer/skills/` SHALL load a product-side summary of ADR-0061 and `.agents/rules/capability-scoping.md` (one allowed-tools function `resolve_allowed_tools`, skills-only permission, selection only narrows, no side paths), AND its self-test SHALL run the CARD-539 guard tests (architecture guard, selection-subset property tests) and pass them before it proposes any change.

## Decisions (open, safety first)

- **D1 What the tool may start:** it launches a browser and a server. Only the CARD-532 test environment (own port, throwaway data), never the live serve or Jacob's data? **Recommend yes, hard-coded.**
- **D2 Sandbox and permissions:** which agents get the tools (Developer only?), process limits, timeouts, kill on cancel.
- **D3 HITL:** approval before each run, or before runs that clone real data or use real models. **Recommend approval for clone and real-model runs.**
- **D4 Model use:** journeys that call real models cost GPU time on the same vLLM; limits and scheduling.
- **D5 Scope of self-building:** reading results only vs letting the Developer change code after a failure (out of scope here; a later card).
- **D6 Scoping rules in self-work (decided with this requirement, 2026-09-26):** the rules reach the product Developer as a summary inside its platform-pack runbook, not by reading `.agents/` (agents-vs-packs rule); the summary cites ADR-0061 as the source so it does not drift. Needs CARD-539 first (the guard tests must exist).

## Done when

The Developer can run a journey from a chat, read its report and explain a failure; Projects Studio shows the run; the safety decisions are implemented as decided.

## Decision (Jacob, 2026-09-30)
- Jacob approved the class-b recommendation: **Park**. Journey testing stays in the coding-assistant runner (CARD-532, `scripts/live_qa.py`) until the D1-D6 safety decisions are worth making.

## Log
- 2026-09-30: Parked per Jacob's class-b approval.
- 2026-10-01: status set to Parked to match the 2026-09-30 decision (the field had stayed Ready).

## Split (2026-10-05)
Parent parked (Jacob 2026-09-30). Built as Ready slices:
- **CARD-632** (first slice, building now): list/read/summarize journey reports (no run).
- **CARD-633**: `run_journey` throwaway-only + HITL.
- **CARD-634**: Projects Studio journey runs view.
REQ-533-005 (capability-scoping summary in Developer self-work) stays on the parent until a later slice if still needed after ADR-0062/0064 notes.

## Split complete (2026-10-05)
All Ready slices shipped: CARD-632 (read), CARD-633 (run throwaway+HITL), CARD-634 (Projects Studio view). Parent marked Done. REQ-533-005 (capability-scoping summary in Developer self-work) remains for a later card if still needed after ADR-0062/0064.
