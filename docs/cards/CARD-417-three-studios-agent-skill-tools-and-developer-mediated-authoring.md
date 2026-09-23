---
id: CARD-417
title: "Three Studios: Agent / Skill / Tools Lifecycle Surfaces and Developer-Mediated Authoring"
status: Ready
created: 2026-09-22
adr: docs/adr/0057-three-studios-and-developer-mediated-authoring.md
labels:
  - type:architecture
  - type:planning
  - area:ux
  - area:studios
  - area:skills
  - area:agents
  - area:tools
---

# [CARD-417] Three Studios: Agent / Skill / Tools Lifecycle Surfaces and Developer-Mediated Authoring

> **Status**: Ready (planning / decision — **no product code** until Jacob says **build** after forks are locked)
> **Created**: 2026-09-22
> **ADR Reference**: [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md) (**Accepted** 2026-09-22; forks locked)
> **Labels**: `type:architecture`, `type:planning`, `area:ux`, `area:studios`, `area:skills`, `area:agents`, `area:tools`
> **Depends on**: CARD-411 Done (Option A Forge/Factory split + SQLite skill tool bindings on `qa` / `v0.40.0`)

---

## Gate language (exact reply phrases)

This card **requires a decision/design phase before build**.

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Discuss, refine inventory, compare options, draft ADR language — **still no product code** |
| **`build`** | Only after product-policy forks below are locked and (if needed) an ADR is **Accepted** |
| **`merge to qa`** | Only after In Review + live operator test of eventual implementation card(s) |

Do **not** treat scaffolding this Ready card as approval to implement.

---

## 1. Four Beats

### Beat 1 — What Jacob means

After CARD-411, the healthy mental model is three primitives and two scoping edges:

1. **Agent** — identity, “what makes a good agent,” preferences; then **skill on/off** (prefer toggle pills).
2. **Skill (runbook)** — Matt Pocock–style lifecycle; then **tools scoped onto the skill**.
3. **Tool / MCP** — capabilities (built-in, MCP, or custom). Custom deterministic scripts should prefer a **custom MCP server** for consistency rather than one-off script sprawl (policy still open).

Friction today: Factory tries to do agent brief + skill authoring + tool catalog on **one screen**. That forces three different jobs into one place. Fields for agent and skill are mostly right; the levers live in the wrong studios, and Tools has almost no lifecycle surface.

Jacob also wants **deterministic, non-developer UX**: drafts (typed in Studio UI or talked through with an agent) should be filtered through the **developer specialist** as source of truth for good-agent / good-skill / good-tool+MCP standards, with feedback back into the Studio.

Open design questions (see forks):

- Visible developer **job/conversation** vs invisible backend review when the operator hits Build/Review.
- How Tools Studio defines and tests custom tools + MCP attach/deploy.
- Whether tier (`user` / `platform` / `pack`) dies as an operator concept.
- Whether interchange folders should become clearer `agents/` / `skills/` / `tools/` under ADR-0056 (SQLite remains binding registry).

### Beat 2 — What AutoReiv does now

| Surface | Role today | Gap |
|---------|------------|-----|
| **Agent Studio (Forge)** | Agent identity + RBAC; CARD-411 made skill **Inspect** read-only + Open in Factory | Skill scoping UI still not “toggle pills only”; still shares mental space with Factory |
| **Factory** | Three columns: agent brief, skill workshop, tools/grounding | Agent + skill + tools co-located; still named “Factory / scaffolder” |
| **Tools** | Catalog checkboxes inside Factory col 3; MCP elsewhere | No Tools Studio; no first-class custom tool / MCP lifecycle |
| **Developer agent** | Exists as a specialist pack; used for coding/MCP work | Not wired as the canonical authoring gate for Studio Build/Review |
| **Bindings** | CARD-411: SQLite `skill_tool_bindings` + skill store bodies | Agent↔skill still pack/SQLite allowlists; tier taxonomy still in frontmatter |

Standards already in product (must keep):

- Built-in “what makes a good agent” guidance / scaffolder invariants.
- Matt Pocock–style skill runbook structure + capability linter (ADR-0054 / skill contracts).

### Beat 3 — What will change (target shape)

#### Recommended studio split

1. **Agent Studio** — agent lifecycle + **skill toggles** only. No skill body / tool binding edits (already Option A).
2. **Skill Studio** — promote today’s Factory col 2+3: skill lifecycle + tool scoping. Drop agent-brief half over time (or deep-link to Agent Studio).
3. **Tools Studio (new)** — catalog, MCP attach/deploy, custom capability requests with guardrails; testing harness.

#### Developer-mediated authoring (recommended default)

- Studio fields remain the operator’s draft.
- **Build / Review** submits a structured packet to the **developer** specialist as a **visible standing job / Chat thread** (option A below) so the operator can watch, reply, and keep context.
- Cheap lint (valid frontmatter, catalog tool ids) may stay invisible in-form.
- Invisible full LLM pass (option B) is secondary — faster, less teachable.

#### Out of scope for first implementation slice (unless Jacob expands)

- Full Agents/Skills/Tools monolith folder redesign (ADR-0056 amendment + migration).
- Killing every Factory label overnight without a cutover plan.
- Implementing custom Ansible/Terraform/PowerShell tool factories before Tools Studio policy is locked.

### Beat 4 — What dies

