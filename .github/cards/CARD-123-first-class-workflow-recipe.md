# [CARD-123] First-class Workflow (the recipe)

> **Status**: Done
> **Created**: 2026-08-30
> **Spec Reference**: CARD-096; CARD-099; CARD-106; CARD-114 Finding 16; CARD-117; CARD-118; CARD-120; CARD-121
> **Labels**: `type:feat`, `type:docs`

---

## 1. Why / Intent
**Workflow is a first-class recipe.** It is not a skill. It is not Goal.

Instantiating a workflow creates a **Job** with **Phase** rows.

**Walked (2026-08-30 Jacob t161-t164u):** Workflow = reusable plan. It lives with the agent who **starts** it. The picker is in **Chat**, next to Goal and Verify, and shows only that agent's startable recipes. Do not force workflows day one; an empty picker is correct until a plan is worth repeating. Primary birth: Goal checkbox (one-off planner, already produces linear phases) then a Chat control **Save as workflow** after a plan/run you like. That populates the picker. New user prompt + picked workflow = new Job, same chapters, different facts. Goal is the **factory**, not already a workflow. AutoReiv today: Goal plans phases; there is **no save** and **no picker**. CARD-123 is that object.

This card is **alignment / lock**. Not a coding card. Do not implement product Python/JS. Do not name inspiration products.

Start in Chat. Edit later optional in Agent Studio on the owner. **No Workflow Studio.** Skills Studio is not the house (CARD-118). Pickup **after CARD-117 / CARD-121 / CARD-120**.

CARD-114 Finding 16: workflows / job templates are missing today. Goal checkbox is standing in. `propose_workflow` parks a HITL draft; it does not start a Job.

---

## 2. What to Build
Product implementation (this pickup). Alignment lock in section 8 still stands.

- Persist a workflow recipe on the starting agent (JSON under `$DATA_DIR/agents/<agent_id>/workflows/`).
- Chat: Workflow picker next to Goal and Verify; empty/disabled until this agent has a saved recipe.
- After a Goal-planned job (2+ phases): Save as workflow (name the recipe). Store chapters, not instance facts / transcript blobs.
- Picking a workflow + sending a new user message instantiates a Job already holding those Phase rows.
- Agent Studio: small list on the selected agent (name + ordered chapters; edit/delete). No Workflow Studio.
- Do not replace Goal. Do not auto-convert every Goal plan. Do not build Agent Packs, memory, or live Okta.


