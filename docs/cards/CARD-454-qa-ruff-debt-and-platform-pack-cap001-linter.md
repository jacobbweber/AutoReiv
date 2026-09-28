---
id: CARD-454
title: "qa baseline: ruff errors and Tutor skills over the CAP-001 tool cap"
type: bug
status: In Review
priority: P1
milestone: M22
needs_decision: none
related: [CARD-456, CARD-451]
proof:
  journeys: [card-454-tutor-trimmed-skills]
  checks:
    - tests/unit/skills/test_capability_linter.py::test_platform_packs_all_pass_mechanical_linter
    - tests/unit/skills/test_capability_linter.py::test_skill_tool_cap_matches_the_runtime_per_turn_clamp
    - preflight.py --fast and --full with no KNOWN
branch: fix/card-454-456-clean-baseline
log: {minutes: 35, qa_runs: 2, reruns: 1, findings: 2, fast_tier_s: 41, full_tier_s: 1004}
created: 2026-09-24
---

# CARD-454 qa baseline: ruff errors and Tutor skills over the CAP-001 tool cap

## Problem
`ruff check .` reported 7 errors on qa, and `test_platform_packs_all_pass_mechanical_linter` failed (4 Tutor skills over
CAP-001). Preflight carried both as KNOWN/XFAIL, so new failures could hide behind them.

## Cause
- Unsorted imports in 6 education files and an unused local (`blob`) in the CARD-440 test.
- CAP-001 allowed 6 tools per skill while the kernel mounts up to 8 per turn (`MAX_ACTIVE_TOOLS_PER_TURN`, ADR-0061 rule 4).
  `due-review` and `education-wiki-curation` declared 10 tools; `progress-summary` 8, `quiz-turn` 7.

## Change
- `ruff --fix` plus deleting the unused `fm`/`blob` lines.
- `linter.MAX_TOOLS_PER_SKILL` 6 -> 8, with a guard test that it equals the kernel per-turn clamp; ADR-0054 amended.
- Trimmed in `platform-packs/tutor/pack.json` and `SKILL.md` (v1.2.0):
  - `due-review` 10 -> 7: dropped `wiki_note_search`, `wiki_note_list`, `wiki_template_list` (the runbook's turn is ledger-only; `wiki_note_read` kept for a due item's source note).
  - `education-wiki-curation` 10 -> 8: dropped `wiki_note_search`, `wiki_note_list` (curation creates, reads and updates notes; templates stay).
  - Every dropped tool is still ticked on Tutor through sibling skills (socratic-tutoring, start-resume-topic, quiz-turn), so Tutor loses no capability.
- Removed the `xfail(CARD-454)` marker and the ruff `KNOWN_LINT` entry.

## What dies
The ruff `KNOWN_LINT` entry, the CARD-454 xfail, the 6-tool CAP-001 limit.

## Proof
- Journey `card-454-tutor-trimmed-skills`: a Tutor chat's due review calls the due ledger tools; a curriculum curation calls the curation tools; no tool is policy-blocked.
- Checks: platform packs pass the linter; cap guard (skill cap == per-turn clamp == 8); CAP-001 still rejects 9 tools.

