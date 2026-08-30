# [CARD-123] First-class Workflow (the recipe)

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: CARD-096; CARD-099; CARD-106; CARD-114 Finding 16; CARD-117; CARD-118; CARD-120; CARD-121
> **Labels**: `type:docs`, `type:refactor`

---

## 1. Why / Intent
**Workflow is a first-class recipe.** It is not a skill. It is not Goal.

Instantiating a workflow creates a **Job** with **Phase** rows.

It lives **next to jobs**, not in Skills Studio. UI home is **Agent Studio** (or later a section on that screen). This is **not** a new graph runtime.

Pickup **after CARD-117 / CARD-121 / CARD-120**. This card is alignment / lock. Not a coding card. Do not implement product Python/JS. Do not name inspiration products.

CARD-114 Finding 16: workflows / job templates are missing today. Goal checkbox is standing in. `propose_workflow` parks a HITL draft; it does not start a Job.

---

## 2. What to Build
Alignment only. Do not implement product Python/JS on this card.

- Record the primitive: Workflow = the recipe. Instantiating it creates a Job with Phase rows.
- Explicit: not a skill (CARD-117 runbook). Not Goal (one-off planner checkbox). Not a new graph runtime.
- Lives next to jobs. Agent Studio / later a section. Not Skills Studio (CARD-118 drops the standalone pack editor).
- Cheat-sheet lock (section 5): workflow (recipe) vs job (this run) vs phase (chapter).
- Example (section 6): HR new-employee-onboarding. Does not require live HR.
- Change list stub (section 7): object is missing today. Goal checkbox is a one-off planner. Every chat is a Job named Chat.
- Pickup after CARD-117, CARD-121, CARD-120.
- CHANGELOG Unreleased note that this backlog card opened.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Written alignment: Workflow is a first-class recipe. Instantiating it creates a Job with Phase rows.
- [ ] Explicit: not a skill. Not Goal. Not a new graph runtime.
- [ ] Lives next to jobs, not in Skills Studio. Agent Studio / later a section.
- [ ] Cheat-sheet lock is recorded (section 5): workflow (recipe) vs job (this run) vs phase (chapter).
- [ ] HR new-employee-onboarding example is recorded (section 6) without requiring live HR.
- [ ] Change list stub is recorded (section 7): object is missing today; Goal checkbox is a one-off planner; every chat is a Job named Chat.
- [ ] Pickup after CARD-117 / CARD-121 / CARD-120 is explicit.
- [ ] No product Python/JS. Status stays **Ready** (backlog). Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code. Do not write Python/JS for the product. Do not add a graph runtime. Do not put this in Skills Studio.
- Pickup after CARD-117 (skill = runbook), CARD-121 (tool = one callable), CARD-120 (Python rename). CARD-118 is the one-Agent-Studio lock. CARD-119 Agent Packs stay later-discuss.
- Do not name inspiration products.
- Walked lock here is **intent**, not a build-now.

---

## 5. Cheat-sheet lock

Do not mix these words.

- **workflow** = the recipe (reusable). You instantiate it.
- **job** = this run. One instance of work happening now.
- **phase** = a chapter of that run. Not skill steps. Not the recipe itself.

Skill (CARD-117) stays one `SKILL.md` runbook (order / pitfalls / done-when). Goal stays a one-off planner checkbox, not a saved recipe.

---

## 6. Example (no live HR)

**HR new-employee-onboarding.** A recipe you can instantiate again for the next hire.

Instantiating creates a Job with Phase rows, for example: create account, assign laptop, grant apps, send welcome.

Does **not** require a live HR system. Teaching shape only. No live Okta. No credentials.

---

## 7. Change list stub (not build-now)

Object is **missing today**.

- Goal checkbox is a one-off planner (CARD-099): asks for linear phases, persists Job+Phases, not a saved recipe you can run again.
- Every chat is a Job named Chat (CARD-096 / CARD-099 default one-job-one-phase).
- `propose_workflow` (CARD-106) is a HITL draft SOP, not this object. It does not start a Job.
- `$DATA_DIR/templates/jobs` is created empty. No YAML runner.
- Do not put Workflow in Skills Studio (CARD-118: drop the standalone pack editor; one Agent Studio).
- Do not add a graph runtime. Linear Job + Phase rows are enough.
