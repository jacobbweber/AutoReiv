---
id: CARD-411
title: "Skill Runbook YAML Frontmatter, Tool Binding UI, and Forge vs Factory Separation"
status: Ready
created: 2026-09-21
adr: none
labels:
  - type:feat
  - type:refactor
  - area:ux
  - area:skills
  - area:forge
---

# [CARD-411] Skill Runbook YAML Frontmatter, Tool Binding UI, and Forge vs Factory Separation

> **Status**: Ready  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:feat`, `type:refactor`, `area:ux`, `area:skills`, `area:forge`  

---

## 1. Why / Intent (Beat 1: What Jacob Means)

Jacob has identified two closely linked architectural and UX opportunities regarding how skills, tools, and agents are edited:

1. **Runbook Frontmatter & Tool Binding Visibility**:
   - When clicking `[Edit Runbook]` in Agent Studio (Forge), the editor currently displays mostly the markdown body or basic text.
   - The operator cannot easily inspect or edit the YAML frontmatter (`name`, `description`, `tier`, `requires_tools`, `verification`, `safety`).
   - If a user wants to bind an additional tool to a skill (or remove one), there is no UI affordance to add tools to `requires_tools`.

2. **The Forge vs. Factory Single Lever Dilemma**:
   - Currently, tool-to-skill bindings and skill authoring sit awkwardly between Agent Studio (Forge) and the Agent Training Factory.
   - In the Factory, you can associate tools to skills during capability manufacturing, but you cannot easily pick an existing skill to edit it.
   - In Forge, you can edit runbooks, but cannot manage tool bindings.
   - **Architectural Question**: Should we enforce a strict Single Lever separation:
     - **Agent Studio (Forge)** = Strictly an **RBAC assignment surface** per agent (toggle skills on/off, assign tones, models, providers, and agent-level overrides).
     - **Agent Training Factory** = The **single workshop** where skills, tools, runbooks, and capability definitions are birthed, modified, tested, and bound?
     - Or do some agent levers belong in the Factory as well?

---

## 2. What AutoReiv Does Now (Beat 2: Current Behavior & Gaps)

1. **Forge Runbook Editor Gaps**:
   - `forge/runbook_editor.js` renders a modal editing `SKILL.md`.
   - Frontmatter is parsed but not presented as structured interactive inputs (e.g. tag chips, multi-select tool pickers for `requires_tools`).
   - Adding a tool requires hand-crafting YAML lines in the raw markdown text, risking syntax breakage.
2. **Dual-Location Confusion**:
   - Users look in Forge to edit what a skill *is*, but Forge is designed around *who* the agent is.
   - Training Factory generates skills through an 8-phase pipeline, but lacks an "open existing skill in workshop" flow.

---

## 3. What Will Change (Beat 3: Technical Implementation Options)

### Discussion & Architectural Hypotheses for Jacob:

#### Option A: Clean Responsibility Separation (Recommended)
- **Agent Studio (Forge)**:
  - Focused strictly on **Agent Identity & RBAC**: Identity prompt, model, tone, context budget, and checkboxes for which platform/user skills this agent is allowed to execute.
  - Viewing a skill opens a read-only runbook inspector with a shortcut: `[Open in Factory Workshop ↗]`.
- **Training Factory**:
  - The single canonical **Capability Workshop**:
  - Author, edit, and test skills, tool bindings (`requires_tools`), and runbook markdown.
  - Structured frontmatter editor with multi-select tool picker from the platform tool catalog.
- **Benefits**: Zero duplicate levers. Clear mental model: *Forge manages agents; Factory builds capabilities.*

#### Option B: Hybrid In-Place Editor in Forge
- Keep the runbook editor modal in Forge, but enhance it with:
  1. Structured header cards showing parsed frontmatter fields.
  2. Multi-select chip input to easily add/remove tools from `requires_tools`.
  3. Live validation preventing saving if a tool is not in the platform catalog.
- **Benefits**: Fast editing without navigating away from the agent you are configuring.

---

## 4. What Dies Today (Beat 4: The Prune List)

- **PRUNE**: Manual raw text editing of YAML frontmatter headers in runbooks.
- **PRUNE**: Ambiguous boundaries where both studios partially attempt to manage skill-tool associations.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-411-001] Structured Runbook Metadata UI**:
  - *Ubiquitous*: THE SYSTEM SHALL render structured metadata controls (name, description, required tools multi-select, tier, safety) when inspecting or editing a skill runbook.
- **[REQ-411-002] Tool-to-Skill Binding Affordance**:
  - *Event-Driven*: WHEN an operator adds or removes a tool in the skill editor, THE SYSTEM SHALL automatically update `requires_tools` in the YAML frontmatter with valid catalog tool identifiers.
- **[REQ-411-003] Single Lever Studio Alignment**:
  - *Ubiquitous*: THE SYSTEM SHALL establish a single canonical path for skill/tool modification according to the agreed division between Forge and Factory.

---

## 6. Constraints & Verification Plan

### Automated Tests
- Backend test for skill frontmatter serialization: Verify adding/removing tools in API preserves markdown body and valid frontmatter.
- Frontend Vitest tests for the runbook tool selector and metadata rendering.

### Manual Verification
1. Open a skill in the agreed studio (Forge or Factory).
2. Add a new required tool via the picker and save.
3. Verify: `SKILL.md` frontmatter contains the tool, and agents with this skill gain access to the tool upon next turn.
