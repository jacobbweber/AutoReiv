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

**Later talk (same day):** skills is where Jacob went wrong by far. Do **not** get confused by the current AutoReiv skills implementation. Revisit from the ground up. Align implementation, controls, and surface features to this primitive. Section 5 records that intent so later work can pick it up. See also CARD-118 (studio freeze/replace), CARD-119 (Agent Packs later), CARD-120 (Python `*Skill` rename).

---

## 2. What to Build
Alignment only. Do not implement product Python/JS on this card.

- Record the primitive: Skill = one `SKILL.md` runbook, not a pack, not a worker.
- Progressive disclosure contract: name + blurb first; body on demand when the task matches.
- Allowlist tools still reach the model every turn (they are not hidden inside the skill).
- Stop using Skill Pack as the name of this primitive.
- Account for CARD-114 findings and Hermes `06-skills.md`.
- Record the 2026-08-30 later talk as open questions / later work (section 5): ground-up rebuild vs current implementation; two explicit per-agent lists (tools + skills); load path (inject name+blurb every turn vs today's list-then-open); where on/off levers live; built-in vs user-added file location; surface features stay off this card.
- CHANGELOG Unreleased note that this backlog card opened / intent expanded.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Written alignment: Skill = one `SKILL.md` runbook (order, pitfalls, done-when), not a skill pack, not a worker.
- [ ] Example is recorded: Okta Admin = AGENT; user provisioning = SKILL with atomic TOOLS per step.
- [ ] Progressive disclosure is name + description first, not the body. Skill index is name + blurb only.
- [ ] Explicit: tools on the agent allowlist still go to the model every turn; do not treat in-skill tool lists as hidden from the model.
- [ ] The phrase Skill Pack is not used for this primitive.
- [ ] CARD-114 findings and Hermes `06-skills.md` (`D:\Projects\research\hermes_research`) are pointed at.
- [ ] Later talk is recorded (not answered): current implementation is not the definition; two per-agent lists; load path right vs today; levers in Agent Studio not Skills Studio; built-in vs user-added; no studio/Okta/packs on this card. Cross-links CARD-118, CARD-119, CARD-120.
- [ ] No product Python/JS. Status stays **Ready** (backlog). Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code. Do not write Python/JS for the product.
- Foundations first: lock this primitive before studio features, Agent Packs, or Python module renames (CARD-118, CARD-119, CARD-120).
- Do not treat current `$DATA_DIR/skills` "packs" or Python `*Skill` classes as the definition of this primitive.
- Do not invent answers to section 5 open questions. Record them so later work can pick them up.

---

## 5. Later talk (2026-08-30): ground-up revisit

Jacob: skills is where he went wrong by far. Do **not** get confused by the current AutoReiv skills implementation. Revisit from the ground up. Align **implementation**, **controls**, and **surface features** to the primitive in sections 1–4.

These are **open questions / later work items**, not answers.

### 5.1 Ground-up: current pieces are likely off

Current AutoReiv Skills Studio, `$DATA_DIR/skills` packs, `list_user_skill_packs` + `skill_view`, Python `*Skill` classes, and the leftover orchestration field `skills: List[str]` ("authorized skill pack tags or tools") are **not** the definition of this primitive. Treat them as likely off. Rebuild the primitive first, then map or replace those pieces.

### 5.2 Controls / allowlists (does "RBAC" even make sense?)

Two explicit per-agent lists, not one mixed bag.

- **Tools per agent:** already Forge checkboxes in Agent Studio (the tool allowlist).
- **Skills per agent:** MISSING today. Whoever has tools `list_user_skill_packs` and `skill_view` (builtin Assistant, AutoReiv, Agent Builder only) can list ALL packs under `%LOCALAPPDATA%\AutoReiv\skills`. Coding / Conductor / Review do not even have those tools.

Decide later whether to keep calling this RBAC or just "explicit skills list + explicit tools list" on the agent. Do not build a heavy RBAC system by default.

### 5.3 Load path (right vs today)

- **Right:** for skills this agent is allowed, inject name + short description into the prompt every turn (the menu). Body of `SKILL.md` only when the model opens it (`skill_view` / equivalent). Tools on that agent's list still send full schemas every turn; they are not hidden inside the skill.
- **Today:** names are NOT auto-injected. Model must call `list_user_skill_packs` first, then `skill_view` for the body. That extra list call is off vs Hermes.

### 5.4 Where the on/off levers live (UI)

- **Tool on/off:** Agent Studio / Forge checkboxes (exists).
- **Skill on/off:** should live next to the agent (same Agent Studio idea: this agent may use these runbooks). Not Skills Studio as the RBAC surface.
- **Skills Studio (CARD-118)** is the editor of runbook files, currently premature; freeze/replace, do not grow it as the control plane.

### 5.5 Where the code / files should live

Jacob may want built-in vs added-later separated.

- **Built-in:** ships with the product (seed runbooks vs Python tool groups must not share the word skill — CARD-120).
- **User-added:** data dir (`%LOCALAPPDATA%\AutoReiv\skills` today). Keep product code and user files distinct.
- Later packaging of an agent + its skills + its tools is **CARD-119 Agent Packs**, not this primitive.

### 5.6 Surface features stay off this card

Do not add Skills Studio features, live Okta, or Agent Packs on this card. Foundations first.

Cross-links: CARD-118 (studio freeze/replace), CARD-119 (Agent Packs later), CARD-120 (Python `*Skill` rename).
