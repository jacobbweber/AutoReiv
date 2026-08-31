# [CARD-119] Agent Packs (import / export / build)

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: CARD-117; CARD-118; CARD-120; CARD-121; CARD-123; CARD-103
> **Labels**: `type:feat`, `type:docs`

---

## 1. Why / Intent
**Agent Pack is packaging, not a fourth primitive.** The primitives stay **agent**, **skill** (one `SKILL.md` runbook), and **tool** (one atomic callable). An Agent Pack is one specialist in a folder you can import, export, or back up: who they are, their skills, which tools came with them, their workflows, and whether a person should pick them in Chat.

It is not a Skill Pack. It is not a Pack Studio tab. It is not new Python tool code inside the zip (later builder owns wiring new callables).

**Walked (2026-08-30 Jacob t173u-t175u):** Import / Export lives on **Agent Studio** (the selected agent). The **SDK** is the how-to: pack schema (folder + JSON fields) plus a short guide for doing it by hand. **AutoReiv** (the platform agent in Chat) also gets skills and tools to write that same pack. Hand path and talk-to-AutoReiv path both write the same schema. **Show in Chat** is one checkbox in Agent Studio. On = that agent appears in Chat's agent dropdown (`#agentSelect`). Off = a behind-the-scenes specialist; handoff can still use them. Building a pack does not restripe Chat's picker. Assistant, AutoReiv, and whoever is already in that dropdown stay pickable until you untick them.

**Earlier lock (t153u):** when packs exist, the shipped core roster is two agents: **Assistant** (talk-to-the-human) and **AutoReiv** (platform). Specialists (Coding, Conductor, Review, Agent Builder, Okta Admin, EUC, etc.) should arrive as packs, not more forever-builtins. **Do not rip existing builtins on this card.** Capture that roster intent only.

---

## 2. What to Build
Product implementation (this pickup). Alignment lock in section 8 still stands.

- Pack schema (folder + JSON) for one specialist. Fields: identity (id, name, description, instructions / `system_prompt`, tone, purpose, avatar, model), `allowed_skill` + the `SKILL.md` files, pack-owned tool ids (`allowed_tool_names` that belong to the pack), `show_in_chat`, and this agent's workflows (CARD-123 JSON). Do not copy transcripts, instance facts, or secrets.
- How-to doc (the SDK): schema, folder layout, import by hand, export by hand. Not a separate installer. Not a Pack Studio.
- Agent Studio on the selected agent: **Import** and **Export**. Import lands in the user data dir and creates/updates that agent. Export writes a pack folder/zip from the selected agent. Same screen as instructions, tone, Tools, Skills, Workflows (CARD-118). No third tab.
- `show_in_chat` on the agent (default **on**). Agent Studio checkbox **Show in Chat**. Chat `#agentSelect` and the chat top-bar picker only list agents with it on. Do not filter handoff's agent name+blurb directory. Do not hide current talk-to agents as a side effect of shipping this card.
- Pack-owned Tools group in Agent Studio fills from the pack's tool ids and those ticks come **on** with the pack. Platform group stays the extra platform callables (off for a specialist). Do not ship new Python tool modules in the zip.
- **AutoReiv** agent: one SKILL.md runbook plus atomic tools that import, export, and write a pack matching the schema. Jacob can talk to AutoReiv to build a pack. Users still do not hand-edit Python tool implementations.
- Workflows ride along (already `$DATA_DIR/agents/<id>/workflows/`).
- Do not delete Coding, Conductor, Review, Agent Builder, or other builtins. Do not reship the `okta-admin` seed (CARD-118). Okta Admin is an example of a specialist bundle, not a product pack on this card.
- No Agent Packs as a kernel object. No memory (CARD-116). No Pack Studio.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Agent Pack is packaging (import / export / build), not a fourth primitive. Not a Skill Pack renamed.
- [ ] Schema + how-to (the SDK) exist: folder layout and JSON fields, including `show_in_chat`. Hand import/export is documented.
- [ ] Agent Studio has Import / Export on the selected agent. No Pack Studio. Import appears in Chat only if Show in Chat is on.
- [ ] Show in Chat checkbox in Agent Studio. Default on for existing agents so Chat's picker does not restripe. Off hides from Chat dropdowns only. Handoff can still target them.
- [ ] Pack-owned tools group fills from the pack; those ticks come on with the pack. Platform stays the extra list. No new Python callables in the zip.
- [ ] AutoReiv has a runbook + tools to write/import/export the same schema. Hand path and AutoReiv path are two authors, one format.
- [ ] Workflows on that agent are included in the pack. Transcripts / person facts / secrets are not.
- [ ] Core roster intent is recorded: shipped core is Assistant + AutoReiv; specialists arrive as packs later. Builtins are **not** ripped on this card.
- [ ] Product Python/JS + tests. Status **In Review** after code. Not Done until live test. Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Work on `qa`. Do not push. Do not clone.
- Product code is in scope. Fix the card if a word disagrees before expanding scope.
- Do not add a Pack Studio tab. Do not add a fourth primitive. Do not treat this as a Skill Pack (CARD-117).
- Do not rip existing builtins. Do not reship `okta-admin`. Do not put new Python tool implementations in the pack zip (later pack-builder).
- Do not restripe Chat's picker: default `show_in_chat=true`. Building a pack does not hide anyone.
- Do not filter handoff targets by Show in Chat.
- Users do not hand-edit tool implementations in Agent Studio.
- Do not name inspiration products in cards, specs, CHANGELOG, UI, or notes.
- Do not build CARD-116 memory. Do not build CARD-122.
- Controls already shipped (CARD-121): two Studio tool groups; untick omits schema; no RBAC; no in-flight mapper.

