# [ADR-0055] Operator-Contract Testing Over Broad Unit-TDD Theater

> **Status**: Accepted  
> **Date**: 2026-09-21  
> **Deciders**: Jacob (Visionary & Product Owner), AutoReiv Harness Engineer  
> **Consulted**: Chief of Staff direction on harness reliability  
> **Related Cards**: [CARD-412](../cards/CARD-412-test-suite-hygiene-obsolete-test-pruning-and-consolidation-audit.md)  
> **Supersedes / Softens**: Dogmatic broad unit-TDD interpretation of `.agents/rules/tdd-invariants.md` (pre-2026-09-21); volume Playwright as primary regression net  
> **Companion Rules**: `.agents/rules/tdd-invariants.md`, `.agents/rules/operator-contract-testing.md`, `.agents/rules/definition-of-done.md`

---

## 1. Context & Problem Statement

AutoReiv accumulated ~1,850 unit tests (~4.5 minutes per backend run) under a forced Test-Driven Development push. Those tests largely pin **internal implementation details** (exact tool string lists, private helpers, historical card shapes). After architectural redactors and direction shifts:

1. Harmless refactors break dozens of whitebox tests that then get rewritten to match the new internals — they never fail on operator-visible bugs.
2. Playwright and chrome-level smokes miss durable-state and cross-layer failures.
3. Real regressions keep returning: for example, static context-window settings that do not persist after save, and Observe per-agent chat-session metrics reports that write an empty wiki inbox note despite data existing in the database.

Jacob's intent for tests was **preventing regression of operator jobs**. The current suite does not buy that intent at acceptable cost.

---

## 2. Decision Drivers

* **Operator jobs over internals**: Persistence, inbox deliverables, and Studio round-trips matter more than private helper shapes.
* **Subtractive suite hygiene**: Dead and brittle tests are a continuous tax on every card.
* **Fast feedback**: Backend gate should target under ~60 seconds for the kept unit/invariant set, plus a thin contract layer.
* **Honesty over theater**: Empty deliverables, silent failures, and "looks done but wrote nothing" must fail closed (honesty-smoke-gate).
* **No pause forever**: Strategy lands via CARD-412 without freezing all product work indefinitely.

---

## 3. Considered Options

* **Option 1: Keep expanding broad unit TDD and Playwright volume.**  
  *Rejected*: Already failed to catch the regressions Jacob cares about; high maintenance cost.
* **Option 2: Delete the entire unit suite and rely only on manual live testing.**  
  *Rejected*: Loses real invariants (safety gates, single-lever, schema/boundary) and honesty checks.
* **Option 3: Operator-contract pyramid (Chosen)** — keep a small invariant unit bucket; prune zombies and brittle whitebox; lock durable operator jobs with integration/API contracts and a thin post-live smoke/honesty gate.

---

## 4. Decision Outcome

Chosen: **Option 3**.

### Testing pyramid (AutoReiv)

1. **Bucket A — Essential invariants (KEEP)**  
   Security / tool-policy gates, boundary hygiene, single-lever invariants, schema validators, honesty-class negative assertions. Fast, hermetic where possible.

2. **Bucket B — Redundant permutations (CONSOLIDATE)**  
   Parameterize or merge overlapping helper tests.

3. **Bucket C — Dead / zombie / whitebox theater (PRUNE)**  
   Retired tools/skills/packs, superseded card fixtures, assertions on private internals that do not express an operator contract.

4. **Operator contracts (ADD / PREFER)**  
   Vertical slices through real FastAPI + real SQLite under a temp user-data directory. Assert durable outcomes Jacob can see: settings round-trip, non-empty wiki inbox notes, chat/session metrics readable after seed.

5. **Post-live smoke / honesty (KEEP THIN)**  
   Skill `honesty-smoke-gate` and serve hygiene against a running instance. Five to ten golden paths maximum — not unbounded Playwright growth. Fail closed on empty deliverables and silent SSE death.

### Default for new cards

* Prefer an **operator contract** or **invariant negative assertion** for durable state and Studio/operator jobs.
* Do **not** add whitebox unit tests that only mirror implementation details unless they lock Bucket A safety/schema invariants.
* Do **not** expand Playwright volume as a substitute for contracts.
* Fix regression bugs **through** a failing contract first whenever the bug is an operator round-trip.

### First contracts (seeded by CARD-412)

1. **Settings context-window persist**: set static context window via settings API → re-read → value matches; survives process-equivalent reload of settings store.
2. **Observe per-agent chat session metrics → non-empty inbox**: seed session metrics in DB → run observe/report path → `00_Inbox/` note exists and body is non-empty with expected fields.
3. **Wiki note create single-lever smoke**: create via `wiki_note_create` (or public API equivalent) → read back same path; no empty success theater.

---

## 5. Consequences

* CARD-412 executes suite triage, prune, and the first operator contracts.
* `.agents/rules/tdd-invariants.md` and DoD are updated to match this ADR.
* New always-on guidance lives in `.agents/rules/operator-contract-testing.md`.
* AGENTS.md test-locked delivery bullet points at operator contracts rather than "comprehensive unit + Playwright" volume.

---

## 6. Compliance

Agents MUST re-read this ADR and the companion rules before proposing new test files or declaring In Review for cards that touch durable settings, wiki inbox deliverables, observe/report jobs, or large test-suite changes.
