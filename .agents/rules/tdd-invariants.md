---
trigger: glob
globs: 'src/**/*.py,tests/**/*.py,src/web/static/**/*.js'
description: Test-locked delivery via operator contracts and invariants — not broad whitebox TDD theater.
---

# Rule: Test-Locked Delivery & Verification Invariants

Companion: [ADR-0055](../../docs/adr/0055-operator-contract-testing-and-suite-hygiene.md) and `.agents/rules/operator-contract-testing.md`.

## 1. Outcome-Driven Verification (Test-Locked Delivery)

We reject dogmatic TDD theater (writing artificial mock tests before understanding the problem, only to abandon cleanup once green). We also reject **volume unit suites** that pin internals and miss operator jobs. We enforce **Test-Locked Delivery**:

- **Exploration & Root Cause Analysis First**: Inspect the runtime, experiment, and prototype to understand bugs and architectural boundaries before locking assertions.
- **Zero Code Ships Untested**: No feature, bug fix, or refactor moves to `In Review` or merges into `qa` without automated proof. Prefer **operator contracts** and **Bucket A invariants** over new whitebox unit tests. Thin post-live honesty/smoke covers control-plane tips (skill `honesty-smoke-gate`).
- **Negative Assertions (Regression Guards)**: Assert that the defective behavior is absent (empty inbox deliverable, missing persisted setting, obsolete DOM, deprecated flags, duplicate stream bubbles).
- **Immutable Assertion Rule**: Do not weaken, comment out, or delete valid Bucket A or operator-contract assertions to make a test pass. Fix the implementation. Pruning Bucket C zombie tests is allowed under CARD-412 / ADR-0055 with an explicit prune rationale.

---

## 2. Which Tests To Write

| Situation | Write |
|-----------|--------|
| Durable settings, DB → wiki/report deliverable, Studio round-trip | Operator contract (real FastAPI + SQLite, temp user-data) |
| Safety gate, schema, single-lever, boundary hygiene | Bucket A unit/invariant test |
| Control-plane tip / SSE honesty | honesty-smoke-gate (post-live) |
| Pure helper with no operator surface | Small hermetic unit test only if it locks a real invariant |
| "Make coverage numbers go up" / mirror private fields | **Do not write** |

Playwright / Vitest frontend checks remain useful for chrome invariants, but they are **not** a substitute for operator contracts on persistence and deliverables.

---

## 3. The Refactor & Scavenger Pass (Mandatory Post-Green Cleanup)

Getting tests to pass is the midpoint, not the finish line. Once automated proof is green:

1. **Execute the Scavenger Pass** (`.agents/rules/code-hygiene-and-pruning.md`): grep modified/superseded symbols; remove orphaned callers and dead branches.
2. **Enforce the Single Lever Invariant**: new logic replaces the old path; no parallel duplicate lever.
3. **Re-verify**: re-run the kept backend gate (invariants + operator contracts) and relevant frontend tests; do not require the historical 1,850-test drag as proof of Done once CARD-412 prune has landed.

---

## 4. Test Quality Standards

- **Unit (Bucket A)**: Fast, hermetic; interfaces or in-memory fixtures where possible.
- **Operator contracts / integration**: Vertical slices against real SQLite and FastAPI under temp user-data; assert durable outcomes and fail closed on empty success theater.
- **Edge Cases**: Empty strings, 0, null/undefined, timeouts, external service failures — especially on contract boundaries.
- **Zero Suppression**: Do not use `@ts-ignore`, `eslint-disable`, `skip`, or `# type: ignore` to mask failing tests without explicit human approval.
