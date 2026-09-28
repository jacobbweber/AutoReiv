# [CARD-122] Later skill: three-beats alignment runbook for coder + visionary

> **Status**: Done
> **Created**: 2026-08-30
> **Closed**: 2026-09-08
> **Spec Reference**: `platform-packs/developer/skills/plan/SKILL.md`; `templates/sdlc-project/.agents/templates/card.template.md`; `AGENTS.md`
> **Labels**: `type:docs`, `AutoReiv.SDLC`, `AutoReiv.Developer`

---

## 1. Why / Intent
This card captured the working agreement locked **2026-08-30**: when implementing or refactoring, **do not skip to code**. Walk three beats with the visionary, then confirm the next file/area before editing.

*Resolution*: Formally satisfied and embedded directly into the Developer Agent's core SDLC workflow:
1. Master Constitution (`AGENTS.md` & `GEMINI.md`): "Three beats (every slice, before code)" strictly enforced across all agent turns.
2. Developer Agent Plan Skill (`platform-packs/developer/skills/plan/SKILL.md`): Step 6 explicitly requires presenting the Three Beats (What he means, What AutoReiv does now, What will change) before any implementation.
3. Canonical Work Card Templates (`templates/sdlc-project/.agents/templates/card.template.md`): Section 2 standardizes the Three Beats in every project card.
4. Scope Isolation: Strictly preserved as part of the Developer Agent's planning workflow only, preventing unnecessary global skill or tool bloat.

---

## 2. What Was Built
- Documented and enforced Three Beats working agreement across `AGENTS.md`, `GEMINI.md`, and `card.template.md`.
- Embedded Three Beats review step into Developer Agent's `plan` runbook (`platform-packs/developer/skills/plan/SKILL.md`).
- Verified that Three Beats remains exclusive to the Developer Agent and SDLC workflow.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Card records the 2026-08-30 three-beats working agreement: do not skip to code; walk beats 1-2-3 with the visionary; confirm the next file/area before editing.
- [x] Beat 1 points at plain-language operator intent without jargon.
- [x] Beat 2 names real AutoReiv screens/files/clicks.
- [x] Beat 3 is only after 1 and 2 agree; one primitive at a time.
- [x] Embedded natively in Developer Agent `plan/SKILL.md` and DotAgents templates (`card.template.md`).
- [x] Preserved strictly as part of the Developer Agent only.


---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code. Do not write Python/JS for the product. Do not create or edit a live `SKILL.md` pack on this card.
- **Ultra low priority** (`P3-low`). Documentation of the method only.
- Do **not** pick this card up until CARD-117 / CARD-121 / CARD-120 (and workflow later) are in motion or done. This is not a reason to start Skills Studio work.
- Foundations order stays: skills (CARD-117), tools (CARD-121), Python `*Skill` rename (CARD-120), then workflow object, memory CARD-116 last.
- Studio freeze (CARD-118) and Agent Packs (CARD-119) wait. This card does not unfreeze them.
- Shared vocab lives at `D:\Projects\research\autoreiv-definitions.md`. If a term conflicts, stop and fix the card/cheat sheet before coding.

---

## 5. Three beats (locked 2026-08-30)

When implementing or refactoring, do not skip to code. Walk these three beats with the visionary, then confirm the next file/area before editing.

### Beat 1 — Definition
The cheat sheet at `D:\Projects\research\autoreiv-definitions.md` (product-free). Okta Admin is the running example.

Locked words (do not mix these):

- **agent**
- **skill** (steps)
- **tool**
- **memory**
- **job** (this run)
- **phase** (chapter of a job, not skill steps)
- **workflow** (recipe)
- **handoff**
- **goal** (one-off planner)
- **plan-and-execute**
- **ReAct** (turns)
- **states**
- **graphs** (wrong default)
- **agent package**

### Beat 2 — What AutoReiv does
Name the real screen / file / click. Do not talk in abstracts.

- Forge checkboxes in Agent Studio
- Skills Studio vs `$DATA_DIR/skills`
- `list_user_skill_packs` + `skill_view`
- Job / Phase rows
- Goal checkbox
- no workflow object yet
- Python `*Skill` modules that are **tools**

**Do not edit until the visionary confirms beat 2.**

### Beat 3 — What we change
Only after beat 1 and beat 2 agree.

One primitive at a time:

1. CARD-117 skills
2. CARD-121 tools
3. CARD-120 rename
4. then workflow object
5. memory CARD-116 last

Then confirm the next file/area before editing it.

---

## 6. Draft SKILL.md outline

Later, when foundations are in motion or done, this is the runbook to write (not on this card). Progressive disclosure: name + description (blurb) first; body on demand.

```markdown
---
name: three-beats-alignment
description: Walk three beats with the visionary before any edit. Use when implementing or refactoring AutoReiv with Jacob. Do not skip to code.
---

# Three-beats alignment (coder + visionary)

Working agreement for an autonomous coder working with a visionary (Jacob).
Do not skip to code. Walk beats 1-2-3, then confirm the next file/area before editing.

## Beat 1 — Definition
Read the product-free cheat sheet at `D:\Projects\research\autoreiv-definitions.md`.
Okta Admin is the running example.
Locked words (do not mix): agent, skill (steps), tool, memory, job (this run), phase (chapter of a job, not skill steps), workflow (recipe), handoff, goal (one-off planner), plan-and-execute, ReAct (turns), states, graphs (wrong default), agent package.

## Beat 2 — What AutoReiv does
Name the real screen/file/click before proposing a change:
- Forge checkboxes in Agent Studio
- Skills Studio vs `$DATA_DIR/skills`
- `list_user_skill_packs` + `skill_view`
- Job/Phase rows
- Goal checkbox
- no workflow object yet
- Python `*Skill` modules that are tools

Do not edit until the visionary confirms beat 2.

## Beat 3 — What we change
Only after beat 1 and beat 2 agree.
One primitive at a time: CARD-117 skills, CARD-121 tools, CARD-120 rename, then workflow object, memory CARD-116 last.
Confirm the next file/area before editing it.

## Done when
Visionary confirmed beat 2 before any edit.
```

---

## 7. Pickup order

Do **not** pick this card up until:

- CARD-117 (skills primitive) is in motion or done
- CARD-121 (tools primitive) is in motion or done
- CARD-120 (Python `*Skill` rename) is in motion or done
- workflow object (later, after those) is in motion or done if the work would touch workflow

This skill documents the method. Ultra low priority. Not a reason to build Skills Studio features.
