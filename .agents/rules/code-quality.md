---
trigger: always_on
description: One path per capability, delete what you replace, keep it simple.
---
# Code quality

- One capability, one code path. Change the canonical function, or replace it and delete the old one. Never add a parallel helper, control, listener or endpoint for the same job.
- The card's "What dies" lists what the change retires ("nothing" is allowed). Delete it on the same card.
- Scavenger before In Review: `rg -n "<symbol>"` for every touched or retired symbol. Zero orphaned callers, imports, DOM ids, CSS rules or fixtures.
- Write code for the card only. No speculative options or extension points. Extract a helper on the third copy, not the second.
- Do not grow a file past 800 lines. When you touch one that is over, split out the part you change.
- No new suppressions (`eslint-disable`, `# noqa`, `# type: ignore`, `pytest.mark.skip`) without Jacob's OK.
- No new lint errors or warnings in changed files (`ruff check`, `npx eslint`).
