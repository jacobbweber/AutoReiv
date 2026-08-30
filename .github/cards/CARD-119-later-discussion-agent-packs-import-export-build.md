# [CARD-119] Later discussion: Agent Packs (import/export/build)

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: none (conceptual; after agent/skill/tool foundations)
> **Labels**: `type:docs`, `type:research`

---

## 1. Why / Intent
Later discussion: **Agent Packs** (import / export / build). Conceptual idea: ship an **agent together with its skills and tools** (example: an Okta Admin bundle).

This is **packaging**, not a fourth primitive. The primitives stay **agent**, **skill** (one runbook), and **tool**. Do not invent "Agent Pack" as a new first-class object in the kernel.

Not build-now. Discuss after agent / skill / tool foundations (CARD-117 and related) are solid.

This card is a **parking lot**. It is not a coding card.

---

## 2. What to Build
Discussion placeholder only. Do not implement product Python/JS on this card. Do not add import/export/build UI.

- Record the concept: an Agent Pack bundles one agent + its skills + its tools for ship/import/export.
- Explicit: **not** a fourth primitive. **Not** a Skill Pack renamed.
- Example only: Okta Admin bundle (agent + user-provisioning runbook + atomic tools).
- Discuss after agent/skill/tool foundations. No build on this card.
- CHANGELOG Unreleased note that this backlog card opened.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Agent Pack is recorded as later packaging (import/export/build), not a fourth primitive.
- [ ] Example is recorded: ship an agent with its skills and tools (e.g. Okta Admin bundle).
- [ ] Explicit: not build-now; discuss after agent/skill/tool foundations.
- [ ] No product Python/JS. Status stays **Ready** (backlog). Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code. Do not add pack import/export/build.
- Do not treat this as a Skill Pack. Skill Pack is not the primitive (CARD-117).
- Foundations first: CARD-117 (skill = runbook), then studio rethink (CARD-118), then this discussion.
