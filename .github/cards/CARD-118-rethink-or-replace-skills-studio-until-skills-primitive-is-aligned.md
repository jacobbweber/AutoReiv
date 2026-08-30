# [CARD-118] Rethink or replace Skills Studio until skills primitive is aligned

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: docs/specs/user-intent-review/findings.md (Findings 15, 17); CARD-105, CARD-113
> **Labels**: `type:docs`

---

## 1. Why / Intent
Jacob's original Skills Studio was **organizing before definitions were solid**. The skills primitive is now being aligned (CARD-117: Skill = one `SKILL.md` runbook, not a pack, not a worker). Until that lands, big studio features should freeze.

Likely **drop or replace later**. This card captures that intent and what the current studio actually edits today, so later work does not keep growing the wrong UI.

This card is **alignment / freeze**. It is not a coding card and does not add studio features.

CARD-117 now owns ground-up controls/levers/code-location; this card stays freeze/replace studio.

---

## 2. What to Build
Capture-and-freeze only. Do not implement product Python/JS on this card. Do not add studio features.

- Record that the current Skills Studio edits `$DATA_DIR/skills` `SKILL.md` packs (CARD-105 list/edit; CARD-113 archive/confirm-delete). Disk is the source of truth. Python builtins (WikiSkill, execute_code, handoff) stay out of that list.
- Freeze big studio features until CARD-117 (skills primitive = runbook) is aligned.
- Later: rethink or replace the studio; do not assume the current pack editor is the product.
- CARD-114 Finding 15 (three places that look like skills) and Finding 17 (catalog is list-then-open) stay in scope as reasons the UI is confusing.
- CHANGELOG Unreleased note that this backlog card opened.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Card records that current Skills Studio edits `$DATA_DIR/skills` `SKILL.md` packs (not Python builtins).
- [ ] Freeze is explicit: no big studio features until the skills primitive (CARD-117) is aligned.
- [ ] Later drop/replace is on the table; this card does not commit to keeping the current studio.
- [ ] CARD-114 Findings 15 and 17 are pointed at.
- [ ] No product Python/JS. Status stays **Ready** (backlog). Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code. Do not add, polish, or expand Skills Studio on this card.
- Depends on CARD-117 (primitive first). Do not treat Agent Packs (CARD-119) as a studio feature to build now.
