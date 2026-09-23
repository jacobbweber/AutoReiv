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
> **ADR Reference**: [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md) (**Accepted**)  
> **Labels**: `type:feat`, `area:ux`, `area:studios`, `area:tools`, `area:mcp`  
> **Parent planning**: [CARD-417](./CARD-417-three-studios-agent-skill-tools-and-developer-mediated-authoring.md)  
> **Depends on**: [CARD-418](./CARD-418-skill-studio-extract-from-factory.md) Done; [CARD-419](./CARD-419-agent-studio-skill-toggle-pills.md) Done; [CARD-420](./CARD-420-developer-mediated-authoring-v1-visible-build-review.md) Done

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine AC / cutover - **no product code** |
| **`build`** | Implement on `feat/card-421-*` from `qa` |
| **`merge to qa`** | After In Review + live test |

---

## 1. Why / Intent (Beat 1)

ADR-0057 locks **Tools Studio** as the third studio: the operator home for **tool catalog browse** and **MCP server attach / status / test**. Skill Studio already owns skill bodies and skill-to-tool binding. Agent Studio owns agent identity and skill on/off pills. Tools and MCP still live split across Settings, Agent Studio (Forge), and the Skill Studio catalog pane, so operators have no single place to answer "what tools exist, and which MCP servers are attached."

This card is ADR-0057 build-order step 4 (Tools Studio v1). It does **not** build custom MCP-only capability authoring, naked script factories, or developer mediation for tools.

---

## 2. What AutoReiv does now (Beat 2)

- **No Tools Studio dock.** Dock has Factory, Skill Studio, Agent Studio (Forge), Settings, and others. Nothing named Tools Studio.
- **Platform MCP attach** lives in **Settings** (`settings.js`): list / add / test / delete via `GET|POST|DELETE /api/settings/mcp` and `POST /api/settings/mcp/test` (aliases under `/api/mcp/servers`). Durable store key `mcp_servers`.
- **Agent-scoped MCP attach** lives in **Agent Studio / Forge** (`forgeMcpServersCard`): list / add / test / mount via `/api/agents/{agent_id}/mcp*`. Persisted on the agent profile as `mcp_servers`.
- **Skill Studio** still shows the **capability / MCP tool catalog checkboxes** used only to bind tools onto a skill (`skill_tool_bindings` / `requires_tools`). That is skill-to-tool scoping, not tool lifecycle.
- **Capability registry and scaffold APIs** exist under `/api/capabilities/*` (registry upsert, gap scaffold draft/sandbox/approve). Those are not a Tools Studio operator surface yet, and naked custom-tool scaffolding is **out of policy for v1**.
- **Hosted MCP server** (`src/web/routers/mcp_server.py`, `/api/mcp/sse`) exposes AutoReiv agents outward. That is not the attach UI this card owns.

---

## 3. What will change (Beat 3)

1. Add **Tools Studio** as an Agent Desktop dock window (label: **Tools Studio**). New module under `src/web/static/modules/studios/` (for example `tools_studio.js`) plus a `view-tools-studio` panel in `index.html`.
2. **Catalog pane (read-first):** browse the live tool / capability catalog (platform tools plus mounted MCP tool names), with search and a clear source label (platform vs MCP server). Show mounted / available status when the existing MCP manager already exposes it. This pane does **not** write `skill_tool_bindings`.
3. **MCP pane:** attach / edit / test / enable-disable / delete MCP servers using the existing durable APIs. Default cutover (confirm or change on **continue** before **build**):
   - **Platform MCP** moves its operator home from Settings into Tools Studio (same `/api/settings/mcp*` contracts).
   - **Agent-scoped MCP** is reachable from Tools Studio with an agent picker (same `/api/agents/{id}/mcp*` contracts), so Tools Studio owns MCP attach/status while Agent Studio can keep a short status strip plus **Open in Tools Studio**.
4. **Settings cutover:** Settings MCP section becomes a thin shell or link (**Open in Tools Studio**), not a second full writer UI.
5. **Agent Studio cutover:** Forge remote-MCP card becomes thin (status + open Tools Studio) or stays as a scoped editor only if live test proves agent-context attach must stay inline. Prefer one full MCP form in Tools Studio.
6. Preserve Skill Studio tool checkboxes for skill-to-tool binding. Deep-link optional: from a catalog row, **Open in Skill Studio** is allowed later; not required for v1.
7. Proof: Vitest for dock open + catalog render + MCP list hydrate; pytest or existing MCP route tests stay green; no new dual durable store.

