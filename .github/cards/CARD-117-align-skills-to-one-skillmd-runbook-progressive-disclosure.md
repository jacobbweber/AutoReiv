# [CARD-117] Align Skills to one SKILL.md runbook (progressive disclosure)

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: docs/specs/user-intent-review/findings.md; D:\Projects\research\hermes_research\06-skills.md
> **Labels**: `type:docs`, `type:refactor`

---

## 1. Why / Intent
Capture 2026-08-30 alignment: **Skill = one `SKILL.md` runbook** (order, pitfalls, done-when). It is not a "skill pack" and not a worker.

Example: **Okta Admin is an AGENT**; **user provisioning is a SKILL** with atomic **TOOLS** per step.

Progressive disclosure: the skill index is **name + description (blurb) only**. Do not dump all tools-inside-a-skill as if they were hidden. Tools on the agent allowlist still go to the model every turn. Opening a matching skill loads the runbook body.

Stop using the phrase **Skill Pack** for this primitive.

Point at CARD-114 findings (especially Findings 13-17: Okta brochure, pack tools as labels, three places that look like skills, missing workflows, catalog is list-then-open) and Hermes skills research at `D:\Projects\research\hermes_research\06-skills.md`.

This card is **alignment / docs**. It is not a coding card.

---

## 2. What to Build
Alignment only. Do not implement product Python/JS on this card.

- Record the primitive: Skill = one `SKILL.md` runbook, not a pack, not a worker.
- Progressive disclosure contract: name + blurb first; body on demand when the task matches.
- Allowlist tools still reach the model every turn (they are not hidden inside the skill).
- Stop using Skill Pack as the name of this primitive.
- Account for CARD-114 findings and Hermes `06-skills.md`.
- CHANGELOG Unreleased note that this backlog card opened.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Written alignment: Skill = one `SKILL.md` runbook (order, pitfalls, done-when), not a skill pack, not a worker.
- [ ] Example is recorded: Okta Admin = AGENT; user provisioning = SKILL with atomic TOOLS per step.
- [ ] Progressive disclosure is name + description first, not the body. Skill index is name + blurb only.
- [ ] Explicit: tools on the agent allowlist still go to the model every turn; do not treat in-skill tool lists as hidden from the model.
- [ ] The phrase Skill Pack is not used for this primitive.
- [ ] CARD-114 findings and Hermes `06-skills.md` (`D:\Projects\research\hermes_research`) are pointed at.
- [ ] No product Python/JS. Status stays **Ready** (backlog). Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code. Do not write Python/JS for the product.
- Foundations first: lock this primitive before studio features, Agent Packs, or Python module renames (CARD-118, CARD-119, CARD-120).
- Do not treat current `$DATA_DIR/skills` "packs" or Python `*Skill` classes as the definition of this primitive.
