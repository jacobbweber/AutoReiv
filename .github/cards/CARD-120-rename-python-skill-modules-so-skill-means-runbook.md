# [CARD-120] Rename Python Skill modules so skill means runbook

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: CARD-117; docs/specs/user-intent-review/findings.md (Finding 15)
> **Labels**: `type:refactor`, `type:docs`

---

## 1. Why / Intent
Python modules currently named `*Skill` (WikiSkill, GitSkill, CardSkill, and similar) are **tool groups**, not runbooks. After CARD-117, **skill in code should mean a `SKILL.md` runbook**. Those modules need rename/align so the word "skill" is not overloaded.

This is **refactor-and-alignment**. Foundations first (CARD-117). **No new features** on this card.

---

## 2. What to Build
Rename/align only, and only after the skills primitive is aligned. Do not add features. Do not implement on this card until CARD-117 is accepted.

- Inventory Python modules/classes currently called skills (WikiSkill, GitSkill, CardSkill, AgentBuilderSkill, etc.).
- Treat those as **tool groups** (callable actions), not runbooks.
- Rename/align so `skill` in code means one `SKILL.md` runbook.
- No new features, no behavior change beyond naming/alignment.
- CHANGELOG Unreleased note that this backlog card opened.
- Local commit only. Do not push. (When this card is later executed: still no new features.)

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Inventory of Python `*Skill` modules/classes exists (WikiSkill, GitSkill, CardSkill, and the rest).
- [ ] Those modules are treated as tool groups, not runbooks.
- [ ] Rename/align plan (and later code) makes `skill` mean a `SKILL.md` runbook.
- [ ] No new features on this card. Foundations (CARD-117) first.
- [ ] No product Python/JS while this card is backlog. Status stays **Ready** until foundations are aligned. Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress until CARD-117 is aligned.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code on this opening commit. When later executed: refactor/rename only, no new features.
- Zero breaking change to tool behavior; tests stay green after any rename.
- Do not conflate this with Agent Packs (CARD-119) or Skills Studio (CARD-118).
