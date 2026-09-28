# [CARD-117] Align Skills to one SKILL.md runbook (progressive disclosure)

> **Status**: Done
> **Created**: 2026-08-30
> **Spec Reference**: docs/specs/user-intent-review/findings.md
> **Labels**: `type:docs`, `type:refactor`

---

## 1. Why / Intent
Capture 2026-08-30 alignment: **Skill = one `SKILL.md` runbook** (order, pitfalls, done-when). It is not a "skill pack" and not a worker.

Example: **Okta Admin is an AGENT**; **user provisioning is a SKILL** with atomic **TOOLS** per step.

Progressive disclosure: the skill index is **name + description (blurb) only**. Do not dump all tools-inside-a-skill as if they were hidden. Tools on the agent allowlist still go to the model every turn. Opening a matching skill loads the runbook body.

Stop using the phrase **Skill Pack** for this primitive.

Point at CARD-114 findings (especially Findings 13-17: Okta brochure, pack tools as labels, three places that look like skills, missing workflows, catalog is list-then-open) and prior art studied outside this repo.

This card is **alignment / docs**. It is not a coding card.

**Later talk (same day):** skills is where Jacob went wrong by far. Do **not** get confused by the current AutoReiv skills implementation. Revisit from the ground up. Align implementation, controls, and surface features to this primitive. Section 5 records that intent so later work can pick it up. See also CARD-118 (studio freeze/replace), CARD-119 (Agent Packs later), CARD-120 (Python `*Skill` rename).

**Locked (Jacob 2026-08-30 t154u, not build-now):** controls / prompt assembly. Ditch **RBAC** as the name. Two explicit Agent Studio checkbox groups per agent (pack-owned vs platform/shared). Untick MUST omit that tool schema / skill name+blurb from model context. Prompt assembly: agent directory is name + one-line purpose only; skill index is ticked skills name+blurb; tool schemas are ticked tools only; skill body on open (`skill_view`). Section 6 is the lock. CARD-119 already owns core roster (Assistant+AutoReiv, packs later); do not duplicate or contradict that epic.

**Walked (2026-08-30, not build-now):** section 8 is the locked change list (skill checklist on AgentProfile, prompt inject, drop list-first, conceptual Okta split). Do not implement on this card.

---

## 2. What to Build
Alignment only. Do not implement product Python/JS on this card.

- Record the primitive: Skill = one `SKILL.md` runbook, not a pack, not a worker.
- Progressive disclosure contract: name + blurb first; body on demand when the task matches.
- Allowlist tools still reach the model every turn (they are not hidden inside the skill).
- Stop using Skill Pack as the name of this primitive.
- Account for CARD-114 findings and prior art studied outside this repo.
- Record the 2026-08-30 later talk as open questions / later work (section 5): ground-up rebuild vs current implementation; built-in vs user-added file location; surface features stay off this card. Controls / load path / lever home are no longer open: they are locked in section 6 (t154u).
- Record the t154u lock (section 6, not build-now): two explicit Agent Studio checkbox groups; pack-owned come ON at create/import; platform/shared default All Off except builtin Assistant and AutoReiv; untick omits context; no in-flight dynamic mapper; no DB/UI pixel spec beyond Agent Studio as the lever home.
- Record the 2026-08-30 walked change list (section 8, not build-now): `allowed_skill` ids next to Forge; pack-owned ON; platform All Off except Assistant/AutoReiv; inject ticked name+blurb; keep `skill_view` for body; drop must-call-list-first; untick omits prompt and refuses `skill_view`. File notes only (`models.py`, `user_catalog.py`, `profiles.py`). Okta split conceptual. CARD-118 / CARD-120 stay separate.
- CHANGELOG Unreleased note that this lock and the walked change list were recorded.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Written alignment: Skill = one `SKILL.md` runbook (order, pitfalls, done-when), not a skill pack, not a worker.
- [x] Example is recorded: Okta Admin = AGENT; user provisioning = SKILL with atomic TOOLS per step.
- [x] Progressive disclosure is name + description first, not the body. Skill index is name + blurb only.
- [x] Explicit: tools on the agent allowlist still go to the model every turn; do not treat in-skill tool lists as hidden from the model.
- [x] The phrase Skill Pack is not used for this primitive.
- [x] CARD-114 findings and prior art studied outside this repo are pointed at.
- [x] Later talk is recorded (not answered except where t154u locked it): current implementation is not the definition; built-in vs user-added; no studio/Okta/packs on this card. Cross-links CARD-118, CARD-119, CARD-120.
- [x] t154u lock is recorded (not built): ditch RBAC as the name; two Agent Studio checkbox groups (pack-owned ON at create/import; platform/shared All Off except builtin Assistant and AutoReiv, who keep useful platform ticks we choose); `wiki_read` and `wiki_write` are separate tools; untick MUST omit that tool schema / skill name+blurb from model context (fake lever is a bug); agent directory is name + one-line purpose only; skill index is ticked skills name+blurb; tool schemas are ticked tools only; skill body on open (`skill_view`); no in-flight dynamic mapper; no DB/UI pixel spec beyond Agent Studio as the lever home; CARD-119 roster epic not duplicated or contradicted.
- [x] Walked 2026-08-30 change list is recorded (section 8, not built): Skill = one SKILL.md; stop saying skill pack for that file; AgentProfile skill checklist (`allowed_skill` ids, today only `allowed_tool_names` in `src/domain/kernel/models.py`); pack-owned ON; platform All Off except Assistant/AutoReiv; untick omits name+blurb and refuses `skill_view`; inject ticked names+blurbs; keep `skill_view` for body; drop must-call-list-first (`user_catalog.py` already lists name+description; only Assistant/AutoReiv/Agent Builder have those tools in `profiles.py`); Okta Admin = agent, user-provisioning = skill; no live Okta; CARD-118 studio freeze; CARD-120 Python `*Skill` rename.
- [x] No product Python/JS. Status stays **Ready** (backlog). Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code. Do not write Python/JS for the product.
- Foundations first: lock this primitive before studio features, Agent Packs, or Python module renames (CARD-118, CARD-119, CARD-120).
- Do not treat current `$DATA_DIR/skills` "packs" or Python `*Skill` classes as the definition of this primitive.
- t154u is a lock of **intent**, not a build-now. Do not implement Agent Studio checkbox groups, prompt assembly, or a mapper on this card.
- Do not invent a DB/UI pixel spec beyond Agent Studio as the lever home.
- CARD-119 already has core roster Assistant+AutoReiv and packs later. Do not duplicate that epic. Do not contradict it.
- Do not invent answers to remaining section 5 open questions (file location, surface features). Controls / prompt assembly are locked in section 6.
- Walked 2026-08-30 (section 8) is a lock of **intent**, not a build-now. Do not implement `allowed_skill`, prompt inject, or `skill_view` refuse on this card.

