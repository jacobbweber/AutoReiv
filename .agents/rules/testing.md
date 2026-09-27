---
trigger: always_on
description: How every change is proven. Each line is checkable.
---
# Testing

## Order
1. Reproduce and find the root cause.
2. Write a test that fails for that cause.
3. Fix. See it pass.

## What to write (first that fits)
1. Operator contract: real FastAPI + SQLite, temp data dir, assert a durable outcome plus one negative assertion. Folder `tests/integration/`.
2. Guard test: an invariant or architecture rule (boundaries, capability scoping, single lever, schema). Mark the file `pytestmark = pytest.mark.guard`.
- A test file slower than about 1.5 s per test gets `pytestmark = pytest.mark.slow` (skipped by the fast tier unless changed).
3. Small unit test for pure logic. Do not assert private helpers or copy internal string lists.
- Every bug fix leaves a negative assertion that the bug is gone.
- Every ADR that constrains code has a guard test that names the ADR.

## Live journeys
- A journey (`tests/e2e/journeys/card-N-slug.mjs`) is the proof of done for a card.
- Assert structure (a card appears, a job reaches done, a tool is called), never exact model text.
- Where the model chooses the path, force the path (direct prompt or API call). Routing checks live in their own journey.

## Known bugs
- Test blocked by an open card: `@pytest.mark.xfail(strict=True, reason="CARD-N")`.
- Journey step blocked by an open card: `{ knownBug: 'CARD-N' }`. It reports XFAIL; a pass (XPASS) fails the run so the marker gets removed.
- `soft: true` needs `card: 'CARD-N'`.
- No nudges, extra prompts, retries or sleeps to get past a known bug.

## Never
- Never weaken, skip or delete a valid assertion to go green. Fix the code.
- Never delete a guard test or operator contract without Jacob's OK.

## Tiers
| Tier | When | Command (skill `preflight`) | Budget |
|---|---|---|---|
| Fast | every branch before In Review, after each merge | `preflight.py --fast` | ~3 min |
| Proof | every card | `scripts/live_qa.py run --journeys <ids>` | 10-15 min |
| Full | once per merge batch; nightly adds all journeys | `preflight.py --full` / `--nightly` | ~22 min |
