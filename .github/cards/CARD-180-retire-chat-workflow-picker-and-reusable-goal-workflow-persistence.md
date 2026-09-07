# [CARD-180] Retire Chat Workflow Picker and Reusable Goal Workflow Persistence

> **Status**: Ready
> **Created**: 2026-09-07
> **Spec Reference**: CARD-123; CARD-174
> **Labels**: `type:cleanup`, `type:ui`, `AutoReiv.Chat`, `AutoReiv.Orchestration`

---

## 1. Why / Intent

In CARD-123, AutoReiv introduced a mechanism where a completed Goal plan could be saved as a static "Workflow" JSON recipe, and re-executed via a "Workflow" dropdown picker in the chat bar.

In practice, this feature creates unnecessary cognitive friction and architectural clutter:
1. **Dial Overload in Chat**: Users are forced to choose between "Goal Mode" and "Workflow", causing confusion about which to use.
2. **Static Plans vs. Dynamic LLMs**: Freezing 3 or 4 step titles into a static template often yields worse results than allowing the Planner to formulate fresh steps tailored to the current context.
3. **Misleading Nomenclature**: Calling a static checklist a "Workflow" creates a false expectation of automation pipelines. True automation belongs to **Routines** (scheduled background execution) and **Pipelines/Graphs** (like the Agent Training Factory), while reusable instructions belong to **Saved Prompts** (CARD-152).

This card retires the chat-level Workflow picker and the "Save as workflow" button, streamlining the chat interface into a lean, intuitive experience: **Prompt + Goal Mode (with auto-Verify).**

---

## 2. Three Beats: How It Works

### Beat 1: Chat Bar Cleanup
1. **What you see**: A clean chat input bar containing only the prompt input and the Goal Mode toggle (with auto-Verify from CARD-179). The empty/disabled Workflow dropdown is completely gone.
2. **What AutoReiv does now**: `src/web/static/modules/studios/chat.js` and `index.html` mount `#chatWorkflowPicker` directly next to the Goal checkbox.
3. **What will change**: Remove `#chatWorkflowPicker` and its options loader.

### Beat 2: Job Card Actions Cleanup
1. **What you see**: When a multi-phase Goal finishes running in chat, the job card displays its completion status cleanly without a "Save as workflow" button. Reusable tasks are saved as prompts in Prompts Studio instead.
2. **What AutoReiv does now**: Completed multi-phase jobs render a "Save as workflow" button that prompts the user for a recipe name and writes a JSON file.
3. **What will change**: Remove the "Save as workflow" button and its modal handler from `chat.js`.

### Beat 3: Backend Stream Payload Simplification
1. **What you see**: Chat streaming requests are simpler and faster, processing only the user prompt, agent ID, and goal mode.
2. **What AutoReiv does now**: `src/web/routers/chat.py` inspects `req.workflow_id`, checks for saved JSON files, and branches job creation.
3. **What will change**: Remove the chat-level `workflow_id` branching from `chat.py`.

### Beat 4: Agent Studio Workflows Card Cleanup
1. **What you see**: In Agent Studio, the inspector for an agent cleanly shows Identity, System Prompt, Tone & Avatar, Platform Skills, Custom Runbooks, Native & MCP Tools, Storage, and Memory. The unused "Workflows: Saved multi-step plans" box is gone.
2. **What AutoReiv does now**: `src/web/templates/index.html` lines 928 and 1363-1380 render a "Workflows" box with `#studioWorkflowsList`, and `src/web/static/modules/studios/forge.js` fetches `/api/agents/{agent_id}/workflows` to render and edit chapters.
3. **What will change**: Remove the Workflows box from `index.html` and remove the `loadAgentWorkflows`, chapter editing, saving, and deletion code from `forge.js`.

---

## 3. Technical Touchpoints

| Layer | Component | File Path |
| :--- | :--- | :--- |
| **Frontend UI** | Chat Studio (remove picker & save button) | `src/web/static/modules/studios/chat.js` |
| **Frontend UI** | Agent Studio (remove workflows inspector card & loader) | `src/web/static/modules/studios/forge.js` |
| **Frontend Template** | Chat Input Drawer & Agent Studio HTML Markup | `src/web/templates/index.html` |
| **Backend Router** | Chat Stream Request Handler | `src/web/routers/chat.py` |

---

## 4. Acceptance Criteria (Definition of Done)

- [ ] [REQ-CLEAN-001] Remove `#workflowPicker` dropdown and its population logic from `chat.js` and HTML templates.
- [ ] [REQ-CLEAN-002] Remove the "Save as workflow" button (`#saveAsWorkflowBtn`) and modal trigger from `chat.js` and HTML templates.
- [ ] [REQ-CLEAN-003] Remove `workflow_id` parameter handling and branching from `src/web/routers/chat.py`.
- [ ] [REQ-CLEAN-004] Remove `#studioWorkflowsList` box and all workflow chapter rendering/management functions (`loadAgentWorkflows`, etc.) from Agent Studio in `forge.js` and `index.html`.
- [ ] [REQ-CLEAN-005] All automated unit and integration tests pass cleanly via `pytest` and `vitest`.
- [ ] [REQ-CLEAN-006] Zero lint errors via `ruff check .`.

---

## 5. Constraints & Working Agreement

- **Ready card only. Do not implement until Jacob explicitly says build.**
- Work strictly on local `qa` branch.
- No third-party product names in card or code.
