---
id: CARD-454
title: "qa preflight ruff debt + platform pack CAP-001 mechanical linter failures"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-451
labels:
  - type:chore
  - area:tooling
  - area:skills
  - P2
---

# [CARD-454] qa preflight ruff debt + platform pack CAP-001 mechanical linter failures

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
