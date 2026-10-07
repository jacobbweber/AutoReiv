---
id: CARD-657
title: "Preflight 'changed tests' stage fails when every changed test is slow-marked"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/skills/test_card657_preflight_zero_tests_pass.py]
branch: feat/card-657-preflight-zero-tests-pass
log: {minutes: 15, qa_runs: 0, findings: 0}
created: 2026-10-06
completed: 2026-10-06
related:
  - CARD-656
---

# CARD-657 Preflight 'changed tests' stage fails when every changed test is slow-marked

## Intent
In CARD-656, `preflight.py --fast --base qa` reported "pytest changed tests (not slow) | FAIL | 32 warnings in 6.11s". The only changed Python tests were `tests/unit/skills/test_skills_studio.py` and `test_skills_studio_archive_delete.py`, and both set `pytestmark = pytest.mark.slow`. So `-m "not slow"` selects nothing and pytest exits 5.

`judge()` already treated exit 5 as PASS when the output said "no tests ran" or "deselected", but with `-n auto` (xdist) the summary line has neither. The same files pass in the full suite, so this is a false failure that blocks the prep script.

## Decisions
- Jacob approved the build on 2026-10-06.
- Treat pytest exit code 5 as "no tests selected" (PASS) whenever the stage is not a lint stage (`lint is None`). Pytest documents exit 5 as "no tests were collected"; do not require the text "deselected" or "no tests ran".
- Do not change which tests the stage runs; slow-marked files still stay out of the fast "not slow" stage.

## Change
- `preflight.py` `judge()`: `rc == 5 and lint is None` → PASS with note "no tests selected".

## What dies
A green full suite blocked by a false FAIL on a stage that selected zero tests.

## Proof
- Checks (failing first): exit 5 with only a warnings line (the CARD-656 shape) is PASS; empty output too; classic "no tests ran" / "deselected" still PASS; a real pytest failure and a lint exit 5 still FAIL.
- Lean: recreate a fast-preflight case that selects zero tests and confirm the stage is PASS, not FAIL.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | __PYTEST__ |
| preflight --fast --base qa | GREEN | __FAST__ |

## Release note
Quick preflight no longer fails a stage when pytest selected zero tests (for example when every changed test is marked slow).
