---
trigger: always_on
description: Prefer operator-contract and invariant tests over whitebox unit theater; governs what tests to add, keep, or prune.
---

# Rule: Operator-Contract Testing (Regression That Matters)

This rule implements [ADR-0055](../../docs/adr/0055-operator-contract-testing-and-suite-hygiene.md). It overrides any habit of adding broad whitebox unit tests or expanding Playwright volume as the default regression net.

---

## 1. Intent

Jacob wants tests that **prevent operator-visible regressions** (settings that stick, reports that write real wiki notes, Studio jobs that do not lie). He does **not** want a large suite that only mirrors internals and breaks on every harmless refactor.

---

## 2. What To Prefer (In Order)

1. **Operator contracts** — integration/API tests through real FastAPI + real SQLite under a temp user-data directory. Assert durable outcomes an operator can see.
2. **Bucket A invariants** — safety/tool-policy gates, boundary hygiene, single-lever invariants, schema validators, honesty-class negative assertions.
3. **Thin post-live smoke / honesty** — skill `honesty-smoke-gate` and serve hygiene; a small fixed set of golden paths (about five to ten), fail closed on empty deliverables and silent SSE death.
4. **Hermetic unit tests** — only when they lock Bucket A behavior that cannot be expressed cheaper as a contract.

---

## 3. What Not To Do By Default

- Do **not** add whitebox unit tests that assert private helpers, exact historical tool/skill string lists, or card-era fixtures unless they are true Bucket A invariants.
- Do **not** expand Playwright volume to compensate for missing contracts.
- Do **not** weaken, skip, or delete a valid Bucket A or operator-contract assertion to go green — fix the product code.
- Do **not** chase uncarded flaky UI bugs as the main workstream without locking them behind a contract when they are durable-state / deliverable failures.

---

## 4. Operator Contract Shape (Required Pattern)

An operator contract MUST:

1. Use a **temp user-data directory** (never the live Jarvis user-data checkout path as the fixture root).
2. Exercise the **public path** Jacob uses (HTTP API and/or the same application services the Studio calls) — not a private helper alone.
3. Assert **durable state or a non-empty deliverable** (re-read settings; wiki note exists under `00_Inbox/` with non-empty body; metrics fields present).
4. Include at least one **negative assertion** against the known failure mode (empty inbox note, missing persisted field, success theater with no write).

### Seed contracts (CARD-412)

| ID | Operator job | Must assert |
|----|--------------|-------------|
| OC-1 | Settings context-window persist | Save static context window → re-GET / reload store → value matches |
| OC-2 | Observe per-agent chat session metrics report | Seed DB metrics → run report → inbox note non-empty with expected fields |
| OC-3 | Wiki note create single-lever | `wiki_note_create` (or API equivalent) → read back same path; no empty success |

New durable-state bugs get a new OC row (or extend an existing one) **before** or **as** the fix ships.

---

## 5. Suite Hygiene Buckets (CARD-412 And Ongoing)

When touching `tests/`:

| Bucket | Action |
|--------|--------|
| **A** Essential invariants | KEEP and lock |
| **B** Redundant permutations | CONSOLIDATE (parametrize / merge) |
| **C** Dead, zombie, whitebox theater | PRUNE |

Target: kept backend unit/invariant gate meaningfully faster (CARD-412 aims under ~60 seconds) plus a thin `tests/integration/` (or equivalent) operator-contract suite. Pruning must not delete Bucket A or existing operator contracts without Jacob's explicit approval.

---

## 6. Card And Review Gates

- Cards that change settings persistence, wiki inbox deliverables, observe/report jobs, or the test suite itself MUST reference ADR-0055 and list which operator contracts apply.
- **In Review** requires: relevant operator contracts and Bucket A invariants green; honesty-smoke for control-plane tips; Scavenger Pass on superseded test fixtures (see `.agents/rules/code-hygiene-and-pruning.md`).
- Prefer fixing Jacob's example regressions **through** OC-1 / OC-2 rather than one-off manual patches with no lock.
