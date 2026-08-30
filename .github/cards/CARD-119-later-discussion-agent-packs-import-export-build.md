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

**Later talk (2026-08-30 t153u) — side thought (do not start Agent Packs until foundations walked):** When Agent Packs are eventually implemented, the **shipped core roster is two agents: Assistant and AutoReiv**. Specialists (Coding, Conductor, Review, Agent Builder, Okta Admin, EUC, etc.) should arrive as **Agent Packs** (agent + its skills + its tools), not as more builtins baked into the platform forever. This keeps the system true: core talk-to-the-human + platform agent; everything else is a pack you import.

Do **not** delete or rip existing builtins on this card. Capture intent only. Foundations first (CARD-117, 121, 120, workflow later). Memory CARD-116 last. CARD-122 three-beats skill is unrelated low-priority.

Controls (not this card to build): Agent Studio has two checkbox groups per agent — pack-owned skills/tools vs a small **platform** group (e.g. wiki_read default on, wiki_write off). Untick MUST omit that schema from context. No RBAC engine. No in-flight dynamic mapper. Handoff uses an agent name+blurb directory, not nested full tool/skill schemas of other agents.

---

## 2. What to Build
Discussion placeholder only. Do not implement product Python/JS on this card. Do not add import/export/build UI.

- Record the concept: an Agent Pack bundles one agent + its skills + its tools for ship/import/export.
- Explicit: **not** a fourth primitive. **Not** a Skill Pack renamed.
- Example only: Okta Admin bundle (agent + user-provisioning runbook + atomic tools).
- Record t153u intent: core ship roster is Assistant + AutoReiv; specialists arrive as packs later. Do not rip existing builtins here.
- Record controls intent (not to build here): two Agent Studio checkbox groups (pack-owned vs small platform group); untick omits schema; no RBAC engine; no in-flight dynamic mapper; handoff is name+blurb directory.
- Discuss after agent/skill/tool foundations. No build on this card.
- CHANGELOG Unreleased note that this backlog card opened / intent expanded.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Agent Pack is recorded as later packaging (import/export/build), not a fourth primitive.
- [ ] Example is recorded: ship an agent with its skills and tools (e.g. Okta Admin bundle).
- [ ] t153u intent is recorded: shipped core roster is Assistant + AutoReiv; specialists (Coding, Conductor, Review, Agent Builder, Okta Admin, EUC, etc.) arrive as Agent Packs, not more forever-builtins. Do not delete/rip existing builtins on this card.
- [ ] Controls intent is recorded (not this card to build): two Agent Studio checkbox groups per agent (pack-owned skills/tools vs small platform group, e.g. wiki_read default on, wiki_write off); untick MUST omit that schema from context; no RBAC engine; no in-flight dynamic mapper; handoff uses agent name+blurb directory, not nested full tool/skill schemas of other agents.
- [ ] Explicit: not build-now; do not start Agent Packs until foundations walked (CARD-117, 121, 120, workflow later). Memory CARD-116 last. CARD-122 is unrelated low-priority.
- [ ] No product Python/JS. Status stays **Ready** (backlog). Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code. Do not add pack import/export/build.
- Do not treat this as a Skill Pack. Skill Pack is not the primitive (CARD-117).
- Do **not** delete or rip existing builtins on this card. Capture intent only.
- Foundations first: CARD-117 (skill = runbook), CARD-121 (tools), CARD-120 (Python rename), then workflow later. Then studio rethink (CARD-118), then this discussion. Memory CARD-116 last. CARD-122 three-beats skill is unrelated low-priority.
- Controls notes here are intent only. Do not build Agent Studio checkbox groups, RBAC, a dynamic mapper, or handoff-directory changes on this card.

---

## 5. Later talk (2026-08-30 t153u): core roster + packs later

Jacob side thought. Do **not** start Agent Packs until foundations are walked.

### 5.1 Shipped core roster is two agents

When Agent Packs are eventually implemented, the **shipped core roster is two agents: Assistant and AutoReiv**.

- **Assistant**: talk-to-the-human.
- **AutoReiv**: platform agent.

Specialists (Coding, Conductor, Review, Agent Builder, Okta Admin, EUC, etc.) should arrive as **Agent Packs** (agent + its skills + its tools), not as more builtins baked into the platform forever.

This keeps the system true: core talk-to-the-human + platform agent; everything else is a pack you import.

### 5.2 Do not rip existing builtins on this card

Capture intent only. Do **not** delete or rip existing builtins here.

Pickup order stays: foundations first (CARD-117, 121, 120, workflow later). Memory CARD-116 last. CARD-122 three-beats skill is unrelated low-priority.

### 5.3 Controls (not this card to build)

Intent only. Do not implement on this card.

- Agent Studio has two checkbox groups per agent:
  - pack-owned skills/tools
  - a small **platform** group (e.g. wiki_read default on, wiki_write off)
- Untick MUST omit that schema from context.
- No RBAC engine.
- No in-flight dynamic mapper.
- Handoff uses an agent name+blurb directory, not nested full tool/skill schemas of other agents.