---

## 5. Later talk (2026-08-30): ground-up revisit

Jacob: skills is where he went wrong by far. Do **not** get confused by the current AutoReiv skills implementation. Revisit from the ground up. Align **implementation**, **controls**, and **surface features** to the primitive in sections 1-4.

Controls / load path / lever home started as open questions here. They are **locked** in section 6 (Jacob 2026-08-30 t154u). Remaining items are still later work, not answers.

### 5.1 Ground-up: current pieces are likely off

Current AutoReiv Skills Studio, `$DATA_DIR/skills` packs, `list_user_skill_packs` + `skill_view`, Python `*Skill` classes, and the leftover orchestration field `skills: List[str]` ("authorized skill pack tags or tools") are **not** the definition of this primitive. Treat them as likely off. Rebuild the primitive first, then map or replace those pieces.

### 5.2 Controls / allowlists (LOCKED t154u)

Ditch **RBAC** as the name. Not a heavy RBAC system. Two explicit checkbox groups on Agent Studio per agent (not one mixed bag). See section 6.

- **Pack-owned skills/tools:** come ON when that agent/pack is created or imported. Untick still omits schema / name+blurb.
- **Platform/shared:** `wiki_read`, `wiki_write` as separate tools, etc. Default **All Off** for agents that are not builtin **Assistant** or **AutoReiv**. Users opt in. Assistant and AutoReiv keep useful platform ticks we choose.

Today: tool checkboxes already exist in Agent Studio (Forge allowlist). Skills-per-agent list is MISSING. Whoever has tools `list_user_skill_packs` and `skill_view` (builtin Assistant, AutoReiv, Agent Builder only) can list ALL packs under `%LOCALAPPDATA%\AutoReiv\skills`. Coding / Conductor / Review do not even have those tools. That current mix is not the lock.

### 5.3 Load path (LOCKED t154u)

See section 6.3. Summary:

- **Locked:** ticked skills inject name + blurb every turn (the menu). Body of `SKILL.md` only when the model opens it (`skill_view` / equivalent). Ticked tools send full schemas every turn; they are not hidden inside the skill. Unticked tools/skills MUST be omitted from context.
- **Today:** names are NOT auto-injected. Model must call `list_user_skill_packs` first, then `skill_view` for the body. That extra list call is off vs progressive disclosure (name+blurb then body).

### 5.4 Where the on/off levers live (LOCKED t154u)

