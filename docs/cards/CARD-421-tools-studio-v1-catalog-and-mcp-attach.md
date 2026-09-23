---
id: CARD-421
title: "Tools Studio v1 (Catalog Browse + MCP Attach/Status)"
status: Ready
created: 2026-09-22
adr: docs/adr/0057-three-studios-and-developer-mediated-authoring.md
labels:
  - type:feat
  - area:ux
  - area:studios
  - area:tools
  - area:mcp
---

# [CARD-421] Tools Studio v1 (Catalog Browse + MCP Attach/Status)

> **Status**: Ready  
> **Created**: 2026-09-22  
> **ADR Reference**: [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md) (**Accepted**; packaging policy amended 2026-09-22 — dual native + MCP lanes, tighten later)  
> **Labels**: `type:feat`, `area:ux`, `area:studios`, `area:tools`, `area:mcp`  
> **Parent planning**: [CARD-417](./CARD-417-three-studios-agent-skill-tools-and-developer-mediated-authoring.md)  
> **Depends on**: [CARD-418](./CARD-418-skill-studio-extract-from-factory.md) Done; [CARD-419](./CARD-419-agent-studio-skill-toggle-pills.md) Done; [CARD-420](./CARD-420-developer-mediated-authoring-v1-visible-build-review.md) Done  
> **Successors (written in advance)**: [CARD-422](./CARD-422-tools-studio-form-and-developer-mediation.md) Ready; [CARD-423](./CARD-423-custom-tool-packaging-native-and-mcp.md) Ready; [CARD-424](./CARD-424-mcp-disable-must-unmount.md) Ready (disable must unmount)

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine AC / cutover - **no product code** |
| **`build`** | Implement on `feat/card-421-*` from `qa` |
| **`merge to qa`** | After In Review + live test |

---

## Slice map (so unfinished work is never only in chat)

| Card | Status | Ships |
|------|--------|-------|
| **CARD-421** (this card) | Ready | Tools Studio dock; catalog browse; tools grouped under MCP when that is the source; Routines-like search/filter; platform + agent-scoped **MCP attach/status/test**; Settings and Agent Studio become thin Open-in-Tools-Studio shells for attach. **No** form, **no** Talk/Submit to developer, **no** code editor, **no** MCP hosting move. |
| **CARD-422** | Ready (advance) | Form-driven create/modify/delete intent + Talk to developer / Submit to developer that actually opens or runs the developer with form context. Operator never types tool code in the studio. |
| **CARD-423** | Ready (advance) | Dual packaging lanes: native AutoReiv custom tools **and** MCP-backed custom tools; developer skills/runbooks for AutoReiv tool and MCP building; chat-path context to a folder of scripts is allowed as developer input, not a Tools Studio point-at-folder factory. |
| **CARD-424** | Ready (follow-up) | Disable must unmount; enable remounts; list status matches reality. Found in CARD-421 live test. |

When CARD-421 merges Done, CARD-422 is still Ready — that is the reminder that more Tools Studio work remains.

---

## 1. Why / Intent (Beat 1)

ADR-0057 locks **Tools Studio** as the third studio: the operator home for **tool catalog browse** and **MCP server attach / status / test**. Skill Studio already owns skill bodies and skill-to-tool binding. Agent Studio owns agent identity and skill on/off pills. Tools and MCP still live split across Settings, Agent Studio (Forge), and the Skill Studio catalog pane, so operators have no single place to answer "what tools exist, and which MCP servers are attached."

This card is ADR-0057 build-order step 4 (Tools Studio v1). Developer-mediated tool lifecycle and dual packaging (native vs MCP) are **CARD-422** and **CARD-423**, written in advance so the remaining slices stay visible.

---

## 2. What AutoReiv does now (Beat 2)

- **No Tools Studio dock.** Dock has Factory, Skill Studio, Agent Studio (Forge), Settings, and others. Nothing named Tools Studio.
- **Platform MCP attach** lives in **Settings** (`settings.js`): list / add / test / delete via `GET|POST|DELETE /api/settings/mcp` and `POST /api/settings/mcp/test` (aliases under `/api/mcp/servers`). Durable store key `mcp_servers`.
- **Agent-scoped MCP attach** lives in **Agent Studio / Forge** (`forgeMcpServersCard`): list / add / test / mount via `/api/agents/{agent_id}/mcp*`. Persisted on the agent profile as `mcp_servers`.
- **Skill Studio** still shows the **capability / MCP tool catalog checkboxes** used only to bind tools onto a skill (`skill_tool_bindings` / `requires_tools`). That is skill-to-tool scoping, not tool lifecycle.
- **Capability registry and scaffold APIs** exist under `/api/capabilities/*` (registry upsert, gap scaffold draft/sandbox/approve). Those are not a Tools Studio operator surface yet.
- **Hosted MCP server** (`src/web/routers/mcp_server.py`, `/api/mcp/sse`) exposes AutoReiv agents outward. **Locked forever in Settings** for operator UI — this card does not move hosting into Tools Studio.