---

## 5. Cheat-sheet lock

Do not mix these words.

- **agent** = named specialist (Chat dropdown / Agent Studio).
- **skill** = one `SKILL.md` runbook (name + blurb in prompt; body on open).
- **tool** = one atomic callable (Agent Studio ticks; schema every turn if ticked).
- **agent pack** = packaging of one agent + its skills + its pack-owned tools + its workflows + Show in Chat. Not a primitive. Not a Skill Pack.
- **Show in Chat** = Agent Studio checkbox. Controls Chat's agent dropdown only.
- **SDK** = the how-to (schema + hand import/export guide). Not a separate product.

---

## 6. Example

Okta Admin as a **thought example** only (do not ship the seed). Pack contains: the Okta Admin agent (name, instructions, tone), a user-provisioning runbook (`SKILL.md`), pack-owned tool **ids** that already exist on the platform (or empty until later builder), `show_in_chat` on or off, optional workflows. Jane vs Bob is instance data and does **not** go in the pack.

A behind-the-scenes specialist (Show in Chat off) can still be a handoff target. A talk-to specialist (on) appears in Chat's dropdown.

---

## 7. Change list (today vs this card)

**Today**
- Agent Studio (`src/web/static/modules/studios/forge.js`, sidebar Agent Studio) already has identity, instructions, tone, Tools (Pack-owned empty + Platform), Skills, Workflows.
- Chat `loadAgents()` in `src/web/static/modules/studios/chat.js` fills `#agentSelect` and the top-bar picker from **all** `/api/agents` rows. No `show_in_chat`.
- `AgentProfile` (`src/domain/kernel/models.py`) has no `show_in_chat`. SQLite `custom_agents` / `agent_overrides` (`src/infrastructure/memory/schema.py`) have no such column.
- Builtins in `src/domain/agents/profiles.py`: `assistant`, `autoreiv`, `coding`, `conductor`, `review`, `agent-builder`. All `is_builtin=True`.
- Backup (CARD-103) is the whole data dir, not one agent.
- No import/export of one specialist. No pack schema. AutoReiv has no pack-build runbook/tools.
- Pack-owned UI copy: "No pack-owned tools yet."

**This card adds**
- Pack schema + how-to doc.
- Import / Export on Agent Studio.
- `show_in_chat` (model, persist, API, Agent Studio checkbox, Chat filter).
- Pack-owned list filled from imported/built packs.
- AutoReiv runbook + tools for the same schema.
- Workflows included in the pack.

---

## 8. Walked lock (2026-08-30)

### 8.1 t153u core roster (intent only)
Shipped core roster is Assistant + AutoReiv. Specialists arrive as Agent Packs. Do not rip builtins on this card.

### 8.2 t173u packaging
Agent Pack = folder you import: name, instructions, tone, SKILL.md runbooks, pack-owned ticks. Shows up in Chat's agent dropdown and Agent Studio. Export/backup is the reverse on that screen. Not a fourth primitive. Not a Skill Pack. No Pack Studio. New Python tools in the zip is later builder.

### 8.3 t174u-t175u SDK, AutoReiv builds, Show in Chat
SDK = schema + how-to, not a separate product. AutoReiv (platform agent) gets skills + tools to build the same pack. Hand import/export is the manual path. Show in Chat is one Agent Studio checkbox; pack schema has the same field; import/AutoReiv-build copies it onto that checkbox. Does not restripe Chat's current picker. Handoff can still use an agent that is off in Chat. Jacob: "perfect continue."

---

## 9. Code map (Grok)

- Profile: `src/domain/kernel/models.py` `AgentProfile`
- Persist: `src/infrastructure/memory/schema.py` `custom_agents`, `agent_overrides`; `src/infrastructure/memory/repositories/settings.py`
- API: `src/web/routers/agents.py` (`/api/agents`, create/update)
- Agent Studio: `src/web/static/modules/studios/forge.js`, `src/web/templates/index.html`
- Chat pickers: `src/web/static/modules/studios/chat.js` `loadAgents()` (`#agentSelect`, top-bar select)
- Builtins: `src/domain/agents/profiles.py`
- AutoReiv allowlist: same file, `id="autoreiv"`
- Skills files: `$DATA_DIR/skills/`
- Workflows: `$DATA_DIR/agents/<owner_agent_id>/workflows/`
- Tools UI groups: already Pack-owned vs Platform in `forge.js` (CARD-121)
