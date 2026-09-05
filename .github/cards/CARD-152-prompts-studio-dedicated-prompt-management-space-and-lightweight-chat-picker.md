# [CARD-152] Prompts Studio: Dedicated Prompt Management Space and Lightweight Chat Picker

> **Status**: Done
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Memory`

---

## 1. Why / Intent

Users manage and execute numerous prompt templates (system audits, meeting summaries, task rollovers, structured code reviews, research queries).
Mixing full prompt authoring, editing, tagging, and deletion inside the Chat Studio options drawer adds unnecessary clutter and breaks conversational flow.
Instead:
1. **Prompts Studio (`#promptsStudio`)**: A dedicated first-class management studio in the main navigation (alongside Agent Studio, Skills Studio, and Workflows Studio) providing a full dual-pane editor to organize, tag, edit, test, and delete prompts.
2. **Lightweight Chat Quick-Picker**: In Chat Studio's options drawer, a streamlined quick-picker dropdown/menu (`#chatPromptsQuickPicker`) to filter and drop any saved prompt directly into the input dock with 1 tap.

---

## 2. Visual Wireframe

### Prompts Studio (`#promptsStudio`)
```text
+---------------------------------------------------------------------------------------------------------+
| [✨ Prompts Studio]                                                   [ + New Prompt ]  [ Refresh ]     |
+---------------------------------------------------+-----------------------------------------------------+
| [ 🔍 Search prompts, tags... ]                    | [ ✏️ Edit Prompt: System Health Diagnostic         ]    |
| Filters: [ All ] [ System ] [ Productivity ] ...  | Title:       [ System Health & Telemetry Diagnostic ]|
+---------------------------------------------------+ Category:    [ System v ]                           |
| [★ Builtin] [System]                              | Description: [ Comprehensive platform diagnostics   ]|
| System Health & Telemetry Diagnostic              | Tags:        [ #health #sre #diagnostics            ]|
| "Run a comprehensive platform health..."          +-----------------------------------------------------+
+---------------------------------------------------+ Template Text:                                      |
| [Productivity]                                    | Run a comprehensive platform health diagnostic:     |
| Weekly Summary & Task Rollover                    | inspect active providers, tool error matrices, and  |
| "Review this week's active and completed..."      | recent system logs, then summarize operational      |
+---------------------------------------------------+ health.                                             |
| [Coding]                                          +-----------------------------------------------------+
| Code Architecture Review                          | Variables: {agent}, {scope}                         |
| "Perform a thorough architecture..."              | [ Save Changes ]   [ Test in Chat ]   [ 🗑️ Delete ] |
+---------------------------------------------------+-----------------------------------------------------+
```

### Chat Studio Lightweight Quick-Picker
```text
+------------------------------------------------------------+
| [ + Options ] ➔ [ 📝 Quick Prompt v ]                      |
+------------------------------------------------------------+
|  🔍 Type to filter prompts...                              |
|  --------------------------------------------------------- |
|  ★ System Health Diagnostic               [ ↵ Insert ]     |
|  ★ Weekly Summary & Task Rollover          [ ↵ Insert ]     |
|  ★ Code Architecture Review                [ ↵ Insert ]     |
|  ★ Meeting Notes to Wiki                   [ ↵ Insert ]     |
|  --------------------------------------------------------- |
|  [ ⚙️ Manage Prompts in Prompts Studio ➔ ]                  |
+------------------------------------------------------------+
```

---

## 3. What to Build

1. **Navigation & Surface Integration (`src/web/templates/index.html`, `src/web/static/modules/layout/navigation.js`)**:
   - Add **Prompts** tab to the sidebar navigation (`#navPrompts`, icon: `sparkles`, title: *"Prompts Studio"*).
   - Add `#promptsStudio` view container in `index.html` with dual-pane layout:
     - Left pane: Search bar, category filter pills, prompt card list with built-in badges.
     - Right pane: Rich prompt editor form with Title, Category, Description, Tags, and full-height Template Text editor.
2. **Prompts Studio Logic (`src/web/static/modules/studios/prompts.js`)**:
   - Modular studio controller following AutoReiv's studio standards.
   - Handles list loading, searching, category filtering, selecting prompt for editing, creating new prompts, and deleting custom prompts.
   - Includes `[ Test in Chat ]` button that switches navigation to Chat Studio and pre-fills the prompt!
3. **Chat Studio Lightweight Quick-Picker (`src/web/static/modules/studios/chat.js`)**:
   - In `#chatOptionsDrawer`, replace the modal popup with a fast, lightweight popover dropdown (`#chatPromptsQuickPicker`).
   - Typing in the filter narrows down templates instantly.
   - Tapping any template instantly inserts it into `#promptInput` and closes the drawer.
   - Bottom link: *"Manage in Prompts Studio ➔"* navigates to Prompts Studio.

---

## 4. Acceptance Criteria (Definition of Done)

- [x] `[REQ-PROMPT-STUDIO-001]`: Sidebar includes **Prompts Studio** navigation item with active tab tracking.
- [x] `[REQ-PROMPT-STUDIO-002]`: Prompts Studio provides a full-width dual-pane management interface to create, edit, categorize, tag, and delete prompts.
- [x] `[REQ-PROMPT-STUDIO-003]`: Prompts Studio includes `[ Test in Chat ]` to transition to Chat Studio with the selected prompt staged.
- [x] `[REQ-PROMPT-STUDIO-004]`: Chat Studio's options drawer provides a lightweight, non-intrusive Quick Prompt picker for 1-click insertion.
- [x] `[REQ-PROMPT-STUDIO-005]`: Automated unit tests for Prompts Studio navigation, DOM structure, and quick-picker.
- [x] `[REQ-PROMPT-STUDIO-006]`: Zero linting errors via `ruff` and `eslint`.

---

## 5. Honor Flags & SDLC Invariants

- Card stays **Ready** until Jacob says `build`.
- Code changes remain isolated on `qa`.
- Unit tests written before production code (TDD Red-Green-Refactor).
