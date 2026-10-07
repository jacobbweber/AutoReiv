---
id: CARD-657
title: "Preflight 'changed tests' stage fails when every changed test is slow-marked"
type: bug
status: Backlog
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-06
completed:
related:
  - CARD-656
---

# CARD-657 Preflight 'changed tests' stage fails when every changed test is slow-marked

## Intent
In CARD-656, `preflight.py --fast --base qa` reported "pytest changed tests (not slow) | FAIL | 32 warnings in 6.11s". The only changed Python tests were `tests/unit/skills/test_skills_studio.py` and `test_skills_studio_archive_delete.py`, and both set `pytestmark = pytest.mark.slow`. So `-m "not slow"` selects nothing and pytest exits 5.

`judge()` already treats exit 5 as PASS when the output says "no tests ran" or "deselected", but with `-n auto` (xdist) the summary line has neither. The same files pass in the full suite, so this is a false failure that blocks the prep script.

## Plan (proposal)
In `judge()`, treat pytest exit code 5 as "no tests selected" (PASS) regardless of the text. Pytest documents exit code 5 as "no tests were collected". Optionally, run changed slow-marked tests in that stage instead of skipping them.

## Acceptance
- A change whose only changed tests are slow-marked gets PASS ("no tests selected") or runs those tests, but is never a FAIL with no failing test.
