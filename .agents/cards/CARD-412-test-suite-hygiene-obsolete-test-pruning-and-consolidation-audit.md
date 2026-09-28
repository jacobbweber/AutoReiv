---
id: CARD-412
title: "Test Suite Hygiene, Operator-Contract Pyramid, and First Regression Locks"
status: Done
created: 2026-09-21
adr: docs/adr/0055-operator-contract-testing-and-suite-hygiene.md
labels:
  - type:refactor
  - area:tests
  - area:hygiene
  - area:reliability
---

# [CARD-412] Test Suite Hygiene, Operator-Contract Pyramid, and First Regression Locks

> **Status**: Done  
> **Created**: 2026-09-21  
> **ADR Reference**: [ADR-0055](../adr/0055-operator-contract-testing-and-suite-hygiene.md)  
> **Labels**: `type:refactor`, `area:tests`, `area:hygiene`, `area:reliability`  
> **Rules**: `.agents/rules/operator-contract-testing.md`, `.agents/rules/tdd-invariants.md`, `.agents/rules/definition-of-done.md`

---

## 1. Why / Intent (Beat 1: What Jacob Means)

After many redactors and direction shifts, AutoReiv carries a massive unit suite (~1,850 tests, ~4.5 minutes) that was grown under forced TDD. That suite is **not** preventing the regressions Jacob cares about. Playwright and chrome-level checks also miss durable-state failures.

**Examples (uncarded today; become first operator contracts here):**

1. Static **context window** size saved in settings does **not** persist after save/reload.
2. **Observe** per-agent chat session metrics report writes an **empty** wiki inbox note even when DB data exists (previously worked).

**Goal:** Establish solid footing ΓÇö prune test theater, lock operator jobs with contracts, keep only invariants that matter ΓÇö before spending cycles on one-off bug whack-a-mole that will recur.

---

## 2. What AutoReiv Does Now (Beat 2)

1. Large whitebox unit suite pinning internals (tool string lists, private helpers, retired pack shapes).
2. Integration folder exists but is not the default regression net for Studio/operator jobs.
3. Definition of Done and TDD rules historically pushed "comprehensive unit + Playwright" volume.
4. Honesty-smoke / serve-hygiene skills exist but are not paired with durable operator contracts for settings and observeΓåÆinbox.
5. Governance as of this card: **ADR-0055 Accepted**; new always-on rule `operator-contract-testing.md`; TDD + DoD updated to prefer contracts.

---

## 3. What Will Change (Beat 3)

### Phase 0 ΓÇö Governance (this continue; lands with rules/ADR) Γ£à planned in-repo

- ADR-0055 accepted.
- `.agents/rules/operator-contract-testing.md` (always_on).
- Rewrite `.agents/rules/tdd-invariants.md` and soften Playwright-as-primary in `.agents/rules/definition-of-done.md`.
- Point `AGENTS.md` test-locked delivery at ADR-0055 / operator contracts.

### Phase 1 ΓÇö Inventory & prune (on **build**)

1. Triage `tests/unit/**` into Buckets A / B / C (see ADR-0055).
2. PRUNE Bucket C (retired weekly tools, zombie fixtures, superseded card whitebox).
3. CONSOLIDATE Bucket B.
4. KEEP Bucket A; measure wall time; target kept backend unit/invariant gate under ~60 seconds where practical (plus contracts separately).

### Phase 2 ΓÇö First operator contracts (on **build**, same card)

| ID | Contract | Failure mode locked |
|----|----------|---------------------|
| **OC-1** | Settings context-window persist | Save ΓåÆ re-read mismatch / silent drop |
| **OC-2** | Observe per-agent chat session metrics ΓåÆ inbox | Empty `00_Inbox/` note despite DB rows |
| **OC-3** | Wiki note create single-lever | Success theater with no readable note |

Implementation notes:

- Temp user-data dir fixtures; real FastAPI + SQLite.
- Prefer `tests/integration/operator_contracts/` (or equivalent clear path).
- Fix OC-1 and OC-2 product bugs **through** the failing contracts (do not "manual patch only").

### Phase 3 ΓÇö Thin post-live map (on **build** if time; else follow-up)

Document the five-to-ten golden paths for honesty-smoke / serve-hygiene; no Playwright volume expansion.

---

## 4. What Dies Today (Beat 4)

**Governance / process (now):**

- Dies: default of "add more unit tests / more Playwright" as the regression answer.
- Dies: DoD language that treats Playwright volume as equal to durable-state proof.

**On build (execution):**

- PRUNE: Bucket C zombie/retired/whitebox theater tests (explicit file list produced during triage).
- PRUNE: Redundant overlapping permutations (fold into parametrized Bucket B).
- PRUNE: Habit of fixing OC-class bugs without a lasting contract.

---

## 5. Acceptance Criteria (EARS)

