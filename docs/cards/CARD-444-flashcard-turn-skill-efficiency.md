---
id: CARD-444
title: "Flashcard-Turn Skill Efficiency (Stop Burning Turn Budget on Wiki Side Quests)"
status: In Review
created: 2026-09-23
adr: none
labels:
  - type:bug
  - area:tutor
  - area:education
  - P1
parent: CARD-438
---

# [CARD-444] Flashcard-Turn Skill Efficiency (Stop Burning Turn Budget on Wiki Side Quests)

> **Status**: In Review
> **Created**: 2026-09-23
> **Observed during**: CARD-438 live-test on Jarvis — flashcard chat hit `Max turn budget of 10 reached` after `wiki_note_create` succeeded; quiz turns completed.
> **ADR Reference**: none
> **Labels**: `type:bug`, `area:tutor`, `area:education`, `P1`
> **Parent**: [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md)
> **Related**: [CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine the minimal tool loop / skill wording — **still no product code** |
| **`build`** | Tighten flashcard-turn (and sibling Learning OS skills if needed) so one card fits under the turn budget |
| **`merge to qa`** | After In Review + live flashcard proof under the default budget |

Do **not** write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md) durable `education_flashcard_*` tools |
| **Related** | [CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md) for pack/default budget; do not redesign Learning OS here |
| **Blocked by** | Nothing once CARD-438 tools are live |
| **Unlocks** | Reliable one-card flashcard turns without raising max_turns as a crutch |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. A single flashcard-turn in Tutor education mode must finish (select card → prompt → grade → honest report) without exhausting the ReAct turn budget on unrelated Wiki writes.
2. The skill should prefer `education_flashcard_next` / `education_flashcard_grade` (and mastery due/upsert only when seeding), not open-ended wiki curation mid-turn.

### Beat 2: What AutoReiv does now

1. `platform-packs/tutor/skills/flashcard-turn/SKILL.md` declares a 4-step turn shape and lists `education_flashcard_next`, `education_flashcard_grade`, `education_mastery_due`, `education_mastery_upsert`, plus Wiki list/search/read/template tools.
2. Tutor pack also allows `education-wiki-curation` with `wiki_note_create` / `wiki_note_update`. Live flashcard chat on Jarvis showed `wiki_note_create` succeeding, then `Execution terminated: Max turn budget of 10 reached` before a durable flashcard grade completed.
3. Runtime budget is `agent.max_turns` in `src/application/kernel/agent_kernel.py` (message: `Max turn budget of {agent.max_turns} reached.`). Default profile/pack omission yields 10.

### Beat 3: What will change

1. Tighten flashcard-turn runbook (and pack skill tool list if needed) so the happy path is at most a small fixed tool count: next/due → (optional one seed upsert) → grade → stop.
2. Explicitly forbid mid-turn `wiki_note_create` / curation / multi-note search loops unless the due ledger is empty and seeding requires a single targeted read of an `education-flashcard` note.
3. Add an automated or deterministic proof that a seeded due card completes under the default Tutor max_turns without hitting the budget terminator.
4. Do **not** redesign Learning OS rails, quiz-turn pedagogy, or Studio UX here.

**Out of scope:** Raising platform default max_turns ([CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md)); Agent Studio persistence (hotfixed on CARD-438 branch); pack AppData sync ([CARD-443](./CARD-443-platform-tutor-pack-appdata-sync.md)); Learning OS redesign.

### Beat 4: What dies today

1. Flashcard turns that burn the whole budget on Wiki side quests and never call `education_flashcard_grade`.
2. Treating a higher max_turns slider as the only fix for an inefficient skill loop.

---

## 2. Acceptance criteria

- **[REQ-444-001]** WHEN Tutor runs `flashcard-turn` with at least one due mastery item, THE SYSTEM SHALL complete select → prompt → `education_flashcard_grade` without invoking `wiki_note_create`.
- **[REQ-444-002]** WHEN the due ledger is empty, THE SYSTEM MAY seed with at most one targeted Wiki read + `education_mastery_upsert` (or extract equivalent), then grade; it SHALL NOT open a multi-note curation loop inside the same flashcard turn.
- **[REQ-444-003]** WHEN a seeded due card is presented under Tutor's default `max_turns`, THE TURN SHALL finish without emitting `Execution terminated: Max turn budget of N reached.`
- **[REQ-444-004]** THE PROOF SHALL record tool-call names for one successful flashcard turn and show the budget terminator is absent.

---

## 3. Proof / live-test notes

1. Seed one due flashcard via `education_mastery_upsert` / mastery due.
2. Enter Tutor education mode; invoke flashcard-turn; answer once.
3. Confirm tools used are the education flashcard/mastery set (no `wiki_note_create` on the happy path); confirm durable `next_due` / grade in mastery.
4. Confirm no max-turn budget termination message.

---

## 4. Constraints

- **build** received; implementation on feat branch. No merge to qa until Jacob says **merge to qa**.
- No Learning OS redesign; skill/runbook and allowlist tightening only.
- No merge to `main`, no GitHub PR, no version bump for docs-only.

---

## 5. Reply phrases

- Refine the minimal loop: say **continue**.
- Start implementation: say **build**.
- After live proof: say **merge to qa**.

---

## 6. Implementation note (In Review)

- Tightened platform-packs/tutor/skills/flashcard-turn/SKILL.md (v1.2.0): minimal next→grade loop; forbid mid-turn wiki_note_create / curation / multi-note search; front-only then grade; honest failures.
- pack.json flashcard-turn tools dropped wiki_note_search / wiki_note_list (seed keeps wiki_note_read + wiki_template_list). System prompt CARD-444 clause.
- Contract: 	ests/unit/education/test_card444_flashcard_turn_skill_efficiency.py.
- Prefer platform pack; AppData lag is CARD-443 (separate). No max_turns raise (CARD-445 separate). No Studio player redesign (CARD-448 Done).
- After live flashcard proof under default budget: say **merge to qa**.
