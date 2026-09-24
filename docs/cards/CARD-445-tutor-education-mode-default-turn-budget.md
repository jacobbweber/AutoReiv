---
id: CARD-445
title: "Tutor Education-Mode Default Turn Budget (Pack / Profile Default Above 10)"
status: Ready
created: 2026-09-23
adr: none
labels:
  - type:feature
  - area:tutor
  - area:agents
  - P1
parent: CARD-438
---

# [CARD-445] Tutor Education-Mode Default Turn Budget (Pack / Profile Default Above 10)

> **Status**: Ready
> **Created**: 2026-09-23
> **Observed during**: CARD-438 live-test — Tutor `platform-packs/tutor/pack.json` omits `max_turns`, so runtime defaults to 10; Learning OS quiz/flashcard tool loops can exhaust that budget even when Agent Studio persistence works.
> **ADR Reference**: none
> **Labels**: `type:feature`, `area:tutor`, `area:agents`, `P1`
> **Parent**: [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md)
> **Related**: [CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md); [CARD-443](./CARD-443-platform-tutor-pack-appdata-sync.md)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Lock the default number and who inherits it — **still no product code** |
| **`build`** | Ship an explicit Tutor (education-mode) default `max_turns` in the platform pack / seed path |
| **`merge to qa`** | After In Review + proof that a fresh Tutor install gets the new default and Studio can still override |

Do **not** write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | CARD-438 hotfix for Agent Studio max_turns persistence (grandfather pack tools on PUT) |
| **Related** | [CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md) reduces tool sprawl; this card sets a sane pack default, not a skill rewrite |
| **Related** | [CARD-443](./CARD-443-platform-tutor-pack-appdata-sync.md) so pack.json default reaches AppData |
| **Blocked by** | Nothing for docs; implementation should not overwrite `user_modified` Tutor overrides |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Fresh Tutor should not start Learning OS turns at a hidden default of 10 if education-mode turns routinely need more ReAct steps.
2. Operator overrides in Agent Studio must still win; the pack default is only the seed when no override exists.

### Beat 2: What AutoReiv does now

1. `AgentProfile.max_turns` defaults to 10 (`src/domain/kernel/models.py`, ge=1, le=1000).
2. `platform-packs/tutor/pack.json` has **no** `max_turns` field; AppData `packs/tutor/pack.json` likewise often omits it.
3. Kernel loop uses `agent.max_turns` (`src/application/kernel/agent_kernel.py`); budget stop text is `Execution terminated: Max turn budget of {agent.max_turns} reached.`
4. Agent Studio Save persists `max_turns` via PUT `/api/agents/{id}` into overrides + pack.json when present; CARD-438 hotfix grandfathers existing pack tools so Save is not blocked by catalog mount lag.

### Beat 3: What will change

1. Set an explicit `max_turns` on the Tutor platform pack (candidate default **40** or **50** — lock at **build** after one flashcard + one quiz live count).
2. Ensure seed/import applies that default for non-`user_modified` Tutor without clobbering operator overrides.
3. Document that runtime always reads the profile value (not a second hardcoded education-mode budget).
4. Optional: surface the effective budget in education-mode chrome once — not required for this card's minimum.

**Out of scope:** Flashcard skill rewrite ([CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md)); hash-gated AppData sync implementation ([CARD-443](./CARD-443-platform-tutor-pack-appdata-sync.md)); changing the global AgentProfile default for all agents; Learning OS redesign.

### Beat 4: What dies today

1. Silent Tutor default of 10 with no pack-declared budget for education-mode tool loops.
2. Confusion that education mode has a separate hardcoded budget of 10 (it does not — it uses `agent.max_turns`).

---

## 2. Acceptance criteria

- **[REQ-445-001]** WHEN Tutor is seeded from `platform-packs/tutor` with no user override, THE PROFILE SHALL expose an explicit `max_turns` equal to the pack-declared education-mode default (value locked at build).
- **[REQ-445-002]** WHEN the operator has saved a different `max_turns` in Agent Studio (`user_modified`), THE SYSTEM SHALL keep that override across restart.
- **[REQ-445-003]** WHEN a Tutor chat turn hits the budget, THE MESSAGE SHALL report the profile's `max_turns` (the same value Agent Studio shows).
- **[REQ-445-004]** THE PROOF SHALL show a fresh Tutor (no override) GET `/api/agents/tutor` returning the new default, and a Studio override of 100 still sticking after reload.

---

## 3. Proof / live-test notes

1. On a clean Tutor (clear override or fresh data dir fixture), confirm GET max_turns equals pack default.
2. Set 100 in Agent Studio; Save; reload; confirm 100.
3. Run one Learning OS turn; if budget stop appears, confirm N matches the profile.
4. Automated: pack manifest asserts `max_turns`; API persistence test already covers override path.

---

## 4. Constraints

- Docs-only until **build**.
- Do not overwrite user-modified Tutor packs.
- No `main` merge, no GitHub PR, no version bump for docs-only.

---

## 5. Reply phrases

- Lock the default number: say **continue**.
- Start implementation: say **build**.
- After live proof: say **merge to qa**.