- **[REQ-412-000] Governance**: THE SYSTEM SHALL document ADR-0055 and ship `.agents/rules/operator-contract-testing.md` plus updated `tdd-invariants.md` and `definition-of-done.md` aligned to operator contracts.
- **[REQ-412-001] Dead-test elimination**: THE SYSTEM SHALL contain zero Bucket C tests asserting retired symbols, superseded tools, or archived pack structures after the prune pass.
- **[REQ-412-002] Speed**: THE SYSTEM SHALL complete the kept backend unit/invariant gate in under 60 seconds on a standard Jarvis-class dev machine (operator contracts may be a separate named gate).
- **[REQ-412-003] Invariants retained**: THE SYSTEM SHALL retain Bucket A security, boundary, single-lever, and honesty-class negative assertions.
- **[REQ-412-004] OC-1**: WHEN an operator saves a static context-window size via settings, THE SYSTEM SHALL persist and return that value on subsequent read/reload.
- **[REQ-412-005] OC-2**: WHEN session metrics exist in storage and the observe per-agent metrics report runs, THE SYSTEM SHALL write a non-empty note under `00_Inbox/` containing expected metric fields.
- **[REQ-412-006] OC-3**: WHEN a note is created through the canonical create path, THE SYSTEM SHALL allow read-back of that note at the same path with non-empty body.

---

## 6. Constraints & Verification Plan

### Automated

- Before/after counts and timings for `pytest` unit gate vs integration operator contracts.
- `ruff check` on touched test and src paths.
- OC-1..OC-3 green.

### Manual (Jacob)

- Live: set context window, restart or hard refresh settings, confirm value sticks.
- Live: run observe per-agent chat session metrics report; confirm inbox note is non-empty.
- Confirm agents following `.agents/rules` no longer propose whitebox TDD theater as the default.

### Out of scope for this card

- Full rewrite of every historical unit file beyond triage buckets.
- Large new Playwright suites.
- Unrelated UI polish bugs without an operator contract.

---

## 7. Human reply phrases

- **continue** ΓÇö refine this plan / governance only (no prune/fix yet).
- **build** ΓÇö execute Phase 1 prune + Phase 2 OC-1..OC-3 (and product fixes).
- **merge to qa** ΓÇö after In Review live-test of contracts and prune.

---

## 8. Build outcomes (Phase 1+2)

### Status
**In Review** ΓÇö OC-1..OC-3 green; prune documented; awaiting Jacob live verification.

### Phase 1 prune list (Bucket C whitebox theater)

Deleted (frontend source-string / CSS-class / z-order polish locks with no operator-contract value):

- `tests/unit/frontend/css_extraction_396.test.js`
- `tests/unit/frontend/studio_window_containment_348.test.js`
- `tests/unit/frontend/observe_collapse_agent_kpis_311.test.js`
- `tests/unit/frontend/observe_expand_scroll_312.test.js`
- `tests/unit/frontend/chat_no_titlebar_agent_picker_301.test.js`
- `tests/unit/frontend/sessions_not_on_dock_305.test.js`
- `tests/unit/frontend/factory_popup_scroll_314.test.js`
- `tests/unit/frontend/routines_modal_zorder_dock_clearance_344.test.js`

Kept Bucket A: scavenger negatives, weekly-tool excision locks, safety/schema/single-lever tests, honesty packs.

Deferred (intentional): full education/orchestration whitebox consolidation (Bucket B) ΓÇö large surface; follow-up card if suite still >60s after contracts separate gate.

### Phase 2 operator contracts

| ID | Path | Result |
|----|------|--------|
| OC-1 | `tests/integration/operator_contracts/test_oc1_settings_context_window_persist.py` | green |
| OC-2 | `tests/integration/operator_contracts/test_oc2_observe_session_metrics_inbox.py` | green |
| OC-3 | `tests/integration/operator_contracts/test_oc3_wiki_note_create_single_lever.py` | green |

### Product fixes

- **OC-1**: CARD-153 removed `saveMatrixBtn` but left `#defaultContextInput` loading without a save path. `Save Provider` now also `POST /api/settings/matrix` with `default_context_window`. `SettingsService.save_purpose_matrix` persists `model_dump(mode="json")`.
- **OC-2**: Audit export returned success without verifying note body (unit test mocked wiki and never asserted content). Export now fail-closes on empty markdown / empty read-back and returns `body_chars`. `FrontmatterParser.dump` uses `model_dump()` for all Pydantic metas including `WikiInboxNoteMeta`.

### Human live-test steps (Jacob)

1. **OC-1 live**: Settings Studio ΓåÆ set Default context window to `131072` ΓåÆ Save Provider ΓåÆ hard refresh (or restart serve) ΓåÆ confirm input still shows `131072`.
2. **OC-2 live**: Chat a few turns with an agent that records telemetry ΓåÆ Observe Studio ΓåÆ pick that agent/session ΓåÆ Generate Report to Inbox ΓåÆ open the new `00_Inbox/` note ΓåÆ confirm non-empty body with Total Tokens / prompt breakdown (not frontmatter-only).
3. **OC-3 live**: Wiki ΓåÆ create a note via Studio (or confirm wiki_note_create path) ΓåÆ open same path ΓåÆ body non-empty.
4. Confirm agents following `.agents/rules/operator-contract-testing.md` no longer propose whitebox TDD theater as the default regression answer.

