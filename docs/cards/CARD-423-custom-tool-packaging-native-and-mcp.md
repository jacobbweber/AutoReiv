---
id: CARD-423
title: "Custom tool packaging: native and MCP (dual lanes) + developer skills"
status: Ready
created: 2026-09-22
adr: docs/adr/0057-three-studios-and-developer-mediated-authoring.md
labels:
  - type:feat
  - area:tools
  - area:mcp
  - area:developer
  - area:policy
---

# [CARD-423] Custom tool packaging: native and MCP (dual lanes) + developer skills

> **Status**: Ready (written in advance so the slice is not forgotten)  
> **Created**: 2026-09-22  
> **ADR Reference**: [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md) (packaging policy: allow both; tighten later)  
> **Depends on**: [CARD-421](./CARD-421-tools-studio-v1-catalog-and-mcp-attach.md); preferably [CARD-422](./CARD-422-tools-studio-form-and-developer-mediation.md) if form chooses packaging lane  
> **Policy lock (2026-09-22)**: MCP is **not** required for every custom tool. Platform tools need no MCP. Custom tools may be **native** AutoReiv tools or **MCP-backed**. Operator / Jacob may tighten later.

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine AC / tighten policy wording — **no product code** |
| **`build`** | Implement on `feat/card-423-*` from `qa` |
| **`merge to qa`** | After In Review + live test |

---

## 1. Why / Intent (Beat 1)

Jacob clarified that pointing at a folder of scripts means **tell the developer agent a path in conversation** and ask for one tool per script or playbook — not a Tools Studio folder factory. He asked whether AutoReiv should force an MCP server between every custom tool and the runtime. Objectively, MCP adds a valuable shared protocol and isolation for many cases, but it is not always worth the ceremony for a small local helper. **Locked: allow both lanes; tighten later if needed.**

This card implements dual packaging and the developer skills/runbooks so the developer agent builds AutoReiv tools and MCP servers correctly.

---

## 2. What AutoReiv does now (Beat 2)

- Platform / built-in tools already run without MCP.
- Custom capability scaffold paths exist; ADR previously steered custom via MCP only for the first custom lifecycle — **amended** to allow native custom tools as well.
- Developer packs may already know general MCP patterns; AutoReiv-specific tool and MCP runbooks may still be thin or missing.

---

## 3. What will change (Beat 3)

1. Document and implement **two packaging lanes** for custom tools:
   - **Native**: tool registered and executed inside AutoReiv's tool/capability path (no MCP server required).
   - **MCP-backed**: developer builds or wraps an MCP server; AutoReiv attaches it; tools appear grouped under that server in Tools Studio.
2. Form / developer brief (CARD-422) can record which lane was chosen; catalog labels source clearly (platform / native custom / MCP server name).
3. Add or harden **developer skills / runbooks** for AutoReiv tool development and MCP server wrapping (including "here is a directory of scripts — expose one tool per entry" as a **chat-driven** developer task, not a studio folder picker).
4. Guardrails for native tools (permissions, sandboxing, HITL where already required) without pretending MCP is the only safety layer.
5. Optional later tighten: policy flag or ADR amendment to prefer or require MCP for classes of tools — out of this card unless Jacob asks.

**Out of scope:** moving MCP hosting into Tools Studio; Tools Studio code editor; SSH host address book.

---

## 4. What dies (Beat 4)

- Hard requirement that **every** custom tool must sit behind an MCP server (replaced by dual lanes).
- Expectation that point-at-folder is a first-class Tools Studio UI factory (it is developer conversation context).

---

## 5. Acceptance criteria (EARS)

- **[REQ-423-001]** THE SYSTEM SHALL allow a custom tool to be packaged as a native AutoReiv tool without requiring an MCP server.
- **[REQ-423-002]** THE SYSTEM SHALL allow a custom tool to be packaged behind an MCP server that AutoReiv attaches, with tools discoverable under that server in Tools Studio when CARD-421 grouping exists.
- **[REQ-423-003]** WHEN the operator or developer supplies a filesystem path in developer conversation as context for wrapping scripts or playbooks, THE SYSTEM SHALL treat that as developer input context and SHALL NOT require a Tools Studio folder-picker factory for that story.
- **[REQ-423-004]** THE SYSTEM SHALL provide developer-facing skill or runbook guidance specific to building AutoReiv tools and MCP wrappers (not only generic MCP knowledge).
- **[REQ-423-005]** THE SYSTEM SHALL label catalog entries so the operator can tell platform, native custom, and MCP-provided tools apart.

---

## 6. Verification

Manual live test after build:

1. Create or accept one **native** custom tool path end-to-end; agent can call it without an MCP attach.
2. Create or accept one **MCP-backed** custom tool path; attach server; tool appears under that server in Tools Studio.
3. Developer chat can take a path string and produce a wrap plan or implementation without a studio folder picker.
4. Developer skill/runbook for AutoReiv tools/MCP is present and used in the happy path.

---

## 7. Honest scope note

This card exists so allow-both is not a chat-only decision. CARD-421 does not implement dual lanes; it only browses and attaches. CARD-422 collects intent. CARD-423 makes packaging and developer guidance real.