- **Both groups** live on Agent Studio (same idea as today's Forge checkboxes): this agent may use these runbooks and these tools.
- Not Skills Studio as the control plane. Skills Studio (CARD-118) is the editor of runbook files, currently premature; freeze/replace, do not grow it as the control plane.
- No DB/UI pixel spec on this card beyond Agent Studio as the lever home.

### 5.5 Where the code / files should live

Jacob may want built-in vs added-later separated.

- **Built-in:** ships with the product (seed runbooks vs Python tool groups must not share the word skill - CARD-120).
- **User-added:** data dir (`%LOCALAPPDATA%\AutoReiv\skills` today). Keep product code and user files distinct.
- Later packaging of an agent + its skills + its tools is **CARD-119 Agent Packs**, not this primitive.

### 5.6 Surface features stay off this card

Do not add Skills Studio features, live Okta, or Agent Packs on this card. Foundations first.

Cross-links: CARD-118 (studio freeze/replace), CARD-119 (Agent Packs later), CARD-120 (Python `*Skill` rename).

---

## 6. Locked (Jacob 2026-08-30 t154u): controls / prompt assembly

Not build-now. No product Python/JS. No in-flight dynamic mapper. No DB/UI pixel spec beyond **Agent Studio as the lever home**.

CARD-119 already records the core roster (Assistant + AutoReiv) and specialists as packs later. Do **not** duplicate that epic here. Do **not** contradict it.

### 6.1 Two checkbox groups on Agent Studio (ditch "RBAC")

Per agent. Not a heavy RBAC engine. Not one mixed bag.

**1) Pack-owned skills/tools**

Come **ON** when that agent/pack is created or imported. Untick still omits that tool schema / skill name+blurb from the model context.

**2) Platform/shared**

`wiki_read`, `wiki_write` as **separate tools**, etc. Default **All Off** for agents that are not builtin **Assistant** or **AutoReiv**. Users opt in. Assistant and AutoReiv keep useful platform ticks we choose.

### 6.2 Untick MUST omit from model context

Untick MUST omit that tool schema / skill name+blurb from the model context. A fake lever (checkbox off but the schema or name+blurb still sent) is a **bug**.

### 6.3 Prompt assembly

- **Agent directory in context:** name + one-line purpose only (not nested tools/skills of other agents).
- **Skill index:** ticked skills, name+blurb.
- **Tool schemas:** ticked tools only.
- **Skill body:** on open (`skill_view`).

### 6.4 Out of scope on this card

- No in-flight dynamic mapper.
- No DB/UI pixel spec beyond Agent Studio as the lever home.
- Do not build these controls or the prompt-assembly path here. Record only.

---

## 7. When we pick this up

Working agreement (Jacob 2026-08-30 t131u): Jacob and Coding walk this card (and CARD-121 / CARD-120) together methodically. Do not silent-big-bang the refactor.

CARD-121 is the **sibling tools pass**, not a second definition of skill. Keep the two primitives separate in UI and code. CARD-121 has a one-line pointer at this t154u lock.

- Order: Skill primitive (this card) then Tool primitive (CARD-121) then Python `*Skill` rename (CARD-120). Studio freeze (CARD-118) and Agent Packs (CARD-119) wait. Memory is CARD-116, separate.
- Shared vocab: `D:\Projects\research\autoreiv-definitions.md` and these cards. If a term conflicts, stop and fix the card before coding.
- Full working agreement lives on CARD-121 section 7 (three beats per slice; confirm the next file/area before editing it).
- Do not re-litigate section 6 controls / prompt assembly or the section 8 walked change list when pickup starts. Those locks stand unless Jacob revises them.

---

## 8. Walked 2026-08-30

Locked change list. **Not build-now.** No product Python/JS. Status stays **Ready**.

1. **Skill = one `SKILL.md` runbook.** Stop saying skill pack for that file.
2. **Agent profile skill checklist** next to Forge: `allowed_skill` ids, same idea as `allowed_tool_names`. Today `AgentProfile` only has `allowed_tool_names` (`src/domain/kernel/models.py`).
3. **Pack-owned skills come ON** with that agent. **Platform skills default All Off** except Assistant and AutoReiv.
4. **Untick** = name+blurb not in the prompt; `skill_view` refused for that id.
5. **Prompt:** inject this agent's ticked skill names+blurbs. Keep `skill_view` for the body. Drop must-call-list-first for the menu. Files: `user_catalog.py` list already returns name+description without body; `skill_view` loads body; only Assistant / AutoReiv / Agent Builder have those tools (`profiles.py`).
6. **Split okta-admin conceptually:** Okta Admin is an agent; user-provisioning is a skill. No live Okta on this card. Skills Studio freeze is CARD-118. Python `*Skill` rename is CARD-120.
