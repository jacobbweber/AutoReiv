---
trigger: model_decision
description: Use before declaring a slice, PR, or merge ready - DoD checklist including Scavenger Pass, operator contracts, and honesty gate.
---

# Rule: Definition of Done (DoD) Gate

Before declaring any feature, vertical slice, card, or pull request complete, the agent must verify that every item on this checklist is satisfied.

Companion: [ADR-0055](../../docs/adr/0055-operator-contract-testing-and-suite-hygiene.md), `.agents/rules/operator-contract-testing.md`, `.agents/rules/tdd-invariants.md`.

---

## 1. Automated Verification & Code Quality Checklist

- [ ] **Card Acceptance Criteria Synchronized**: `docs/cards/CARD-xxx.md` accurately documents implemented behavior, data structures, and edge cases.
- [ ] **Operator Contracts / Invariants Pass**: Relevant **operator contracts** (durable settings, wiki inbox deliverables, observe/report jobs) and **Bucket A invariants** pass. Do not treat a large historical whitebox unit suite as proof of Done once CARD-412 prune guidance applies — prefer the named contract + invariant gates.
- [ ] **Frontend Unit Tests (Vitest)**: Pure frontend logic/utilities that changed have passing unit tests where they lock real UI invariants.
- [ ] **Negative Assertions & Regression Guards**: Tests explicitly assert that previous defects (empty deliverables, missing persisted fields, obsolete DOM, redundant states) cannot reoccur.
- [ ] **Thin Smoke / Honesty (Not Playwright Volume)**: Control-plane tips pass skill `honesty-smoke-gate` (no `done_on_failed`, `honesty_theatre`, `silent_sse_death`). Frontend chrome checks may use Vitest/Playwright sparingly for navigation/invariants — **do not** expand Playwright volume as a substitute for operator contracts.
- [ ] **Scavenger Pass Completed**: Callers audited via ripgrep; zero orphaned functions, dead variables, zombie DOM, or superseded test fixtures left behind (`.agents/rules/code-hygiene-and-pruning.md`).
- [ ] **Single Lever Verified**: Exactly one canonical code path exists for every modified capability.
- [ ] **Lint & Style Clean**: Zero linter errors and zero warnings (`ruff check .`, `npm run lint:frontend`).
- [ ] **No Unverified Suppressions**: Zero unapproved `@ts-ignore`, `eslint-disable`, or `# type: ignore` directives.

---

## 2. Architecture & Documentation Checklist

- [ ] **Topology & Steering Updated**: Any new container or component is mapped in `steering/structure.md` or `steering/tech.md`.
- [ ] **ADR Filed**: If a significant architectural, technology, testing-strategy, or structural decision was made, an ADR is filed under `docs/adr/` (testing pyramid changes → ADR-0055 or a successor).
- [ ] **Changelog Updated**: `CHANGELOG.md` updated with the change summary under `[Unreleased]`.
- [ ] **Honesty / stress smoke (control-plane tips)**: No red class before merge to `qa`. See skill `honesty-smoke-gate`.
- [ ] **Branch Hygiene**: Working feature/fix branch merged into `qa` and local branch deleted (`git branch -d <branch>`).

---

## 3. Live QA And Review Check-in Checklist

- [ ] **Assistant live QA done**: The card's live-test steps were run by the assistant (Playwright real browser, real models, desktop 1280x800 and phone 390x844, isolated scratch/test environment); failures fixed; results recorded in the card. CARD-532 runner / skill `live-qa` when available.
- [ ] **Out-of-scope findings filed**: Each one is a Ready card.
- [ ] **Review check-in sent**: What changed, what was tested, results, open items and new cards, 2-3 screenshots under a C: path (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-N\`). Merge only after Jacob's **merge to qa**.
- [ ] **Observability**: Clear log outputs or visual endpoints highlighted for inspection.
- [ ] **Contract Map**: For durable-state cards, name the OC-* (or new) operator contract that locks the job.
