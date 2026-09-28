---
id: CARD-331
title: 'Help Studio'
status: Parked
created: 2026-09-14
adr: none
labels:
  - type:feature
  - P1
  - Help
  - Studio
  - UX
  - OperatorDocs
---

# [CARD-331] Help Studio

> **Status**: Parked
> **Created**: 2026-09-14
> **Branch**: `feat/education-studio-finish`
> **Locked Decisions**: Option A on both — (a) New dock Studio, (b) In-app interactive panels.
> **Labels**: type:feature, P1, Help, Studio, UX, OperatorDocs

---

## 1. The Three Beats

### Beat 1: What Jacob Means

1. Per-feature **“what it is / how to use it”** operator help (brain dump Addition 9).
2. Help is reachable from the product surface — operators should not need the repo to learn a feature.
3. Content stays honest and feature-scoped; not a second marketing site.

### Beat 2: What AutoReiv Does Now

1. CARD-021 system-info hub already covers conceptual / architectural overviews to some degree.
2. There is no dedicated Help Studio (or locked expansion of system-info) for per-feature operator help.
3. UI/UX chrome placement for help is undecided (dock Studio vs nested; in-app vs Wiki).

### Beat 3: What Will Change

1. Deliver per-feature “what it is / how to use it” help once placement is locked.
2. Wire chrome placement per Needs discussion outcome (new Studio vs expand system-info; dock vs nested; panels vs Wiki).
3. TDD / smoke as appropriate for chosen surface. **Do not implement until Needs discussion resolves.**

---

## 2. Acceptance

- [ ] **[REQ-HELP-001]**: Per-feature operator help covers “what it is” and “how to use it” for the scoped features.
- [ ] **[REQ-HELP-002]**: Help is reachable from agreed chrome placement (Studio / system-info / nested — per discussion lock).
- [ ] **[REQ-HELP-003]**: Content surface matches discussion lock (in-app panels and/or Wiki pages) without duplicate-theatre.
- [ ] **[REQ-HELP-004]**: Proof: operator can open help for at least one real feature end-to-end. No toast-only Done.

---

## 3. Needs discussion (Decisions Locked)

- (a) **Placement**: **New dock Studio** (Option A locked by Jacob).
- (b) **Surface**: **In-app interactive panels** (Option A locked by Jacob).
- **Current Hold**: Paused to allow upcoming studio and feature evolutions to settle before authoring documentation.

---

## 4. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- **Do not implement** until Needs discussion (CARD-021 + chrome placement) is resolved.
- Coordinate UI/UX for chrome placement; no product code on this scaffold commit.

---

## 5. Out of scope

- Full product documentation rewrite
- Assistant constitution / Wiki scrub (CARD-332)
- Education delivery profiles / knowledge-type anchors (CARD-333/334)

---

## 6. Reply phrases

- After scaffold → Jacob: **build** (or **build CARD-331**) — only after Needs discussion resolves
- After live OK → Jacob: **merge to qa**
