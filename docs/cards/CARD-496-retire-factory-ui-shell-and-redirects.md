---
id: CARD-496
title: "Retire the Agent Training Factory (2/4): remove the Factory UI and redirect every entry point"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-495
  - CARD-497
  - CARD-498
  - CARD-472
  - CARD-418
  - CARD-306
labels:
  - type:cleanup
  - area:factory
  - area:frontend
  - P1
---

# [CARD-496] Retire the Agent Training Factory (2/4): remove the Factory UI and redirect every entry point

> **Status**: Ready (ADR-0060 Accepted 2026-09-25 with D1-D8; build after CARD-495 is Done). Card decisions D1-D3 below are still to confirm at `build`
> **Created**: 2026-09-25
> **Series**: CARD-495 → **CARD-496** → CARD-497 → CARD-498
> **Labels**: `type:cleanup`, `area:factory`, `area:frontend`, `P1`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** No Factory screen, Lab Monitor or training popup anywhere. Every button that used to open the Factory takes you to the Studio or Developer chat that does the job now.

**Beat 2: What AutoReiv does now** (qa `6bedb5b0`):
- **Factory dock tab and view:** `#tab-factory` (index.html L167) and `#view-factory` (L3941). `studios/factory.js` (251 lines) saves nothing (only `GET /api/agents`, L112).
- **Lab Monitor drawer:** `#labMonitorDrawer` (L4823), `forge/lab_monitor.js`.
- **Training popup:** `#trainAgentHandshakeModal` (L4630). Its X, Cancel and Start are unbound (`chat.js` L666-670 passes `state` to `setupTrainModal`), so Retry traps you.
- **Training code:** `chat/train_modal.js`, and `chat/training.js` (payload plus promotion card).
- **`render.js` handlers:** L760-767 (launch-factory), L780-796 (open-lab-drawer), L798-850 (approve/reject promotion).
- **Hidden leftovers:** `#trainAgentToggle` (L454), `#trainAgentBadge` (L572), and `chat.js` L319 and L479-481 (a missing select).
- **Entry points into Factory:**
  - Forge gap backlog "Open Training Factory" (`forge/tools.js` L80-100);
  - Forge "Open Training Factory" (index.html L1623; `forge/scaffold.js` L365-380);
  - Forge Lab Monitor button (`lab_monitor.js` L563-574);
  - new-agent scaffold jumps to Factory (`scaffold.js` L335);
  - chat "agent created" card "Launch Training in Factory" (`chat/stream.js` L196);
  - `window.openFactoryStudioForAgent` and `callbacks.openFactoryStudio` (`app.js` L282).
- **Skill Studio imports** `factory/workshop_meta.js` and `factory/skill_scope.js` (`skill_studio.js` L11-12).

**Beat 3: What will change.**
1. Delete: the Factory tab, view and `factory.js`; the Lab Monitor drawer and `lab_monitor.js`; the training popup, `train_modal.js` training code and `training.js`; the `render.js` Factory/Lab/promotion handlers; the hidden toggle, badge and dead lookups; `openFactoryStudio` and `openFactoryStudioForAgent`.
2. Move `factory/workshop_meta.js` and `factory/skill_scope.js` to `studios/skill_studio/` and update imports (no behaviour change).
3. Redirect:
   - gap backlog: **Open in Skill Studio** (agent scoped) and **Ask Developer** (Tools Studio talk with the gap text, same path as CARD-472);
   - new agent created: stay in Agent Studio with a toast "Agent created. Add skills in Skill Studio.";
   - chat "agent created" card: **Open in Skill Studio**;
   - Forge "Open Training Factory" and Lab Monitor buttons: removed.
4. Rename the Teach button class `btn-escalate-factory` to `btn-escalate-developer`.
5. Update the agent desktop and dock registries so no Factory window can be restored from saved layout.

**Beat 4: What dies.** The Factory screen, Lab Monitor, training popup, Retry, promotion cards, and every "Factory" label in the UI.

## 2. Acceptance criteria (EARS)

- **[REQ-496-001]** THE SYSTEM SHALL NOT render `#tab-factory`, `#view-factory`, `#labMonitorDrawer`, `#trainAgentHandshakeModal`, `#trainAgentToggle` or `#trainAgentBadge`.
- **[REQ-496-002]** WHEN Jacob clicks a gap's **Open in Skill Studio**, THE SYSTEM SHALL open Skill Studio scoped to that agent. WHEN he clicks **Ask Developer**, THE SYSTEM SHALL open a Developer chat with the gap text.
- **[REQ-496-003]** WHEN an agent is created in Agent Studio, THE SYSTEM SHALL stay in Agent Studio and show "Agent created. Add skills in Skill Studio."
- **[REQ-496-004]** WHILE a saved desktop layout references the Factory window, THE SYSTEM SHALL drop it on restore without errors.
- **[REQ-496-005]** Skill Studio SHALL behave exactly as before after the module move (existing CARD-418/419/420 tests pass unchanged apart from import paths).

## 3. Decisions

| # | Decision | Recommendation |
|---|----------|----------------|
| D1 | Keep a "Factory" alias that opens Skill Studio? | **No**: ADR-0057 wants one lever per job |
| D2 | Gap backlog actions | **Open in Skill Studio + Ask Developer** |
| D3 | Old promotion cards in chat history | Render nothing for their buttons; the text stays |

## 4. Failing-tests-first plan

- **Vitest:** a negative-DOM test for REQ-001; gap backlog buttons call `openSkillStudio` / the talk endpoint; the scaffold success path doesn't call any Factory opener; Skill Studio imports resolve from the new folder; saved-layout restore drops `factory`.
- Delete Factory-only Vitest files: `factory_studio`, `lab_monitor_*`, `train_agent_handshake`, `factory_deliverable_modal`, `card_411_factory_layout`. Adjust `chat_train_workbench_keep_one_306`, `card_411_forge_factory_split` and `auto_train_backlog` to the new contract.
- **Smoke (desktop and phone):** the dock has no Factory; gap backlog **Open in Skill Studio** opens Skill Studio; the chat has no training popup.

## 5. Runbook

1. The dock has no Factory.
2. Agent Studio: create an agent; you stay in Agent Studio with the toast.
3. The gap backlog (seed a gap through `POST /api/agents/{id}/gaps` on the scratch server) shows Open in Skill Studio and Ask Developer, and both work.
4. On phone, the same checks.

## Audit revisions (CARD-495 audit, 2026-09-25)

- **Also remove the Agent Studio "Agent Training Optimization" panel** (`index.html` L1615-1642, `forge/scaffold.js` L159-210, `forgeScaffoldOpenFactoryBtn` L366-380). Its queue is always empty (CARD-495 audit F16). Backend goes in CARD-512.
- **Keep** Skill Studio's `factory*` DOM ids inside `#view-skill-studio` (decision D5). Only `#view-factory` goes.
- `agent_picker.js` L13: drop only the `factory` key; the picker stays for Agent Studio, Tools Studio and the desktop.
- Delete the `AUTO_TRAIN_PROGRESS` handler in `chat.js` L851 and the autonomous-training inputs in `forge.js` L493-496 (decision D7).
- Test: `openSkillStudio(agentId)` from the gap backlog opens Skill Studio for that agent.