- Record the primitive: Workflow = reusable plan (the recipe). Instantiating it creates a Job with Phase rows.
- Record the t161-t164u walk (section 8): lives with the agent who starts it; Chat picker next to Goal and Verify; do not force day one; Goal then Save as workflow is the primary birth; Goal is the factory; start in Chat, optional Agent Studio edit; no Workflow Studio; one object (phase = skill or handoff); save chapter list not instance facts; pickup after 117/121/120; Skills Studio is not the house (CARD-118).
- Explicit: not a skill (CARD-117 runbook). Not Goal (one-off planner checkbox / factory). Not a new graph runtime. Not a separate multi-agent type.
- Cheat-sheet lock (section 5): workflow (recipe) vs job (this run) vs phase (chapter).
- Example (section 6): HR new-employee-onboarding. Same chapters, different facts (Jane vs Bob). Does not require live HR.
- Change list stub (section 7): object is missing today; Goal plans phases; there is no save and no picker.
- Pickup after CARD-117, CARD-121, CARD-120.
- CHANGELOG Unreleased note that this walk was recorded.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Written alignment: Workflow is a first-class reusable plan. Instantiating it creates a Job with Phase rows.
- [ ] Explicit: not a skill. Not Goal. Not a new graph runtime. Goal is the factory, not already a workflow.
- [ ] Lives with the agent who starts it. Picker in Chat next to Goal and Verify (only that agent's startable recipes). Start in Chat. Optional later edit in Agent Studio on the owner. No Workflow Studio. Skills Studio is not the house (CARD-118).
- [ ] Cheat-sheet lock is recorded (section 5): workflow (recipe) vs job (this run) vs phase (chapter). Save the chapter list, not the instance facts.
- [ ] HR new-employee-onboarding example is recorded (section 6) without requiring live HR. Same chapters, different facts (Jane vs Bob).
- [ ] Change list stub is recorded (section 7): object is missing today; Goal plans phases; there is no save and no picker.
- [ ] Walked 2026-08-30 (Jacob t161-t164u) lock is recorded (section 8, not built): reusable plan; Chat picker; do not force day one; Save as workflow after Goal; factory vs recipe; Chat-first; no Workflow Studio; one object (skill vs handoff phase); chapter list not facts; pickup after 117/121/120; CARD-118.
- [ ] Pickup after CARD-117 / CARD-121 / CARD-120 is explicit.
- [x] Product Python/JS landed. Live-test pass (Jacob 2026-08-30: it feels great). Status **Done**. Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Done** (live-test pass 2026-08-30). Local commit only. No push.
- Work on `qa`. Do not push. Do not clone.
- Product code is in scope for this pickup. Do not add a graph runtime. Do not add a Workflow Studio. Do not put this in Skills Studio (CARD-118).
- Pickup after CARD-117 (skill = runbook), CARD-121 (tool = one callable), CARD-120 (Python rename). CARD-118 is the one-Agent-Studio lock. CARD-119 Agent Packs stay later-discuss.
- Do not force workflows day one. Empty picker is correct until a plan is worth repeating.
- Do not name inspiration products.
- Walked 2026-08-30 (section 8) is a lock of **intent**, not a build-now.

---

## 5. Cheat-sheet lock

Do not mix these words.

- **workflow** = the recipe (reusable plan). You instantiate it. Lives with the agent who starts it.
- **job** = this run. One instance of work happening now. New prompt + picked workflow = new Job, same chapters, different facts.
- **phase** = a chapter of that run. A phase is "I run this skill" or "handoff to that agent". Not skill steps. Not the recipe itself.

Skill (CARD-117) stays one `SKILL.md` runbook (order / pitfalls / done-when). Goal stays a one-off planner checkbox (the **factory**), not a saved recipe. Save the **chapter list**, not the instance facts.

Single-agent workflow only if you need ticket checkpoints; otherwise skill steps + ReAct.

---

## 6. Example (no live HR)

**HR new-employee-onboarding.** A recipe you can instantiate again for the next hire.

Instantiating creates a Job with Phase rows, for example: create account, assign laptop, grant apps, send welcome.

Same chapters, different facts (Jane vs Bob).

Does **not** require a live HR system. Teaching shape only. No live Okta. No credentials.

---

## 7. Change list stub (not build-now)

Object is **missing today**.

- Goal checkbox is a one-off planner (CARD-099): asks for linear phases, persists Job+Phases. It is the **factory**, not already a workflow. There is **no save** and **no picker**.
- Every chat is a Job named Chat (CARD-096 / CARD-099 default one-job-one-phase).
- `propose_workflow` (CARD-106) is a HITL draft SOP, not this object. It does not start a Job.
- `$DATA_DIR/templates/jobs` is created empty. No YAML runner.
- Do not put Workflow in Skills Studio (CARD-118: drop the standalone pack editor; one Agent Studio). No Workflow Studio. Start in Chat; optional later edit in Agent Studio on the owner.
- Do not add a graph runtime. Linear Job + Phase rows are enough.
- Do not add a separate multi-agent type: one object; a phase is skill or handoff.

---

## 8. Walked 2026-08-30 (Jacob t161-t164u)

Locked. **Not build-now.** No product Python/JS. Status stays **Ready**.

1. **Workflow = reusable plan.** Lives with the agent who **starts** it. Picker in **Chat** next to Goal and Verify. Only that agent's startable recipes.

2. **Do not force workflows day one.** Empty picker is correct until a plan is worth repeating.

3. **Primary birth:** Goal checkbox (one-off planner, already produces linear phases) then a Chat control **Save as workflow** after a plan/run you like. That populates the picker. New user prompt + picked workflow = new Job, same chapters, different facts (Jane vs Bob).

4. **AutoReiv today:** Goal plans phases. There is **no save** and **no picker**. CARD-123 is that object. Goal is the **factory**, not already a workflow.

5. **Start in Chat.** Edit later optional in Agent Studio on the owner (chapter list, who, skill vs handoff). **No Workflow Studio.** No separate multi-agent type: one object; a phase is "I run this skill" or "handoff to that agent". Single-agent workflow only if you need ticket checkpoints; otherwise skill steps + ReAct.

6. **Save the chapter list, not the instance facts.**

7. **Pickup after CARD-117 / CARD-121 / CARD-120.** Skills Studio is not the house (CARD-118).