---

## 3. What will change (Beat 3)

1. Add **Tools Studio** as an Agent Desktop dock window (label: **Tools Studio**). New module under `src/web/static/modules/studios/` (for example `tools_studio.js`) plus a `view-tools-studio` panel in `index.html`.
2. **Catalog pane (read-first):** browse the live tool / capability catalog (platform tools plus mounted MCP tool names). Prefer **grouping tools under the MCP server** that provides them when that is the source; platform tools in their own group. **Search and filtering** in the spirit of Routines Studio. Show mounted / available status when the existing MCP manager already exposes it. This pane does **not** write `skill_tool_bindings`.
3. **MCP attach pane:** attach / edit / test / enable-disable / delete MCP servers using the existing durable APIs.
   - **Platform MCP** moves its operator home from Settings into Tools Studio (same `/api/settings/mcp*` contracts).
   - **Agent-scoped MCP** is reachable from Tools Studio with an agent picker (same `/api/agents/{id}/mcp*` contracts).
4. **Settings cutover (attach only):** Settings MCP **attach** section becomes a thin shell or link (**Open in Tools Studio**). **MCP hosting** controls stay in Settings forever.
5. **Agent Studio cutover:** Forge remote-MCP card becomes thin (status + **Open in Tools Studio**). Prefer one full MCP attach form in Tools Studio.
6. Preserve Skill Studio tool checkboxes for skill-to-tool binding.
7. Proof: Vitest for dock open + catalog render + MCP list hydrate; existing MCP route tests stay green; no new dual durable store.

**Out of scope for CARD-421:** form + Talk/Submit to developer (CARD-422); native custom tool packaging and dual-lane policy UI (CARD-423); capability scaffold approve/sandbox UI; naked script / Ansible folder factory in the studio UI; code editor; moving MCP **hosting** out of Settings; changing hosted `/api/mcp` server behavior; tier removal; storage folder redesign.

---

## 4. What dies (Beat 4)

- Expectation that **Settings** is the long-term home for MCP **attach**.
- Expectation that **Agent Studio** is the long-term home for full MCP attach forms.
- Expectation that Skill Studio's tool checklist is where operators **manage** tools (it only **scopes** tools onto a skill).
- A second independent MCP **attach** writer UI after cutover (Settings full attach form + Tools Studio full form without a thin-shell decision).
- Expectation that MCP **hosting** belongs in Tools Studio (it stays in Settings forever).

---

## Cutover (locked 2026-09-22)

**Tools Studio is the full MCP attach + catalog surface.** Settings keeps MCP **hosting** forever, plus a one-line attach status and **Open in Tools Studio**. Agent Studio keeps mounted-count status and **Open in Tools Studio**; drops the full add/test attach form once Tools Studio covers agent-scoped attach. Skill Studio tool checkboxes stay.

---

## 5. Acceptance criteria (EARS)

- **[REQ-421-001]** WHEN the operator opens **Tools Studio** from the dock, THE SYSTEM SHALL present a tool / capability catalog browse surface and an MCP attach/status surface without requiring Skill Studio or Factory to manage MCP servers.
- **[REQ-421-002]** WHEN the operator adds, tests, enables, or deletes a **platform** MCP server from Tools Studio, THE SYSTEM SHALL use the existing Settings MCP durable path (`mcp_servers` / `/api/settings/mcp*`) and reflect mount status after success or failure.
- **[REQ-421-003]** WHEN the operator manages an **agent-scoped** MCP server from Tools Studio (with an agent selected), THE SYSTEM SHALL use `/api/agents/{agent_id}/mcp*` and persist on that agent profile only.
- **[REQ-421-004]** WHEN the operator views Skill Studio after this card, THE SYSTEM SHALL still bind tools onto skills via the existing catalog checkboxes and SHALL NOT require Tools Studio to write `skill_tool_bindings`.
- **[REQ-421-005]** AFTER cutover, THE SYSTEM SHALL NOT present two full competing MCP **attach** writer UIs (Settings full attach form and Tools Studio full form both active without a thin-shell link).
- **[REQ-421-006]** THE SYSTEM SHALL NOT ship a form + Talk/Submit to developer, a naked custom-tool scaffold factory, or MCP hosting controls as part of Tools Studio v1 (those are CARD-422 / CARD-423 / Settings forever).
- **[REQ-421-007]** WHEN MCP-provided tools are listed in the catalog, THE SYSTEM SHALL group them under the MCP server that provides them when grouping data is available, and SHALL offer search/filter comparable in spirit to Routines Studio.

