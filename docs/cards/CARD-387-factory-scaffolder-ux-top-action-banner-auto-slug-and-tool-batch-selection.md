---
id: CARD-387
title: "Factory Scaffolder UX Top Action Banner Auto Slug and Tool Batch Selection"
status: Ready
created: 2026-09-20
adr: none
labels:
  - type:feature
  - domain:factory
  - domain:skills
  - domain:tools
  - domain:agents
---

# [CARD-387] Factory Scaffolder UX Top Action Banner Auto Slug and Tool Batch Selection

> **Status**: Ready  
> **Created**: 2026-09-20  
> **ADR Reference**: ADR-0048, ADR-0052  
> **Labels**: `type:feature`, `domain:factory`, `domain:skills`, `domain:tools`, `domain:agents`

---

## 1. Why / Intent (Beat 1)

### What Jacob Means
1. **Automated `snake_case` Agent ID**: In Column 1 (Agent Brief), when creating a new specialist, the Agent ID (Slug) should not require manual typing or formatting. As the user enters the Display Name (e.g., "3D Scene Artist"), the Agent ID should automatically populate as a clean `snake_case` identifier (e.g., `3d_scene_artist`) and be non-fillable (`readonly`), removing human error and formatting friction.
2. **Prune Redundant Model Dropdown**: The `Default Model` dropdown at the bottom of Column 1 is redundant clutter. In AutoReiv, model providers and fallbacks are configured canonically in Agent Studio and Settings Studio. It should be removed.
3. **Intuitive Top Action Banner**: In the current 3-column layout, the operator selects/identifies the agent (Col 1), defines the skill intent and trigger (Col 2), and selects tools and grounding context (Col 3). Having the `[✨ Generate / Refine Runbook]` button stuck midway in Column 2 forces an awkward backwards jump after completing Column 3. Moving the primary generation button and `[💬 Talk it out with Forge]` into a dedicated horizontal banner floating above the three columns creates an intuitive, left-to-right, top-to-bottom natural flow that scales dynamically on both mobile and desktop.
4. **Batch Tool Selection & Auto-Suggest**: When an agent needs domain tools (e.g. Blender with 24 tools), ticking every tool individually is tedious. Column 3 needs a `[Select All]` and `[Clear]` button next to the search filter (matching Agent Studio's pattern) so filtering "blender" and clicking `[Select All]` checks all 24 tools instantly. Additionally, an `[🪄 Auto-Suggest Tools]` button will match tools from the catalog based on the skill name, trigger, and intent notes.

---

## 2. What AutoReiv Does Now (Beat 2)

- `factoryAgentIdInput` is an editable text input requiring manual typing and formatting.
- `factoryAgentModelSelect` exists at the bottom of Column 1, taking up vertical space for redundant settings.
- `factoryGenerateRunbookBtn` is located in Column 2 between the notes textarea and the runbook editor.
- `factoryIntakeTalkToForgeBtn` is placed in Column 1's footer.
- Column 3 only has a text filter (`factoryToolSearchInput`). Ticking filtered tools requires clicking every checkbox individually.
- No automated keyword/intent tool suggestion exists in the scaffolder.

---

## 3. What Will Change (Beat 3)

### 3.1 Horizontal Top Action Banner
- Add `#factoryTopActionBar` above the 3 columns in `src/web/templates/index.html`:
  - Contains `[✨ Generate / Refine Runbook]` (`#factoryGenerateRunbookBtn`), execution status indicator (`#factoryGenerateStatusText`), and descriptive helper text.
  - Contains `[💬 Talk it out with Forge]` (`#factoryIntakeTalkToForgeBtn`) on the right.
  - Dynamically resizes and wraps gracefully on mobile devices.

### 3.2 Column 1 Refinements
- Make `factoryAgentIdInput` `readonly` with subtle styling (`bg-white/[0.03] text-slate-400 cursor-not-allowed`).
- When `factoryAgentSelect.value === '__new__'`, input on `factoryAgentNameInput` automatically updates `factoryAgentIdInput.value` using `toSnakeCase(name)`.
- Delete `factoryAgentModelSelect` and its label.
- Remove the Column 1 footer that previously held `factoryIntakeTalkToForgeBtn`.

### 3.3 Column 2 Refinements
- With `Generate Runbook` moved to the top banner, the `SKILL.md Runbook (Editable)` textarea sits directly below the trigger and intent inputs.
- `[💾 Save & Pin Skill to Agent]` remains anchored at the bottom of the column.

### 3.4 Column 3 Batch Tool Selection & Auto-Suggest
- Next to `#factoryToolSearchInput`, add:
  - `[Select All]` (`#factorySelectAllToolsBtn`)
  - `[Clear]` (`#factoryClearAllToolsBtn`)
  - `[🪄 Auto-Suggest]` (`#factoryAutoSuggestToolsBtn`)
- When `Select All` is clicked, all currently visible/filtered capability checkboxes are checked and `#factorySelectedToolCountBadge` updates.
- When `Clear` is clicked, all currently visible capability checkboxes are unchecked.
- When `Auto-Suggest` is clicked, the system searches tool names and descriptions matching words in Skill Name, Trigger, and Intent, ticks the matches, and displays a toast notification.

---

## 4. What Dies Today (The Prune List - Beat 4)

1. **`#factoryAgentModelSelect`**: Completely deleted from `src/web/templates/index.html`.
2. **Model Selection References**: Pruned from `factory.js` (`const factoryAgentModelSelect = ...`).
3. **Manual Agent Slug Editing**: Replaced by automated `snake_case` derivation from Display Name.
4. **Column 1 Stranded Button Footer**: Pruned in favor of the unified `#factoryTopActionBar`.
5. **Mid-Column Generation Placement**: Excised from Column 2.

---

## 5. Acceptance Criteria (EARS Syntax)

- **Ubiquitous**: THE SYSTEM SHALL provide a persistent top action banner (`#factoryTopActionBar`) above the 3-column scaffolder containing `[✨ Generate / Refine Runbook]` and `[💬 Talk it out with Forge]`.
- **Event-Driven**: WHEN the user enters text in `#factoryAgentNameInput` while creating a new agent, THE SYSTEM SHALL automatically populate `#factoryAgentIdInput` with the `snake_case` slug and keep the field non-editable (`readonly`).
- **Event-Driven**: WHEN the user enters a search term in `#factoryToolSearchInput` and clicks `#factorySelectAllToolsBtn`, THE SYSTEM SHALL check all visible tool checkboxes and update `#factorySelectedToolCountBadge`.
- **Event-Driven**: WHEN the user clicks `#factoryClearAllToolsBtn`, THE SYSTEM SHALL uncheck all visible tool checkboxes and update the badge.
- **Event-Driven**: WHEN the user clicks `#factoryAutoSuggestToolsBtn`, THE SYSTEM SHALL inspect the skill name, trigger, and intent, check all matching tool checkboxes in the catalog, and update the selection badge.
- **Negative Assertion**: THE SYSTEM SHALL NOT render `#factoryAgentModelSelect` anywhere in the Factory Studio DOM.
- **Negative Assertion**: Automated tests shall verify that `#factoryAgentIdInput` is marked `readonly` when creating a new agent.

---

## 6. Constraints & Verification Plan

### Automated Tests
- `tests/unit/frontend/factory_studio.test.js`:
  - Assert `#factoryTopActionBar` exists and contains the generate and forge buttons.
  - Assert `#factoryAgentModelSelect` is absent from the DOM.
  - Assert `#factoryAgentIdInput` is `readonly` and updates to `snake_case` as `#factoryAgentNameInput` changes.
  - Assert `#factorySelectAllToolsBtn` checks all filtered tools.
  - Assert `#factoryClearAllToolsBtn` clears visible tools.
  - Assert `#factoryAutoSuggestToolsBtn` selects tools matching the entered skill intent.
- Full Vitest test suite (`npx vitest run`) passes 100%.
- ESLint (`npm run lint:frontend`) passes with 0 errors and 0 warnings.
- Ruff (`uv run ruff check .`) passes.

### Manual Verification Runbook
1. Open AutoReiv serve (`http://127.0.0.1:8000`) and switch to Factory tab.
2. In Column 1, ensure `+ Create New Agent` is selected.
3. Type `3D Scene Artist` into Display Name. Verify Agent ID automatically shows `3d_scene_artist` and cannot be directly edited.
4. Verify there is no `Default Model` dropdown in Column 1.
5. In Column 2, enter Skill Name: `Blender Rendering`, Trigger: `Render 3D assets with Blender`.
6. In Column 3, type `blender` in the filter and click `[Select All]`. Verify all Blender tools are checked and badge says `24 Selected`.
7. Click `[Clear]`. Verify all are unchecked.
8. Click `[🪄 Auto-Suggest]`. Verify Blender tools are automatically detected and selected based on the skill trigger.
9. At the top banner, click `[✨ Generate / Refine Runbook]`. Verify the runbook generates into Column 2's editor without requiring scrolling or jumping.
