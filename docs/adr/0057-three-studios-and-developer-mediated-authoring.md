# [ADR-0057] Three Studios and Developer-Mediated Authoring

> **Status**: Accepted
> **Accepted**: 2026-09-22 (Jacob: Accept ADR-0057)
> **Date**: 2026-09-22  
> **Deciders**: Jacob (Visionary & Product Owner), AutoReiv Harness Engineer  
> **Consulted**: CARD-417 planning; CARD-411 Option A live test  
> **Related Cards**: [CARD-417](../cards/CARD-417-three-studios-agent-skill-tools-and-developer-mediated-authoring.md) (forks locked), [CARD-418](../cards/CARD-418-skill-studio-extract-from-factory.md) (first implementation slice), [CARD-421](../cards/CARD-421-tools-studio-v1-catalog-and-mcp-attach.md) (Tools Studio v1), [CARD-422](../cards/CARD-422-tools-studio-form-and-developer-mediation.md), [CARD-423](../cards/CARD-423-custom-tool-packaging-native-and-mcp.md), [CARD-424](../cards/CARD-424-mcp-disable-must-unmount.md), [CARD-411](../cards/CARD-411-skill-runbook-yaml-frontmatter-tool-binding-ui-and-forge-vs-factory-separation.md), [ADR-0056](./0056-durable-runtime-registry-hybrid-c-plus.md)  
> **Supersedes / Softens**: Long-term “Agent Training Factory does agent + skill + tools on one screen” as the operator authoring model

---

## 1. Context & Problem Statement

AutoReiv’s durable primitives are **agents**, **skills (runbooks)**, and **tools (capabilities / MCP)**, with scoping edges agent↔skill and skill↔tool. CARD-411 locked Option A write paths (Forge inspect-only for runbooks; Factory writes skill bodies + SQLite tool bindings). Live testing still showed friction: one Factory screen forces three different lifecycle jobs together.

Jacob locked CARD-417 product forks (2026-09-22): three studios; skill toggle pills; Build/Review defaults to a **visible** developer job; Tools Studio v1 is catalog + MCP attach; then form/developer (CARD-422) and dual native/MCP packaging (CARD-423); tier stays quiet; storage folder redesign deferred under ADR-0056.

This ADR records those decisions as platform policy so implementation cards stay coherent.

---

## 2. Decision Drivers

* Single-lever Studios: one place per primitive’s lifecycle.
* Non-developer operators still get Matt Pocock / “good agent” quality via the **developer** specialist.
* SQLite remains sole writer for bindings (ADR-0056); no revival of `pack.json` as live binding truth.
* Thin, shippable slices; no theatre Studios without durable state and proof.
* Visible trust for LLM-mediated edits (watchable job/conversation).

---

## 3. Considered Options

| Option | Summary | Outcome |
|--------|---------|---------|
| Keep all-in-one Factory | Polish three columns forever | **Rejected** — structural friction |
| Two studios (Agent + Skill); Tools later | Delay Tools Studio | Softened into phased **A** (Tools is studio 3, v1 thin) |
| Invisible-only LLM fill | Studio button, no thread | **Rejected as default** — poor teachability; allowed only for cheap lint |
| Three studios + visible developer mediation | Agent / Skill / Tools; Build opens developer job | **Chosen** |

---

## 4. Decision Outcome (Accepted)

### 4.1 Studio topology

| Studio | Owns | Does not own |
|--------|------|--------------|
| **Agent Studio** | Agent identity, preferences, “good agent” standards, **skill on/off toggles (pills)** | Skill body, frontmatter, tool bindings |
| **Skill Studio** | Skill lifecycle, structured frontmatter, tool scoping onto the skill, Save to skill store + SQLite bindings | Agent identity editing (deep-link to Agent Studio) |
| **Tools Studio** | Tool catalog, MCP attach/status, and custom tools on either lane: native AutoReiv tools or MCP-backed tools (CARD-423) | Skill runbook authorship; agent RBAC; MCP hosting (stays in Settings) |

Factory’s three-column scaffolder is a **transitional** UI. Implementation extracts Skill Studio first; agent brief leaves that surface over subsequent cards; Tools Studio is new dock surface.

### 4.2 Scoping UI

- Agent↔skill: **toggle pills** (not chips-as-editor).
- Skill↔tool: catalog multi-select / checkboxes in Skill Studio (CARD-411 path retained).

### 4.3 Developer-mediated authoring

- Studio fields are the operator **draft**.
- **Build / Review** submits a structured packet to the **developer** specialist as a **visible standing job / conversation** (default).
- Operator may watch Observe/Chat, reply with context, and accept field patches back into the Studio.
- **Invisible** path allowed only for **cheap lint** (valid frontmatter, catalog tool ids, contract linter). Full LLM rewrite must not be silent-only.

### 4.4 Tools policy

- **v1**: catalog browse + MCP server attach/status/test hooks.
- **Then**: custom capabilities via **dual lanes** (amended 2026-09-22 with Jacob): **native** AutoReiv tools **or** **MCP-backed** tools. MCP is not required for every custom tool; tighten later if needed. Tools Studio v1 still has **no** naked script-folder factory UI (chat-path to developer is fine; see CARD-423).
- **Legacy pack modules** (amended 2026-09-23, CARD-425): `packs/<id>/tools/*.py` stays an explicit in-process loader. It is registered with origin `legacy_pack_tool` and catalogued as **Legacy pack tool**. It is not the CARD-423 native custom lane (`native_custom_tools`, sandbox, ToolPolicyGate HITL, catalog origin **Native custom**). This card does not rewrite those modules through the sandbox.
- **MCP hosting** operator UI stays in **Settings forever** (not Tools Studio).
- Exact MCP deploy/attach mechanics are implementation-card scope under this policy.

### 4.5 Explicitly deferred

- Removing tier from data model (UI already quiet).
- Monolith `agents/` / `skills/` / `tools/` folder redesign (ADR-0056 remains ownership source).

### 4.6 Binding & storage invariants (unchanged)

- Operational SQLite writes skill/tool bindings.
- Skill bodies live in the filesystem skill store / pack skill trees as ADR-0056 allows.
- Export/import round-trips bindings + stable ids.

---

## 5. Consequences

### Positive

* Clear operator mental model matching the three primitives.
* Quality gated by developer specialist without hiding the work.
* Aligns with CARD-411 Option A and ADR-0056.

### Negative / risks

* More dock surfaces and deep-links to maintain.
* Developer mediation needs reliable form↔job packet schema and apply-back UX.
* Tools Studio v1 may feel thin until CARD-422 (form/developer) and CARD-423 (dual packaging) land.

### Follow-up

* Accept this ADR → implement via thin cards starting at CARD-418 (Skill Studio extract).
* Later: Agent pills, developer mediation v1, Tools Studio v1, optional tier kill.

---

## 6. Accept / Reject

**Accepted** 2026-09-22 by Jacob. Implementation proceeds via thin cards starting at CARD-418 (Skill Studio extract); say **build CARD-418** to start product code.