## Plan and decisions
Cap 8 instead of trimming everything to 6: the kernel mounts 8 tools per turn, so 6 only forced cuts without a runtime reason (Jacob's direction).

## Findings
- (to findings list) openSessionByTitle cannot open API-created Tutor chats.
- (to findings list) scratch/ holds hundreds of stale files from older cards.
- (fixed) merge-to-qa skill: post-merge fast tier base, roadmap tick, scratch keep rule.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-454-tutor-trimmed-skills | desktop | PASS | due review called education_due_review_list; curation called education_wiki_curate_from_curriculum; no blocked tools. Run 1 failed in the journey harness (drawer), fixed; 2026-09-27 20:31 ET. Screenshots: C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-454\ |

- `preflight.py --fast --base qa`: GREEN in 41 s, no KNOWN, no XFAIL (guard 192, changed 63, mapped 10, vitest 955).
- `preflight.py --full`: GREEN in 1004 s, no KNOWN (ruff 0, eslint 0, unit 2122 passed / 11 skipped, integration 103, honesty, vitest 955, smoke 73).

## Release note
Fixed: qa baseline is clean (ruff 0, platform packs pass the linter); CAP-001 skill tool cap is 8, equal to the per-turn clamp; Tutor due-review and wiki-curation trimmed to 7 and 8 tools.

## Legacy notes (pre-CARD-559 format)

### [CARD-454] qa preflight ruff debt + platform pack CAP-001 mechanical linter failures

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-451 build on Jarvis — unified preflight aborted on `ruff check .` (12 errors already present on `qa`); broad `tests/unit` run had 1 unrelated failure `test_platform_packs_all_pass_mechanical_linter`
> **Related**: CARD-451 (noticed during; not caused by CARD-451 surfaces, which are ruff-clean)
> **Labels**: `type:chore`, `area:tooling`, `area:skills`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine scope (auto-fix only vs also CAP budget policy) — **still no product code** |
| **`build`** | Clear the 12 ruff findings and restore platform-pack mechanical linter green |
| **`merge to qa`** | After preflight Python Linter gate passes and `test_platform_packs_all_pass_mechanical_linter` is green |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

Capture every noticed gap from the CARD-451 verification run that already exists on `qa`: full-repo ruff debt that breaks preflight, and the failing platform-pack capability linter contract.

### Beat 2: What AutoReiv does now

1. Skill **preflight** runs `ruff check .` as Gate 1 and aborts the pipeline on any error.
2. On current tip / `qa` baseline (observed 2026-09-24 during CARD-451), `ruff check .` reports **12 errors** (11 auto-fixable with `--fix`; 1 needs `--unsafe-fixes` / manual).
3. `tests/unit/skills/test_capability_linter.py::test_platform_packs_all_pass_mechanical_linter` lints `platform-packs/` and asserts `error_count == 0` / `passed is True`. It currently fails with `AssertionError: assert 4 == 0` because four Tutor platform skills violate **CAP-001** (tool budget max 6).

### Beat 3: What will change

1. Make `ruff check .` pass (import sort / whitespace / unused local) so preflight Gate 1 is green again.
2. Bring platform-pack Tutor skills under the CAP-001 tool budget (or deliberately adjust the mechanical rule with an ADR + test update — prefer budget compliance unless Jacob chooses otherwise).
3. Re-run preflight and the named linter test; no unrelated feature work.

### Beat 4: What dies today

1. Preflight red solely from unsorted imports / blank-line whitespace / one unused test local.
2. Known-red `test_platform_packs_all_pass_mechanical_linter` left unexplained in backlog.

---

## 2. Inventory (exact findings)

### A. Full-repo ruff (`ruff check .` → 12 errors; blocks preflight)

| # | File | Rule | Message |
|---|------|------|---------|
| 1 | `src/application/education/progress_summary.py:8` | **I001** | Import block is un-sorted or un-formatted |
| 2 | `src/application/kernel/agent_kernel.py:5` | **I001** | Import block is un-sorted or un-formatted |
| 3 | `src/infrastructure/agents/registry.py:5` | **I001** | Import block is un-sorted or un-formatted |
| 4 | `src/infrastructure/skills/platform_pack_promotion.py:761` | **W293** | Blank line contains whitespace |
| 5 | `src/web/routers/agents.py:389` | **I001** | Import block is un-sorted or un-formatted |
| 6 | `src/web/routers/chat.py:1` | **I001** | Import block is un-sorted or un-formatted |
| 7 | `tests/unit/agent_packs/test_card_436_tutor_seed_sync.py:3` | **I001** | Import block is un-sorted or un-formatted |
| 8 | `tests/unit/education/test_card438_chat_quiz_flashcard_durable_grading.py:7` | **I001** | Import block is un-sorted or un-formatted |
| 9 | `tests/unit/education/test_card439_due_reviews_in_tutor_education_mode.py:8` | **I001** | Import block is un-sorted or un-formatted |
| 10 | `tests/unit/education/test_card440_wiki_curation_from_links_curriculum.py:8` | **I001** | Import block is un-sorted or un-formatted |
| 11 | `tests/unit/education/test_card440_wiki_curation_from_links_curriculum.py:130` | **F841** | Local variable `blob` is assigned to but never used |
| 12 | `tests/unit/education/test_card441_progress_you_can_trust_non_studio_surface.py:8` | **I001** | Import block is un-sorted or un-formatted |

Notes: 11/12 are `[*]` auto-fixable via `ruff check --fix .`; F841 may need `--unsafe-fixes` or a one-line delete of unused `blob`.

### B. Failing test

- **Test:** `tests/unit/skills/test_capability_linter.py::test_platform_packs_all_pass_mechanical_linter`
- **Failure:** `AssertionError: assert 4 == 0` on `report.error_count == 0` (`scanned_count=22`, `valid_count=18`, `passed=False`).
- **Cause:** Four shipped Tutor platform skills exceed mechanical **CAP-001** tool budget (maximum 6 tools declared):
  - `platform-packs/tutor/skills/due-review/SKILL.md` — 10 tools
  - `platform-packs/tutor/skills/education-wiki-curation/SKILL.md` — 10 tools
  - `platform-packs/tutor/skills/progress-summary/SKILL.md` — 8 tools
  - `platform-packs/tutor/skills/quiz-turn/SKILL.md` — 7 tools
- (Out of scope unless Jacob expands: AppData copies under `%LOCALAPPDATA%\AutoReiv\packs\tutor\...` mirror the same CAP-001 debt; plus a separate CAP-002 on user skill `skills/docker_test/SKILL.md` when linting user paths.)

---

## 3. Acceptance criteria (EARS)

- **[REQ-454-001]** WHEN `ruff check .` runs from repo root, THE SYSTEM SHALL report zero errors (all 12 listed findings resolved).
- **[REQ-454-002]** WHEN skill **preflight** runs, THE SYSTEM SHALL pass the Python Linter (Ruff) gate.
- **[REQ-454-003]** WHEN `test_platform_packs_all_pass_mechanical_linter` runs, THE SYSTEM SHALL assert `error_count == 0` and `passed is True` for `platform-packs/`.
- **[REQ-454-004]** Out of scope unless Jacob expands: fixing AppData pack copies or the user-skill `docker_test` CAP-002; CARD-451 feature behavior.

---

## 4. Proof / live-test notes

1. `uv run ruff check .` → clean.
2. `uv run python .agents/skills/preflight/scripts/preflight.py` → Python Linter gate green (continue remaining gates as applicable).
3. `uv run pytest tests/unit/skills/test_capability_linter.py::test_platform_packs_all_pass_mechanical_linter -q` → pass.

---

## 5. Constraints

- Docs/chore card until **build**. Prefer mechanical fixes (`ruff --fix`) over behavior changes.
- If CAP-001 budgets must rise for Tutor Learning OS skills, file/amend an ADR and update the linter rule + tests deliberately — do not silently weaken the assertion.
- Do not reset `qa`; no force-push; no version bump for this chore alone unless Jacob asks.

---

## 6. Reply phrases

- Refine scope: say **continue**.
- Start cleanup: say **build**.
- After green preflight + linter test: say **merge to qa**.
