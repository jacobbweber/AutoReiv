# [CARD-119] Agent Packs (import / export / build)

> **Status**: In Review
> **Created**: 2026-08-30
> **Spec Reference**: CARD-117; CARD-118; CARD-120; CARD-121; CARD-123; CARD-103
> **Labels**: `type:feat`, `type:docs`

---

## 1. Why / Intent
**Agent Pack is packaging, not a fourth primitive.** The primitives stay **agent**, **skill** (one `SKILL.md` runbook), and **tool** (one atomic callable). An Agent Pack is one specialist in a folder you can import, export, or back up: who they are, their skills, which tools came with them, their workflows, and whether a person should pick them in Chat.

It is not a Skill Pack. It is not a Pack Studio tab. It is not new Python tool code inside the zip (later builder owns wiring new callables).

**Walked (2026-08-30 Jacob t173u-t175u):** Import / Export lives on **Agent Studio** (the selected agent). The **SDK** is the how-to: pack schema (folder + JSON fields) plus a short guide for doing it by hand. **AutoReiv** (the platform agent in Chat) also gets skills and tools to write that same pack. Hand path and talk-to-AutoReiv path both write the same schema. **Show in Chat** is one checkbox in Agent Studio. On = that agent appears in Chat's agent dropdown (`#agentSelect`). Off = a behind-the-scenes specialist; handoff can still use them. Building a pack does not restripe Chat's picker. Assistant, AutoReiv, and whoever is already in that dropdown stay pickable until you untick them.

**Follow-up lock (2026-08-30 Jacob):** Two complete authors, one landing place. (1) Talk to AutoReiv in Chat: runbook + tools to build a pack. AutoReiv asks for agent details, each skill, and which tools belong to that skill. An agent has many skills; each skill has tools; skills belong to one agent. (2) Hand SDK + Import/Export: same schema, by-hand folder/zip. How-to is the SDK (`docs/agent-packs.md` + schema), not a separate product. Both land in the same data-dir location so the platform loads them the same way.

Agent Studio is where a pack **already here** is edited (name, instructions, tone, Show in Chat, ticks, Import/Export). It is **not** where you invent new skills or new tools. Do not add New skill / New tool buttons. CARD-118 existing New on the skills list stays (out of scope).

**New Agent** (next to Import/Export in Agent Studio) must **not** save a blank custom agent or empty pack. That path cannot finish the pack on that screen. It must switch to Chat, select AutoReiv (`id="autoreiv"`), start a fresh session, and fill a starter prompt like `I am ready to create a new agent.` so AutoReiv walks the schema.

Authoring schema nests tools under skills, skills under the agent, plus agent details / workflows / `show_in_chat`. Runtime after import: union those mapped tools onto the agent's Pack-owned ticks (`pack_tool_names` / allowed tools). Skills become `allowed_skill` + files under `$DATA_DIR/skills/`. Workflows ride along. Do not copy transcripts/secrets/Python tool source.

Show in Chat stays as already shipped: default on; off hides from Chat dropdowns; handoff can still target them.

**Earlier lock (t153u):** when packs exist, the shipped core roster is two agents: **Assistant** (talk-to-the-human) and **AutoReiv** (platform). Specialists (Coding, Conductor, Review, Agent Builder, and other specialists) should arrive as packs, not more forever-builtins. **Do not rip existing builtins on this card.** Capture that roster intent only.

---

## 2. What to Build
Product implementation. Alignment lock in section 8 still stands. Follow-up lock in section 9 is this pickup.

- Pack schema (folder + JSON) for one specialist. Authoring: nested `skills: [{ id, tools, name?, description? }]`. Derived compat: `allowed_skill` = skill ids; `pack_tool_names` = union of skill tools plus leftover top-level list. Also identity (id, name, description, instructions / `system_prompt`, tone, purpose, avatar, model), `show_in_chat`, and this agent's workflows (CARD-123 JSON). Do not copy transcripts, instance facts, or secrets.
- Schema version `1.1`. A `1.0` pack with sibling `allowed_skill` + `pack_tool_names` still imports.
- How-to doc (the SDK): schema, folder layout, import by hand, export by hand. Not a separate installer. Not a Pack Studio.
- Agent Studio on the selected agent: **Import** and **Export**. Import lands in the user data dir and creates/updates that agent. Export writes a pack folder/zip from the selected agent. Same screen as instructions, tone, Tools, Skills, Workflows (CARD-118). No third tab.
- **New Agent** hands off to Chat → AutoReiv with the starter prompt. Does not POST a blank agent. Does not blank the Studio form into a new-custom in-memory agent.
- `show_in_chat` on the agent (default **on**). Agent Studio checkbox **Show in Chat**. Chat `#agentSelect` and the chat top-bar picker only list agents with it on. Do not filter handoff's agent name+blurb directory. Do not hide current talk-to agents as a side effect of shipping this card.
- Pack-owned Tools group in Agent Studio fills from the pack's tool ids and those ticks come **on** with the pack. Platform group stays the extra platform callables (off for a specialist). Do not ship new Python tool modules in the zip.
- **AutoReiv** agent: one SKILL.md runbook plus atomic tools that import, export, and write a pack matching the nested schema. Jacob can talk to AutoReiv to build a pack. Users still do not hand-edit Python tool implementations.
- Workflows ride along (already `$DATA_DIR/agents/<id>/workflows/`).
- Do not delete Coding, Conductor, Review, Agent Builder, or other builtins. Do not reship retired brochure seeds (CARD-118). A specialist bundle is an example, not a product pack on this card.
- No Agent Packs as a kernel object. No memory (CARD-116). No Pack Studio. No CARD-122.
- Do not reverse CARD-117/121 runtime: Chat still lists this agent's ticked tools every turn. Do not hide tool schemas behind skills at turn time.

