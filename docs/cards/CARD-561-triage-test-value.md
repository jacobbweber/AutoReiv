---
id: CARD-561
title: "Card triage and test value pass"
type: feature
status: In Review
priority: P2
milestone: M22
needs_decision: none
proof:
  journeys: []
  checks: [preflight --fast, pytest tests/unit tests/integration -n auto]
branch: chore/card-561-triage-test-value
log: {minutes: 45, qa_runs: 0, findings: 11}
created: 2026-09-27
---

# CARD-561 Card triage and test value pass

## Intent
The backlog had 73 Ready cards (48 P3), 25+ stale "wait for build" gates and a roadmap where M21 had become a catch-all. The unit suite still carried tests that pin retired card text, duplicate each other or round-trip fake data (192.168.1.29). Technical card, no build gate, no app code.

## Goal
Every Ready card has a milestone and a truthful `needs_decision`; Ready P3 <= 30; the roadmap is milestones only; low-value tests are gone with every guard and contract kept.

## Change
**Triage (cards, docs/findings.md, steering/roadmap.md)**
- Removed 29 stale build-gate lines ("Do not write product code until Jacob says build" x25, "Docs-only until build" x4) from cards with no real decision.
- `needs_decision` set on every Ready card: a real decision on CARD-435, 463, 464, 478, 479, 480, 482, 489, and also on CARD-498, 533, 558 (their decisions are real: data-destructive drop, journey-tool permissions, default tool roots); `none` elsewhere.
- Duplicates closed (`status: Superseded`, `superseded_by`): CARD-534 -> CARD-548 (resume runs in the phase session), CARD-549 -> CARD-554 (Formulate knows the Execute agent).
- Folded into docs/findings.md and card files removed (11): CARD-452, 453, 481, 501, 507, 508, 513, 528, 536, 538, 547.
- Parked (6, to keep Ready P3 <= 30): CARD-466, 487, 493, 494, 499, 542.
- Roadmap rebuilt as milestones only: Done M1-M20 in 6 lines; open M21 Factory retirement, M22 Clean baseline and process, M23 Education Studio, M24 Chat, jobs and tool reliability, M25 Self-development (links steering/self-development.md); Horizon lists Parked cards. Every Ready card has `milestone:`.
- Counts: Ready 73 -> 55 (P0 1, P1 3, P2 22, P3 29, incl. this card); Parked 14 -> 20; Superseded +2; folded 11.

**Test value pass (19 tests deleted, 5 files re-pointed to 127.0.0.1)**
- Pinned retired card text or values (11): `test_card_520_tool_escalation::test_adr_and_changelog_name_card_520` (CHANGELOG/ADR wording); `test_card445_global_turn_budget::test_req_445_007_flashcard_skill_states_no_numeric_default_budget` (skill prose); `test_canonical_agent_resolution_383` x3 (grep for removed internal alias maps/tuples); `test_card268_foundation_honesty_resmoke::test_req_faud_268_ui_anchors_present` (HTML ids); `test_socratic_agent_scaffold` x2 (skill prose; seed==platform invariant kept); `test_card269_good_agent_instructions::test_forge_scaffold_includes_provenance` (dead Quick Scaffold, CARD-514); `test_static_css_396::test_index_inline_style_hygiene` (old CARD-31x comment strings); `test_card444::test_flashcard_skill_forbids_wiki_curation_mid_turn` (asserts "CARD-444" in the skill; the tool-list test that enforces it stays).
- Duplicated coverage (6): the "Education Studio chrome not removed" copy in test_card438, 439, 440, 441, 444 and test_card_436 (same HTML-id asserts; would also block CARD-463's cleanup).
- Fake/sample data round-trip (2): `test_ui_agent_select_and_discovery::test_openai_adapter_custom_provider_id`, `::test_ollama_adapter_custom_provider_id` (constructor stores its args).
- 192.168.1.29 -> 127.0.0.1 in the real-behaviour tests kept: test_ollama_adapter (URL join, timeout label, stream), test_ui_agent_select_and_discovery (settings persistence), test_handoff_engine_kernel (provider failure maps to failed), test_log_buffer, test_system_agent_tools.
- Also committed the `uv.lock` update for CARD-560's pytest-xdist.

## What dies
The 19 tests above, 11 folded card files, 29 stale gate lines, the per-card roadmap lines. No guard test or operator contract touched.

## Proof
- `preflight --fast --base qa` GREEN.
- One parallel run: `pytest tests/unit tests/integration -n auto` 2203 passed, 6 skipped in 71.5 s (was 2222).
- No app code changed, so no live journey.

## Plan and decisions
- Open product decisions (not closed, listed for Jacob): CARD-435, 463, 464 (Education), 478, 479, 480, 482 (Beat 3), 489 D1/D2, 498 D1/D2 (drops tables), 533 D1-D6, 558 D1.

## Findings
- 11 folded cards are now findings lines (M22, M24, M25 sections).
- Resolved and removed: the 192.168.1.29 test-value finding.

## Results
| Check | Result |
|---|---|
| preflight --fast | GREEN |
| unit + integration, -n auto | 2203 passed, 6 skipped, 71.5 s |

## Release note
Backlog triaged into milestones M21-M25 and 19 low-value tests removed.
