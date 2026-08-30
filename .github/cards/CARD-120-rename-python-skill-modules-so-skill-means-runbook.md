# [CARD-120] Rename Python Skill modules so skill means runbook

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: CARD-117; CARD-121; docs/specs/user-intent-review/findings.md (Finding 15)
> **Labels**: `type:refactor`, `type:docs`

---

## 1. Why / Intent
Python modules currently named `*Skill` (WikiSkill, GitSkill, CardSkill, and similar) are **tool groups**, not runbooks. After CARD-117, **skill in code should mean a `SKILL.md` runbook**. Those modules need rename/align so the word "skill" is not overloaded.

This is **refactor-and-alignment**. Foundations first (CARD-117 then CARD-121). **No new features** on this card.

**Walked (2026-08-30, not build-now):** section 5 is the locked rename-only plan. Do after CARD-117 and CARD-121. Do not implement on this card.

---

## 2. What to Build
Rename/align only, and only after the skills primitive (CARD-117) and the tools primitive (CARD-121) are aligned. Do not add features. Do not implement on this card until those foundations are accepted.

- Inventory Python modules/classes currently called skills (WikiSkill, GitSkill, CardSkill, AgentBuilderSkill, etc. under `src/application/skills/`).
- Treat those as **tool groups** (callable actions), not runbooks.
- Rename/align so `skill` in code means one `SKILL.md` runbook.
- No new features, no behavior change beyond naming/alignment.
- `wiki_read` vs `wiki_write` split belongs to CARD-121, not extra scope here.
- Record the 2026-08-30 walked rename-only lock (section 5, not build-now).
- CHANGELOG Unreleased note that this walk was recorded.
- Local commit only. Do not push. (When this card is later executed: still no new features.)

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Inventory of Python `*Skill` modules/classes exists (WikiSkill, GitSkill, CardSkill, and the rest under `src/application/skills/`).
- [ ] Those modules are treated as tool groups, not runbooks.
- [ ] Rename/align plan (and later code) makes `skill` mean a `SKILL.md` runbook.
- [ ] Walked 2026-08-30 rename-only lock is recorded (section 5, not built): after CARD-117 and CARD-121; no new features; no behavior change; `wiki_read` vs `wiki_write` is CARD-121 scope, not extra here.
- [ ] No new features on this card. Foundations (CARD-117 then CARD-121) first.
- [ ] No product Python/JS while this card is backlog. Status stays **Ready** until foundations are aligned. Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress until CARD-117 and CARD-121 are aligned.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code on this opening/walk commit. When later executed: refactor/rename only, no new features, no behavior change.
- Zero breaking change to tool behavior; tests stay green after any rename.
- Do not conflate this with Agent Packs (CARD-119) or Skills Studio (CARD-118).
- `wiki_read` vs `wiki_write` split belongs to CARD-121. Do not pull that split into this rename card.
- Do not name inspiration products in this card (Jacob t157u).
- Walked 2026-08-30 (section 5) is a lock of **intent**, not a build-now. Do not rename Python modules on this card.

---

## 5. Walked 2026-08-30

Locked rename-only plan. **Not build-now.** No product Python/JS. Status stays **Ready**.

1. **After CARD-117 and CARD-121.** Rename-only. Do not start this card until the skill primitive (CARD-117) and the tool primitive (CARD-121) are aligned.
2. **Python `*Skill` modules are tool groups, not runbooks.** WikiSkill, GitSkill, CardSkill, and the rest under `src/application/skills/` (`wiki_skill.py`, `git_skill.py`, `card_skill.py`, etc.) group callable tools. They are not `SKILL.md` runbooks.
3. **After rename, skill in code means `SKILL.md`.** The word skill is reserved for the runbook primitive. Tool-group modules get a non-skill name.
4. **No new features, no behavior change.** Rename/align identifiers, imports, docs, and tests only. Tool behavior stays the same.
5. **`wiki_read` vs `wiki_write` split belongs to CARD-121.** Not extra scope here. Do not split, merge, or redesign those tools on this card.