---

## 3. Acceptance Criteria (Definition of Done)

Shipped (first landing, still true):
- [x] Agent Pack is packaging (import / export / build), not a fourth primitive. Not a Skill Pack renamed.
- [x] Schema + how-to (the SDK) exist: folder layout and JSON fields, including `show_in_chat`. Hand import/export is documented.
- [x] Agent Studio has Import / Export on the selected agent. No Pack Studio. Import appears in Chat only if Show in Chat is on.
- [x] Show in Chat checkbox in Agent Studio. Default on for existing agents so Chat's picker does not restripe. Off hides from Chat dropdowns only. Handoff can still target them.
- [x] Pack-owned tools group fills from the pack; those ticks come on with the pack. Platform stays the extra list. No new Python callables in the zip.
- [x] AutoReiv has a runbook + tools to write/import/export the same schema. Hand path and AutoReiv path are two authors, one format.
- [x] Workflows on that agent are included in the pack. Transcripts / person facts / secrets are not.
- [x] Core roster intent is recorded: shipped core is Assistant + AutoReiv; specialists arrive as packs later. Builtins are **not** ripped on this card.

Follow-up (this pickup):
- [x] Nested pack schema `1.1`: tools sit under skills; `allowed_skill` and `pack_tool_names` are derived/compat. `1.0` sibling lists still import.
- [x] `scaffold_agent_pack`, export, and `docs/agent-packs.md` write/describe the nested shape. AutoReiv `build-agent-pack` asks for agent details, each skill, and which tools belong to that skill.
- [x] New Agent switches to Chat, selects AutoReiv, starts a fresh session, fills `I am ready to create a new agent.`, focuses the prompt. Does not auto-submit. Does not POST `/api/agents`. Does not invent an empty custom agent in Agent Studio.
- [x] Agent Studio is not New skill / New tool. CARD-118 New on the skills list is left alone.
- [x] Product Python/JS + tests (634 unit pytest, 92 vitest). Status **In Review** after code. Not Done until live test. Local commit only. No push.

---

## 4. Constraints & Honor Flags
- Work on `qa`. Do not push. Do not clone.
- Product code is in scope. Fix the card if a word disagrees before expanding scope.
- Do not add a Pack Studio tab. Do not add a fourth primitive. Do not treat this as a Skill Pack (CARD-117).
- Do not rip existing builtins. Do not reship retired brochure seeds. Do not put new Python tool implementations in the pack zip (later pack-builder).
- Do not restripe Chat's picker: default `show_in_chat=true`. Building a pack does not hide anyone.
- Do not filter handoff targets by Show in Chat.
- Users do not hand-edit tool implementations in Agent Studio.
- Do not name inspiration products in cards, specs, CHANGELOG, UI, or notes.
- Do not build CARD-116 memory. Do not build CARD-122.
- Do not reverse CARD-117/121: ticked tools still go to the model every turn.
- Do not add New skill / New tool buttons to Agent Studio.
- Controls already shipped (CARD-121): two Studio tool groups; untick omits schema; no RBAC; no in-flight mapper.

---

## 5. Cheat-sheet lock

Do not mix these words.

- **agent** = named specialist (Chat dropdown / Agent Studio).
- **skill** = one `SKILL.md` runbook (name + blurb in prompt; body on open).
- **tool** = one atomic callable (Agent Studio ticks; schema every turn if ticked).
- **agent pack** = packaging of one agent + its skills (each with tools) + its workflows + Show in Chat. Not a primitive. Not a Skill Pack.
- **Show in Chat** = Agent Studio checkbox. Controls Chat's agent dropdown only.
- **SDK** = the how-to (schema + hand import/export guide). Not a separate product.
- **Agent Studio** = edit a pack already here. Not New skill / New tool. New Agent hands off to AutoReiv in Chat.

