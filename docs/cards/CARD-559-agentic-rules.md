---
id: CARD-559
title: "Agentic rules: slim playbook, fast/full/nightly preflight, known-bug XFAIL, model check"
type: feature
status: In Review
priority: P1
milestone: M22
needs_decision: none
proof:
  journeys: [card-520-teach-needs-tool]
  checks:
    - tests/unit/frontend/live_qa_runner_532.test.js
    - tests/unit/scripts/test_card559_live_qa_model_check.py
    - tests/unit/skills/test_card559_card_and_preflight_scripts.py
    - preflight.py --fast
branch: feat/card-559-agentic-rules
log: {minutes: 60, qa_runs: 1, reruns: 0, findings: 7, fast_tier_s: 332, full_tier_s: 1107}
created: 2026-09-27
---

# CARD-559 Agentic rules: slim playbook, fast/full/nightly preflight, known-bug XFAIL, model check

## Intent
Every session loaded ~7,150 tokens of rules, many duplicated or stale, and the gates stopped on the first failure,
retried flaky journeys and nudged the model past a known bug. Jacob approved the rules drafts (scratch/rules-draft,
2026-09-27) with one change: the Roles and Overnight sections move out of AGENTS.md into a design note.

## Goal
An agent starts a card from a short AGENTS.md and four always-on rules, proves it with `preflight.py --fast` that
runs every stage and names known failures, and runs live QA that says "model endpoint down" (exit 4) instead of
failing, marks known bugs XFAIL with their card id and never nudges.

## Change
- `AGENTS.md`: slim playbook (card loop, max 2 build->verify rounds then stop and report, where things live).
- `.agents/rules/`: boundaries, code-quality, testing, definition-of-done (always on) + frontend (UI cards).
- `.agents/skills/`: card (templates bug/feature, new_card.py, list_card_status.py), preflight, live-qa,
  merge-to-qa, ui-review; serve-hygiene, lifecycle/boundary/single-lever audits, adr-manager trimmed.
- `steering/self-development.md`: Roles (Plan/Build/Verify), model-swap batching, overnight (future design note).
- `docs/findings.md`: per-milestone findings log (M22 seeded).
- `preflight.py`: `--fast [--base qa]`, `--full`, `--nightly`; no stop on first failure; KNOWN for CARD-454/456 lint.
- `pyproject.toml`: `guard` and `slow` markers; 29 guard files, 34 slow files tagged.
- Known failures marked: `xfail(strict, CARD-454)` linter test; `it.fails` for 3 CARD-456 Vitest tests.
- `scripts/live_qa.py`: `check-model` (exit 4, "model endpoint down"); `run` checks the model first; reruns only when the endpoint is down.
- `runner.mjs`: `knownBug: 'CARD-N'` -> XFAIL (or XPASS = fail); `soft` needs `card`.
- Journeys: card-520 nudge (CARD-535 workaround) removed, attach step `knownBug: 'CARD-535'`; soft steps name CARD-543 / CARD-546.

## What dies
- Rules: agents-vs-packs, architecture, capability-scoping, checkout-hygiene, code-hygiene-and-pruning, frontend-quality,
  git-workflow, human-engagement, operator-contract-testing, sdd-ears, single-card, tdd-invariants, ui-ux-design (merged).
- Skills: sdd-workflow, card-status, honesty-smoke-gate, tdd-cycle, regression-sentinel (merged into card/preflight/testing).
- The Four Beats card template, the CARD-535 "Approved. Please continue" nudge, journey retries on product failures.

## Proof
- Journey `card-520-teach-needs-tool` (desktop): the attach step is XFAIL CARD-535 (or XPASS -> remove the marker).
- Checks: runner Vitest (xfail / xpass / soft-needs-card), live_qa unit tests (check-model, exit 4, no product retry),
  new_card/preflight script tests, `preflight.py --fast` GREEN with KNOWN/XFAIL only.

## Plan and decisions
Approved in chat (build, then continue). No open decisions.

## Findings
See docs/findings.md (M22). Deferred: list_card_status `--milestone`/priority column (finding), stale build lines and roadmap rebuild (card 4),
CARD-454/456 fixes (card 2), test speed (card 3).

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-520-teach-needs-tool | desktop | XFAIL | Step 4 XFAIL CARD-535: the Developer stopped without proposing attach_tool_to_skill (no nudge). Steps 1-3 pass. ~13 min, 2026-09-27 19:23 ET. Screenshots: C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-559\ |

- `live_qa.py check-model` against 192.168.1.218:8099 (nemotron-3.5-lightning): ok, exit 0; against a dead URL: "model endpoint down", exit 4.
- `preflight.py --fast --base qa`: GREEN in 332 s (ruff/eslint changed PASS, guard 190 passed + 1 xfailed in 25 s, changed tests 339 passed + 1 xfailed in 297 s, vitest PASS).
- `preflight.py --full`: GREEN in 1107 s (ruff KNOWN 7 CARD-454, eslint KNOWN 5 CARD-456, unit 2120 passed / 11 skipped / 1 xfailed, integration 103, honesty PASS, vitest 955, smoke 73).

## Release note
Changed: slim agent playbook and rules; preflight fast/full/nightly tiers; live QA model check (exit 4) and known-bug XFAIL.