**Out of scope:** custom capability authoring via MCP-only servers beyond attach; capability scaffold approve/sandbox UI; naked script / Ansible / Terraform tool factories; developer Build/Review for tools; tier removal; storage folder redesign; moving skill-to-tool binding out of Skill Studio; changing hosted `/api/mcp` server behavior.

---

## 4. What dies (Beat 4)

- Expectation that **Settings** is the long-term home for MCP attach.
- Expectation that **Agent Studio** is the long-term home for full MCP lifecycle forms.
- Expectation that Skill Studio's tool checklist is where operators **manage** tools (it only **scopes** tools onto a skill).
- A second independent MCP writer UI after cutover (Settings full form + Tools Studio full form without a thin-shell decision).

---

## Cutover (proposed; lock on continue or at build start)

**Tools Studio is the full MCP + catalog surface.** Settings keeps a one-line MCP status and **Open in Tools Studio**. Agent Studio keeps mounted-count status (and optional deep-link) but drops the full add/test form once Tools Studio covers agent-scoped attach. Skill Studio tool checkboxes stay.

If live test shows agent-scoped attach is too awkward without agent context, keep a **minimal** Forge attach form that still writes only `/api/agents/{id}/mcp*` and link the catalog to Tools Studio. Document the chosen cutover in this card during build.

---

## 5. Acceptance criteria (EARS)

- **[REQ-421-001]** WHEN the operator opens **Tools Studio** from the dock, THE SYSTEM SHALL present a tool / capability catalog browse surface and an MCP attach/status surface without requiring Skill Studio or Factory to manage MCP servers.
- **[REQ-421-002]** WHEN the operator adds, tests, enables, or deletes a **platform** MCP server from Tools Studio, THE SYSTEM SHALL use the existing Settings MCP durable path (`mcp_servers` / `/api/settings/mcp*`) and reflect mount status after success or failure.
- **[REQ-421-003]** WHEN the operator manages an **agent-scoped** MCP server from Tools Studio (with an agent selected), THE SYSTEM SHALL use `/api/agents/{agent_id}/mcp*` and persist on that agent profile only.
- **[REQ-421-004]** WHEN the operator views Skill Studio after this card, THE SYSTEM SHALL still bind tools onto skills via the existing catalog checkboxes and SHALL NOT require Tools Studio to write `skill_tool_bindings`.
- **[REQ-421-005]** AFTER cutover, THE SYSTEM SHALL NOT present two full competing MCP writer UIs (Settings full form and Tools Studio full form both active without a thin-shell link).
- **[REQ-421-006]** THE SYSTEM SHALL NOT ship a naked custom-tool scaffold / approve factory as part of Tools Studio v1.

---

## 6. Verification

Automated (during build):

- Vitest: dock opens Tools Studio; catalog rows render from the catalog API used by the pane; MCP list hydrates; Skill Studio binding tests remain green.
- Existing MCP route tests for `/api/settings/mcp*` and `/api/agents/{id}/mcp*` stay green.

Manual live test (say **merge to qa** only after this):

1. Pull `feat/card-421-*`, reload serve, hard-refresh.
2. Open **Tools Studio** from the dock. You see catalog browse and MCP attach/status.
3. Add or test a platform MCP server in Tools Studio. It appears in the list with status. Settings no longer has a second full writer (link or thin status only).
4. Select an agent and attach or view an agent-scoped MCP server in Tools Studio. Saving updates that agent only.
5. Open Skill Studio. Tool checkboxes still bind tools onto a skill and save bindings as before.
6. Open Agent Studio. You do not need the old full Forge MCP form to complete the happy path (status + open Tools Studio is enough unless the documented cutover kept a minimal forge form).

---

## 7. Honest scope note

CARD-420 left developer mediation APIs in tree without a Skill Studio Ask developer button. This card similarly ships a **real** catalog + MCP operator path with durable state. Custom MCP-only capability lifecycle is the **next** Tools slice after v1, not theatre inside this card.