---

## 6. Example

A specialist pack as a **thought example** only (do not ship the seed). Pack contains: the agent (name, instructions, tone), one or more runbooks (`SKILL.md`) each listing which existing platform tool ids belong to that skill, `show_in_chat` on or off, optional workflows. Jane vs Bob is instance data and does **not** go in the pack.

A behind-the-scenes specialist (Show in Chat off) can still be a handoff target. A talk-to specialist (on) appears in Chat's dropdown.

---

## 7. Change list (today vs this card)

**Already shipped (first landing)**
- Pack schema + how-to doc, Import / Export on Agent Studio, `show_in_chat`, pack-owned ticks from import, AutoReiv runbook + pack tools, workflows included, builtins not ripped.

**This follow-up adds**
- Nested `skills: [{ id, tools }]` authoring shape (`schema_version` 1.1) with derived `allowed_skill` / `pack_tool_names`. 1.0 packs still import.
- New Agent → Chat, select AutoReiv, fresh session, filled starter prompt (not sent, not a blank Studio agent).
- AutoReiv runbook asks for agent details, each skill, and tools per skill, then writes the nested pack.
- Agent Studio stays the editor for a pack already here. No New skill / New tool buttons.

---

## 8. Walked lock (2026-08-30)

### 8.1 t153u core roster (intent only)
Shipped core roster is Assistant + AutoReiv. Specialists arrive as Agent Packs. Do not rip builtins on this card.

### 8.2 t173u packaging
Agent Pack = folder you import: name, instructions, tone, SKILL.md runbooks, pack-owned ticks. Shows up in Chat's agent dropdown and Agent Studio. Export/backup is the reverse on that screen. Not a fourth primitive. Not a Skill Pack. No Pack Studio. New Python tools in the zip is later builder.

### 8.3 t174u-t175u SDK, AutoReiv builds, Show in Chat
SDK = schema + how-to, not a separate product. AutoReiv (platform agent) gets skills + tools to build the same pack. Hand import/export is the manual path. Show in Chat is one Agent Studio checkbox; pack schema has the same field; import/AutoReiv-build copies it onto that checkbox. Does not restripe Chat's current picker. Handoff can still use an agent that is off in Chat. Jacob: "perfect continue."

---

## 9. Follow-up lock (2026-08-30, confirmed)

Two complete authors, one landing place:

1. Talk to AutoReiv (platform agent in Chat): runbook + tools to build a pack. AutoReiv asks for agent details, each skill, and which tools belong to that skill.
2. Hand SDK + Import/Export: same schema, by-hand folder/zip. How-to is the SDK, not a separate product.

Both land in `$DATA_DIR` so the platform loads them the same way.

New Agent button: must not save a blank custom agent. Switch to Chat, select AutoReiv, starter prompt filled and focused. Do not auto-submit unless sending is trivial; filled+focused is enough so the human hits Send. Do not `POST /api/agents`.

Nested pack schema: tools under skills, skills under the agent. Runtime unions mapped tools onto Pack-owned ticks. Skills become `allowed_skill` + `$DATA_DIR/skills/`. Export without a stored per-skill map emits `skills` with empty `tools` plus top-level `pack_tool_names`. Do not duplicate the union onto every skill.

Do not add New skill / New tool to Agent Studio. Do not reverse CARD-117/121. Do not rip builtins. Do not start CARD-116 or CARD-122.

---

## 10. Code map

- Schema: `src/application/agent_packs/schema.py` (`PACK_SCHEMA_VERSION`, `PackSkill`, `AgentPackManifest`)
- Service: `src/application/agent_packs/service.py`
- AutoReiv tools: `src/application/skills/agent_pack_tools.py`
- Runbook: `src/infrastructure/skills/seeds/build-agent-pack/SKILL.md`
- How-to: `docs/agent-packs.md`
- Agent Studio: `src/web/static/modules/studios/forge.js` (`newAgentBtn`, Import/Export)
- Chat handoff: `src/web/static/modules/studios/chat.js` (`startNewAgentAuthoring`), `src/web/static/app.js` (`onStartNewAgentPack` / `switchTab`)
- Profile: `src/domain/kernel/models.py` `AgentProfile`
- Persist: `src/infrastructure/memory/schema.py` `custom_agents`, `agent_overrides`
- API: `src/web/routers/agents.py`
- Chat pickers: `src/web/static/modules/studios/chat.js` `loadAgents()`
- Builtins: `src/domain/agents/profiles.py` (`id="autoreiv"`)
- Skills files: `$DATA_DIR/skills/`
- Workflows: `$DATA_DIR/agents/<owner_agent_id>/workflows/`