---

## 6. Verification

Automated (during build):

- Vitest: dock opens Tools Studio; catalog rows render; MCP-provided tools group under server when data exists; search/filter narrows the list; MCP list hydrates; Skill Studio binding tests remain green.
- Existing MCP route tests for `/api/settings/mcp*` and `/api/agents/{id}/mcp*` stay green.

Manual live test (say **merge to qa** only after this):

1. Pull `feat/card-421-*`, reload serve, hard-refresh.
2. Open **Tools Studio** from the dock. You see catalog browse (with search/filter) and MCP attach/status. MCP tools appear under their server when attached.
3. Add or test a platform MCP server in Tools Studio. It appears in the list with status. Settings attach writer is thin/link only; hosting still in Settings.
4. Select an agent and attach or view an agent-scoped MCP server in Tools Studio. Saving updates that agent only.
5. Open Skill Studio. Tool checkboxes still bind tools onto a skill and save bindings as before.
6. Open Agent Studio. Status + open Tools Studio is enough for the happy path attach flow.
7. Confirm CARD-422 and CARD-423 still exist as Ready cards (remaining slices).

---

## 7. Honest scope note

CARD-420 left developer mediation APIs in tree without a Skill Studio Ask developer button that only queued theatre. This card ships a **real** catalog + MCP attach operator path. Form + Talk/Submit and dual packaging are **CARD-422** and **CARD-423**, not empty buttons on this screen.

---

## 8. Live discussion + locked forks (2026-09-22)

### Plain meanings

- **Tool**: one named thing an agent can call (inputs in, result out).
- **MCP server (attach)**: an external plug-in box AutoReiv connects to; the box can expose many tools. Not the same as SSH hosts or other machine endpoints saved in Settings.
- **MCP host**: AutoReiv acting as a plug-in box so other apps call into AutoReiv. Different from attach. **Operator UI stays in Settings forever.**
- **Settings SSH / host endpoints**: how to reach a computer. Not the Tools Studio catalog.

### Jacob answers (locked)

1. **Slice call**: Harness Engineer chooses multi-slice; **write successor Ready cards in advance** so unfinished work is never only chat memory.
2. **Folder path clarification**: Point at a folder means while talking to the developer agent, supply a path and ask for one tool per script/playbook — **not** a Tools Studio folder-picker factory. Objective ask: is forcing MCP for every custom tool worth it? Jacob **leans allow both** (native custom tools and MCP-backed) and can tighten later.
3. **MCP hosting**: **forever stay in Settings.**

### Locked forks

| # | Fork | Locked choice |
|---|------|---------------|
| T1 | First ship shape | **C** — CARD-421 thin UI (browse, group, search/filter, attach). CARD-422 form + Talk/Submit. CARD-423 dual packaging + developer skills. |
| T2 | MCP attach UI home | **A** — Tools Studio owns platform + agent-scoped attach; Settings and Agent Studio become thin status + Open in Tools Studio for attach. |
| T3 | MCP hosting UI | **Forever Settings** — never move hosting into Tools Studio. |
| T4 / T5 | Scripts vs MCP / required relationship | **Allow both** — platform tools need no MCP; custom tools may be native AutoReiv tools **or** MCP-backed; MCP is not required for every custom tool. Tighten later if abuse or complexity warrants. Chat-path to a script folder is developer conversation context, not a studio UI. Implementation of dual lanes is **CARD-423**, not this card. |

### Objective note (Harness Engineer, not security-only)

Forcing MCP for every custom tool buys one discovery/auth/transport story and process isolation, and matches industry plug-in boxes. It also adds ceremony (another process, attach config, lifecycle) that is **not always valuable** for a small local helper. Built-in platform tools already call without MCP. Allowing both is the honest product call: prefer MCP when the capability is shared, remote, multi-tool, or should outlive AutoReiv's process; allow native when the helper is local, simple, and owned by AutoReiv. Jacob can tighten to MCP-preferred or MCP-required later without rewriting Tools Studio v1.

---

## Follow-up from live test (2026-09-22)

Disable left servers mounted (`enabled: false` without unmount). Captured as [CARD-424](./CARD-424-mcp-disable-must-unmount.md) Ready — not deferred to chat only.