- Single “Factory does everything” as the long-term authoring model.
- Operator expectation that hand-editing YAML/tier taxonomy is how scoping works.
- Dual write paths for skill tool bindings (`pack.json` as live truth) — already dying under CARD-411 / ADR-0056; this card must not revive them.

---

## 2. Product-policy forks (Jacob must lock before build)

| # | Fork | Options | Status |
|---|------|---------|----------------|
| 1 | Studio topology | **A)** Three studios (Agent / Skill / Tools). **B)** Keep Factory name but hide agent half. **C)** Two studios only (Agent + Skill); Tools later. | **LOCKED: A** |
| 2 | Agent↔skill UI | Toggle pills vs checkboxes vs chips-as-editor | **LOCKED: toggle pills** |
| 3 | Build/Review UX | **A)** Visible developer job/conversation. **B)** Invisible backend fill. **C)** Both (A default, B for lint-only). | **LOCKED: C with A default** |
| 4 | Custom tools policy | **A)** Custom capabilities only via MCP server. **B)** Allow naked scripts with guardrails. **C)** Defer Tools Studio v1 to catalog+MCP attach only. | **LOCKED: C then A** |
| 5 | Tier taxonomy | **A)** Hide now, remove later. **B)** Remove from operator UI + data in same program. **C)** Keep forever. | **LOCKED: A** |
| 6 | Storage/interchange | Leave ADR-0056 packs as-is vs plan `agents/`/`skills/`/`tools/` materialization | **LOCKED: Defer** |

---


---

## Locked decisions (Jacob 2026-09-22)

All six recommended forks are **locked**. Planning may continue (ADR outline, successor card slice); **no product code** until Jacob says **build**.

| # | Decision |
|---|----------|
| 1 | **Three studios**: Agent Studio, Skill Studio, Tools Studio. Skill Studio = today’s Factory col 2+3 promoted; Tools is new; Factory-as-all-in-one fades. |
| 2 | **Agent↔skill UI**: toggle **pills** on/off in Agent Studio. Chips that open a skill editor are not the scoping lever; skill editing lives only in Skill Studio. |
| 3 | **Build/Review UX**: **visible developer job/conversation as default**; invisible path only for cheap lint (valid frontmatter, catalog tool ids). Studio form remains the draft; developer returns suggested field patches / blockers the operator can accept. |
| 4 | **Custom tools policy**: Tools Studio **v1 = catalog + MCP attach/status**; then **custom capabilities via MCP only**. No naked script factory in v1. |
| 5 | **Tier**: keep **quiet/hidden** in operator UX now; remove from operator model in a later thin card. |
| 6 | **Storage/interchange**: **defer** `agents/` / `skills/` / `tools/` monolith folder redesign; stay on ADR-0056 until Studios UX lands. |

### Recommended build order (after **build**)

1. Skill Studio extract (Factory col 2+3 → Skill Studio; deep-link from Forge Inspect).
2. Agent Studio skill toggle pills; remove residual skill-edit chrome.
3. Developer mediation v1 (Build/Review → visible job with form packet; apply approved patches back to Studio).
4. Tools Studio v1 (catalog + MCP attach/status).
5. Optional: tier removal; interchange folder planning under ADR-0056.


## 3. Acceptance criteria (planning card)

- **[REQ-417-001]** Inventory document (this card §Beat 2 + linked design note if needed) lists current Studio levers and ownership without inventing new dual truths.
- **[REQ-417-002]** Jacob locks forks 1–6 (or explicitly defers numbered items).
- **[REQ-417-003]** If topology or developer-mediation changes lasting platform contracts, an ADR is drafted and **Accepted** before any **build**.
- **[REQ-417-004]** Successor implementation cards are sliced thin (e.g. Skill Studio extract → Agent toggle polish → Tools Studio v1 → developer mediation wire-up).

---

## 4. Suggested implementation sequence (after Accept / build)

1. **Skill Studio extract** — Factory col 2+3 become Skill Studio; deep-link from Forge Inspect / Open in Workshop.
2. **Agent Studio skill toggles** — pills on/off; remove residual skill-edit chrome.
3. **Developer mediation v1** — Build/Review → visible job with form packet; apply approved field patches back to Studio.
4. **Tools Studio v1** — catalog + MCP attach/status; custom tool policy deferred or MCP-only.
5. Optional: tier removal + interchange folder planning under ADR-0056.

---

## 5. Constraints

- SQLite remains sole writer for bindings (ADR-0056 / CARD-411).
- No product code on this card; docs/ADR only until **build**.
- Anti-theatre: every Studio must have durable state, operator path, failure modes, and proof when implemented.

---

## 6. Live discussion capture (2026-09-22)

Jacob (paraphrase): designing an agent is its own need; skills need their own space with tool scoping; tools/MCP need a future studio; one screen forces friction; developer agent should be source of truth for good agents/skills/tools; unsure how Studio UI ↔ developer LLM loop should feel (ticket/conversation vs invisible). CARD-411 layout direction was endorsed minus populate bug (fixed before merge).

## Successor cards

- [CARD-418](./CARD-418-skill-studio-extract-from-factory.md) — Skill Studio extract (slice 1) — **Done**.
- [CARD-419](./CARD-419-agent-studio-skill-toggle-pills.md) — Agent Studio skill toggle pills (slice 2) — **Done**.
- [CARD-420](./CARD-420-developer-mediated-authoring-v1-visible-build-review.md) — Developer mediation v1 (slice 3) — **Done**.
- Later (not scaffolded yet): Tools Studio v1.
