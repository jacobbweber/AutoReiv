# [CARD-121] Align Tools to one atomic callable (ground-up like CARD-117)

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: CARD-117; CARD-114; CARD-067; CARD-115; D:\Projects\research\autoreiv-definitions.md
> **Labels**: `type:docs`, `type:refactor`

---

## 1. Why / Intent
Same pass as skills (CARD-117). Jacob now understands Agent / Skill / Tool conceptually. He cannot yet articulate the AutoReiv code/details to make tools "proper". This card is the **later pickup brief** so Coding and Jacob do not think they are aligned while speaking different things.

**Tool = one atomic callable action the runtime actually runs.** Name + description + parameters (schema) go to the model every turn **if** that agent is allowed to call it.

It is not a worker. Not a runbook. Not a "skill pack".

Example: **Okta Admin (AGENT)** uses **create-user (TOOL)**. **User provisioning (SKILL)** says order / pitfalls / done-when.

**Ground-up:** do not treat current AutoReiv tools UI/code as the definition. Map or replace after the primitive is locked.

This card is **alignment / docs**. It is not a coding card. Do not implement product Python/JS here.

See also CARD-117 (Skill primitive first), CARD-120 (Python `*Skill` rename after this primitive is locked), CARD-118 (studio freeze), CARD-119 (Agent Packs later). Memory is CARD-116, separate.

---

## 2. What to Build
Alignment only. Do not implement product Python/JS on this card.

- Record the primitive: Tool = one atomic callable (name + description + parameters schema to the model every turn if allowlisted).
- Record what AutoReiv does today as **likely off / mixed**, with real screens and files (section 5). Call out Forge pack-master grouping as the old skill-pack idea leaking onto TOOLS.
- Record open questions / later work (section 6). Do not invent answers.
- Record the working agreement (section 7): Jacob and Coding walk this with CARD-117 / CARD-120 methodically. No silent-big-bang refactor.
- CHANGELOG Unreleased note that this backlog card opened and that CARD-117 points at the shared working agreement.
- Local commit only. Do not push.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Written alignment: Tool = one atomic callable action the runtime actually runs; name + description + parameters go to the model every turn if that agent is allowed to call it.
- [ ] Explicit: not a worker, not a runbook, not a skill pack. Example recorded: Okta Admin = AGENT; create-user = TOOL; user provisioning = SKILL.
- [ ] Ground-up is recorded: current AutoReiv tools UI/code is not the definition; map or replace after the primitive is locked.
- [ ] Today's mixed surface is named (Forge / `forge.js` pack grouping, agents API, `tool_registry.py`, `profiles.py`, Python `*_skill.py` that register tools, SKILL.md JSON stubs, `list_user_skill_packs` / `skill_view` as tools, `manifest.py` clustering). CARD-115 warning stays gone. CARD-067 allowlist-full turns stay.
- [ ] Open questions listed, not answered: two per-agent lists; load path; where levers live; built-in vs added-later; Forge pack grouping drop/rename; no Okta / Agent Packs / Skills Studio on this card.
- [ ] Working agreement recorded (Jacob 2026-08-30 t131u): walk together; Skill then Tool then Python rename; three beats per slice; shared vocab at `D:\Projects\research\autoreiv-definitions.md`.
- [ ] CARD-117 has a short "When we pick this up" pointer to this agreement and CARD-121 (tools pass is the sibling, not a second definition of skill).
- [ ] No product Python/JS. Status stays **Ready** (backlog). Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Status: **Ready** (backlog). Do not set In Progress.
- Work on `qa`. Do not push. Do not clone.
- Do not implement product code. Do not write Python/JS for the product. Do not rename `*_skill.py` on this card (that is CARD-120, after this primitive is locked).
- Foundations order: Skill primitive (CARD-117) then Tool primitive (this card) then Python `*Skill` rename (CARD-120). Studio freeze (CARD-118) and Agent Packs (CARD-119) wait. Memory is CARD-116, separate.
- Do not treat Forge pack checkboxes, `manifest.py` skill packs, or Python `*Skill` classes as the definition of this primitive.
- Do not invent answers to section 6 open questions. Record them so later work can pick them up.
- CARD-115 already removed the Forge 12-tool warning. Do not bring it back. Jacob's rule: if the list is large, split the agent, don't warn in Forge.
- CARD-067: turns get the full Forge allowlist (no BM25 shrink). Keep that.
- User SKILL.md JSON `tools` (okta-admin seed) are labels/stubs; they do not call Okta (CARD-114). Do not confuse them with Forge Python tools.
- When later executed: Jacob and Coding walk it together. Do not silent-big-bang the refactor.

---

## 5. What AutoReiv does today (likely off / mixed)

Record, do not "fix" on this card. Current pieces are mixed. Rebuild the primitive first, then map or replace.

### 5.1 Lever: Forge in Agent Studio

- Screen: Agent Studio / Forge.
- File: `src/web/static/modules/studios/forge.js`.
- Checkboxes = `agent.allowed_tool_names`. Saved via agents API (`src/web/routers/agents.py`) onto the agent profile.
- Forge UI groups tools into "packs" with a **pack-master-checkbox** (`data-pack`, class `pack-master-checkbox`; catalog from `skill_packs` / `get_hierarchical_skills_catalog`). That grouping is the **old skill-pack idea leaking onto TOOLS**. Call this out.
- The on/off lever should be **per tool on the agent**. Grouping is optional later, not the primitive.

### 5.2 Runtime registry

- `src/application/kernel/tool_registry.py` — `ScopedToolRegistry`, `get_tools_for_agent`.
- `ToolDefinition` in `src/domain/gateway/models.py`.

### 5.3 Builtin agent default lists

- `src/domain/agents/profiles.py`: Assistant, AutoReiv, Coding, Conductor, Review, Agent Builder.

### 5.4 Real Python callables live under `src/application/skills/*_skill.py`

- Examples: WikiSkill, GitSkill, CardSkill, sandbox / execute_code (`sandbox_skill.py`), etc.
- Those **filenames say skill but they REGISTER TOOLS**. CARD-120 renames them after this primitive is locked. **Do not rename on this card.**

### 5.5 User SKILL.md JSON `tools` are not callables

- okta-admin seed tools are labels/stubs; they do not call Okta (CARD-114).
- They must not be confused with Forge Python tools. Do not dump stub JSON tools from SKILL.md into the model as if they were callable.

### 5.6 Catalog openers are TOOLS, not skills

- `list_user_skill_packs` and `skill_view` (see `src/application/skills/user_catalog.py`) are **TOOLS**, not skills.
- Only on Assistant, AutoReiv, Agent Builder (`profiles.py`).

### 5.7 Already-decided, do not regress

- CARD-115 already removed the Forge 12-tool warning. Do not bring it back. If the list is large, split the agent, don't warn in Forge.
- CARD-067: turns get the full Forge allowlist (no BM25 shrink).

### 5.8 Wrong mix still in code

- `src/application/skills/manifest.py` still talks about clustering tools into hierarchical skill packs (`SkillPackManifest`, `get_hierarchical_skills_catalog`, docstring "Hierarchical Skill Pack Manifests & Catalog Clustering"). That is the wrong mix.

---

## 6. Open questions / later work (do not invent answers)

These are **open questions / later work items**, not answers.

1. **Two explicit per-agent lists:** tools (Forge, exists) and skills (missing, CARD-117). Keep them separate in UI and code.
2. **Load path:** tool schemas (name + desc + params) every turn for allowlisted tools. Do not hide tools inside a skill. Do not dump stub JSON tools from SKILL.md into the model as if they were callable.
3. **Where levers live:** Agent Studio / Forge for tools. Not Skills Studio.
4. **Where code lives:** built-in Python tool modules (product) vs later user/pack-provided tools (data dir or Agent Packs CARD-119). Separate concepts. Built-in vs added-later, same as skills CARD-117 item 5.5.
5. **Forge "pack" grouping in the UI:** likely drop or rename so it does not say skill pack. Record, don't redesign on this card.
6. **No live Okta, no Agent Packs, no Skills Studio features on this card.**

---

## 7. Working agreement (critical, Jacob 2026-08-30 t131u)

When this card (and CARD-117 / CARD-120) is later executed, Jacob and Coding walk it together methodically. **Do not silent-big-bang the refactor.**

- **Order of foundations:** Skill primitive (CARD-117) then Tool primitive (this card) then Python `*Skill` rename (CARD-120). Studio freeze (CARD-118) and Agent Packs (CARD-119) wait. Memory is CARD-116, separate.
- **Each slice:** say the real word, then the screen/file/click (Forge checkbox, `profiles.py`, `tool_registry.py`, a `*_skill.py` module). Three beats: what Jacob means, what AutoReiv does now, what we will change.
- Do not assume alignment from a nod. Confirm the next file/area before editing it.
- **Shared vocab:** `D:\Projects\research\autoreiv-definitions.md` and these cards. If a term conflicts, stop and fix the card before coding.
- Related cards will likely ship as one refactor wave, but pickup is still **one primitive at a time** so we don't mix skill and tool in the same edit.
