---
id: CARD-496
title: "Retire the Agent Training Factory (2/6): remove the Factory UI and redirect every entry point"
status: Ready
created: 2026-09-25
updated: 2026-09-25
branch: qa
related:
  - CARD-495
  - CARD-511
  - CARD-497
  - CARD-512
  - CARD-498
  - CARD-514
  - CARD-472
  - CARD-418
  - CARD-306
labels:
  - type:cleanup
  - area:factory
  - area:frontend
  - P1
---

# [CARD-496] Retire the Agent Training Factory (2/6): remove the Factory UI and redirect every entry point

> **Status**: Ready for `build` (refined 2026-09-25 ~11:55 PM ET on qa `7b22c933`; the Factory UI was reproduced on a scratch server with fresh data; decisions D1-D10 below wait for Jacob)
> **Created**: 2026-09-25
> **Governing ADR**: [ADR-0060](../adr/0060-retire-the-agent-training-factory.md) (Accepted). This card is step 2 of 6: CARD-495 (Done), **CARD-496**, CARD-511, CARD-497, CARD-512, CARD-498
> **Scope**: frontend only. **No backend route changes.** Skill Studio keeps calling `/api/agent_training_factory/{capabilities,scaffold/*,skills}` until CARD-497 moves them.
> **Labels**: `type:cleanup`, `area:factory`, `area:frontend`, `P1`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first on `feat/card-496-retire-factory-ui` |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis (carries the CARD-495 docs commits) |

---

## 1. Four Beats

**Beat 1: What Jacob means.** No Factory screen, Lab Monitor, training popup or "Agent Training Optimization" panel anywhere. Every button that used to open the Factory now goes to the Studio or Developer chat that does the job. Skill Studio, Tools Studio, Agent Studio, Teach and gaps keep working exactly as before.

**Beat 2: What AutoReiv does now.** Reproduced 2026-09-25 ~11:52 PM ET on a scratch server (port 8767, fresh data `scratch\c496_audit`, never Jacob's AppData), desktop 1440x900 and phone 390x844, Playwright scripts `scratch\c496_probe.mjs` and `c496_probe2.mjs`. There were **0 console or page errors** on either size.

| Surface | Where (qa `7b22c933`) | Seen on scratch |
|---|---|---|
| Dock **Factory** button and Factory window | `#tab-factory` index.html L167; `#view-factory` L3941; `studios/factory.js`; dock entry `ui/agent-desktop.js` L113-115, L192, L506; `agent_desktop/presets.js` L25; `agent_desktop/window.js` L513-514; `app.js` L18, L103, L128, L166-168, L184-185, L282-287, L301, L402-404, L466-470; CSS `studios.css` L290-322 | Dock shows **Factory** (13 dock buttons). The window says "Factory Ready. Agent brief and assigned skills. Author runbooks in Skill Studio", with an agent brief form and a "Target Specialist" picker. It saves nothing. Visiting it writes `localStorage.autoreiv_factory_selected_agent_id = "__new__"` |
| **Lab Monitor** drawer | `#labMonitorDrawer` L4823; `forge/lab_monitor.js` (wired from `forge.js` L31, L39-42, L683, L728) | There is no button to open it (`#forgeLabMonitorBtn` is not in the template). It opens only through `window.openLabMonitorDrawer`, which the chat's `.open-lab-drawer-btn` calls. It shows "Lab Training Monitor. No training runs found" and 8 training stages. `lab_monitor.js` L220 fetches `GET /api/agent_training_factory/jobs` when Agent Studio loads (seen in the request log) |
| **Training popup** | `#trainAgentHandshakeModal` L4630 ("Launch Autonomous Loop" L4733); `chat/train_modal.js`; `chat/training.js` (payload plus promotion card); `chat.js` L15, L24, L30, L79, L314, L474-476, L659-664 | Hidden, and there is no visible trigger. The hidden leftovers `#trainAgentToggle` (L454) and `#trainAgentBadge` (L572) are still in the page |
| Chat Factory handlers | `chat/render.js` L739-748 (`launch-factory`), L759-776 (`open-lab-drawer`), L777-813 (approve and reject promotion, which calls `/jobs/{id}/promote`) | Reachable only from a training job, and there are none |
| **"Agent created" chat card** | `chat/stream.js` L170-205: "Specialist agent is ready for capability training. Open Factory Studio…" with **Launch Training in Factory** plus **Open in Studio**. Rendered from `scaffold_agent_pack` tool results, live and **when old history is re-rendered** (`render.js` L610-627). There is also a dead branch at `chat.js` L826-830: the server never sends a `handoff` event, it sends `handoff_start`/`handoff_complete` (`routers/chat.py` L393-396) | Shown every time a chat that created an agent is reopened |
| **"Agent Training Optimization" panel** | `#forgeScaffoldQueueCard` L1611-1643, inside Agent Studio's collapsed **Capabilities** section (L1544); `forge/scaffold.js` L159-210, L348-380 | Refresh calls `GET /api/capabilities/scaffold/candidates?limit=50` and gets an empty list. **Open Training Factory** (`#forgeScaffoldOpenFactoryBtn`) opens the Factory window |
| **Gap backlog** | `<details id="agentTrainingBacklogCard">` "Needs Training Backlog" L1351-1362 (collapsed); `forge/tools.js` L56-115 | With one gap seeded (`POST /api/agents/autoreiv/gaps`, 200), it shows **Open Training Factory** and **Dismiss**. Open Training Factory opens the Factory window with `factoryAgentSelect = autoreiv` |
| New agent via the Quick Scaffold modal jumps to the Factory | `forge/scaffold.js` L330-339 | **Unreachable**: `#forgeQuickScaffoldBtn`, the only opener of `#forgeNewAgentModal` (L5018), is not in the template. Agent Studio's New Agent hands off to AutoReiv chat (`forge.js` L657-664, `app.js` L276-281). Filed as CARD-514 |
| Agent picker `factory` key | `studios/agent_picker.js` L13, L185-202 (fills `#factoryAgentSelect`, which lives in `#view-factory`) | See the Factory row |
| Auto-training | `forge.js` L493-496 copies `allow_autonomous_training`/`max_training_retries` into the Save payload (there is no visible input). `chat.js` L851-856 handles `auto_train_progress`, which is never sent | Nothing to see |
| Skill Studio save still refreshes the Factory | `skill_studio.js` L370-374 calls `callbacks.getFactoryCtrl().loadFactoryStudio(pinAgentId)` after a pinned save | Harmless now; dead once the Factory is gone |
| Skill Studio imports Factory files | `skill_studio.js` L11-12 import `./factory/workshop_meta.js`, `./factory/skill_scope.js` | Skill Studio works: 105 tool checkboxes. It calls `GET /api/agent_training_factory/capabilities` and `/skills` (both 200) and has 31 `factory*` ids inside `#view-skill-studio` |
| Teach "Ask Developer" | `render.js` L267 `data-factory-escalation`, L301 `.btn-escalate-factory`; `teach_modal.js` L13, L114-143 | Works (smoke TC-34 (CARD-472) and TC-35/TC-36 (CARD-500); TC-35 already asserts no `/api/agent_training_factory` call after load) |
| Other | `events/event-bus.js` L14 `FACTORY_OPEN` (no users); `forge.js` L4 comment; `skill_studio.js` L3-4, L31 comments | n/a |

**Beat 3: What will change.**
1. **Delete** the Factory tab, window and `factory.js`, including its app registrations, desktop dock entry, preset entry, the window.js special case (keep it for skill-studio and tools-studio) and the CSS. Also delete:
   - the Lab Monitor drawer and `lab_monitor.js`;
   - the training popup, `train_modal.js`, `training.js` and their chat wiring;
   - `#trainAgentToggle` and `#trainAgentBadge`;
   - the `render.js` launch-factory, open-lab and promotion handlers;
   - `openFactoryStudio`, `window.openFactoryStudioForAgent` and `getFactoryCtrl`;
   - `FACTORY_OPEN`;
   - the "Agent Training Optimization" panel and its JS in `scaffold.js` (L159-210, L348-380; the backend stays for CARD-512);
   - the `auto_train_progress` branch and the dead `handoff` branch in `chat.js`;
   - the auto-training copy in the `forge.js` Save payload (D7).
2. **Move** `factory/workshop_meta.js` and `factory/skill_scope.js` to `studios/skill_studio/` and update the imports in `skill_studio.js` and tests. There is no behaviour change. The URLs they call stay the same (CARD-497 moves them).
3. **Redirect:**
   - **Gap backlog:** replace Open Training Factory with **Open in Skill Studio**, which calls `callbacks.openSkillStudio(agentId)` (`app.js` L288), and **Ask Developer**. Ask Developer builds a draft from the gap (tool name = `suggested_tool_name`, behavior = the gap text), then `POST /api/tools_studio/authoring/talk`, then `interpretAuthoringTalk`, then `switchTab('chat')` and `getChatCtrl().openDeveloperSession(...)`. That is the same path Teach (`teach_modal.js` L114-133) and Tools Studio (`tools_studio.js` L300-311) use, with Tools Studio as the fallback. Dismiss stays.
   - **"Agent created" chat card:** replace Launch Training in Factory with **Open in Skill Studio**, and change the copy to "Add skills in Skill Studio, or open it in Agent Studio." Open in Studio becomes **Open in Agent Studio** (same handler). Old history re-renders with the new card because the HTML is built at render time.
   - **Quick Scaffold success:** stay in Agent Studio (the existing toast plus `onLoadAgent`). Drop the Factory jump only (D6).
   - **Skill Studio pinned save:** drop the Factory refresh (L370-374). Nothing replaces it; Agent Studio already reloads the agent when it is opened.
4. **Rename** the Teach button class `btn-escalate-factory` to `btn-escalate-developer`. Keep the `data-factory-escalation` attribute until CARD-497 renames the backend field (D10).
5. **Picker:** drop `PICKER_KEYS.factory` and the `#factoryAgentSelect` block, and remove the stale `autoreiv_factory_selected_agent_id` entry once on load (D8).
6. **Saved desktop layouts:** drop `factory` from `openWindows`, window geometry and saved presets when prefs are read (D9).
7. **Labels:** "Needs Training Backlog" becomes **"Capability gaps"** (D4). The id `agentTrainingBacklogCard` and `data-section` stay.
8. **Keep** Skill Studio's `factory*` ids (ADR-0060 D5). Bump `app.js?v=` so browsers load the new modules.

**Beat 4: What dies.** The Factory window, Lab Monitor, training popup, promotion cards, the Optimization panel UI, and every visible "Factory" or "Training Factory" label. The skill pill "Agent Capability Architecture & Training" is a pack skill name, which CARD-497 rewrites.

---

## 2. What must keep working (the regression fence)

| Flow | Why it is at risk | Guard |
|---|---|---|
| Skill Studio: open, list tools, generate runbook, save, pin to agent, load a skill | Imports move; still calls `/api/agent_training_factory/{capabilities,scaffold/runbook,scaffold/save,skills}` | Existing CARD-418/419/420 Vitest (import paths updated only); new smoke: Skill Studio lists tools, and a save through the page gets 200 |
| Tools Studio: catalog, talk to Developer | `tools_studio_catalog.js` L513 calls `/api/agent_training_factory/capabilities` | CARD-421 Vitest unchanged; smoke opens Tools Studio |
| Agent Studio: load agent, skill pills, Save | Save payload changes (D7); scaffold.js edits | CARD-509 tests; smoke Save round trip |
| Teach: distill, adopt, Ask Developer | Class rename | Smoke TC-34/35/36 updated to `.btn-escalate-developer`, still asserting no Factory call |
| Gaps: list, dismiss, and the two new actions | Rewritten buttons | New Vitest plus smoke |
| Desktop restore | Saved `factory` window | New Vitest plus smoke with a seeded layout |

---

## 3. Acceptance criteria (EARS)

- **[REQ-496-001]** THE SYSTEM SHALL NOT render `#dock-factory`, `#tab-factory`, `#view-factory`, `#labMonitorDrawer`, `#trainAgentHandshakeModal`, `#trainAgentToggle`, `#trainAgentBadge`, `#forgeScaffoldQueueCard` or `#forgeScaffoldOpenFactoryBtn`.
- **[REQ-496-002]** THE SYSTEM SHALL NOT show the words "Training Factory", "Factory Studio" or "Lab Training Monitor" in any visible UI text.
- **[REQ-496-003]** WHEN Jacob clicks a gap's **Open in Skill Studio**, THE SYSTEM SHALL open Skill Studio for that gap's agent.
- **[REQ-496-004]** WHEN Jacob clicks a gap's **Ask Developer**, THE SYSTEM SHALL post the gap as a Tools Studio authoring draft and open the Developer chat with the returned prompt. IF that fails, THEN THE SYSTEM SHALL show an error toast and open Tools Studio for that agent.
- **[REQ-496-005]** WHEN a `scaffold_agent_pack` result renders in chat (live or from history), THE SYSTEM SHALL show **Open in Skill Studio** and **Open in Agent Studio**, and no Factory button.
- **[REQ-496-006]** WHEN Quick Scaffold creates an agent, THE SYSTEM SHALL stay in Agent Studio with that agent loaded.
- **[REQ-496-007]** WHILE a saved desktop layout or preset lists `factory`, THE SYSTEM SHALL drop it on load without errors.
- **[REQ-496-008]** WHEN the app loads, THE SYSTEM SHALL NOT call `/api/agent_training_factory/jobs` or `/api/capabilities/scaffold/*`.
- **[REQ-496-009]** Skill Studio, Tools Studio, Agent Studio Save and Teach SHALL behave as before. Their existing tests SHALL pass with only import-path and class-name edits.
- **[REQ-496-010]** THE SYSTEM SHALL NOT change any backend route in this card.

---

## 4. Decisions (confirm at `build`)

D1-D3 are restated from the first draft, adjusted to what the scratch run showed. D4-D10 are new.

| # | Decision | Recommendation |
|---|---|---|
| D1 | Keep a "Factory" alias (dock button or URL) that opens Skill Studio? | **No.** One lever per job (ADR-0057/0060) |
| D2 | Gap backlog actions | **Open in Skill Studio + Ask Developer** (Ask Developer uses the Teach/Tools Studio talk path, with Tools Studio as fallback); Dismiss stays |
| D3 | Promotion cards in old chat history | **Delete the code.** They were built only live after a training job and are not saved in history (`training.js` L68; no stored message type), so nothing old breaks. The "agent created" card, which *is* re-rendered from history, gets the new buttons (D5) |
| D4 | Rename "Needs Training Backlog" | **Yes, to "Capability gaps"** (label only; ids stay) |
| D5 | "Agent created" chat card | **Open in Skill Studio + Open in Agent Studio**, with new copy |
| D6 | Quick Scaffold modal (unreachable, no opener) | **Remove only its Factory jump here.** Deleting the dead modal is CARD-514 |
| D7 | Stop sending `allow_autonomous_training` / `max_training_retries` on Agent Studio Save | **Yes.** The API then applies its defaults (False/2, `routers/agents.py` L48-49), and nothing reads these fields (audit F17). CARD-497 removes them from the API; the columns stay |
| D8 | Clear the stale `autoreiv_factory_selected_agent_id` localStorage entry | **Yes, once on load** (no user value) |
| D9 | Saved desktop layouts and presets that include `factory` | **Drop silently on load** |
| D10 | Teach button class and attribute | **Rename the class to `btn-escalate-developer` now; keep `data-factory-escalation`** until CARD-497 renames the backend field |

---

## 5. Failing-tests-first plan

Write these tests first, confirm they fail on qa, then build.

**Vitest (new file `tests/unit/frontend/card_496_retire_factory_ui.test.js`):**
1. `index.html` has none of the REQ-001 ids, and none of the REQ-002 phrases outside comments.
2. `app.js`, `agent-desktop.js`, `presets.js` and `window.js` register no `factory` tab. `app.js` has no `openFactoryStudio`/`getFactoryCtrl`; `event-bus.js` has no `FACTORY_OPEN`.
3. Gap backlog:
   - `loadAgentCapabilityGaps` renders **Open in Skill Studio** and **Ask Developer**; clicking them calls `callbacks.openSkillStudio('autoreiv')`;
   - Ask Developer posts `{intent:'create', draft:{tool_name, behavior}}` to `/api/tools_studio/authoring/talk`, then calls `openDeveloperSession`;
   - on a 500 it falls back to `openToolsStudio`.
4. `renderAgentHandoffCardHtml` has no `launch-factory` and shows both new buttons; the delegation handler routes Open in Skill Studio to `openSkillStudio`.
5. Quick Scaffold success path calls no Factory opener.
6. Desktop prefs: `openWindows: ['chat','factory']` reads back as `['chat']`; presets lose `factory`; window geometry for `factory` is dropped.
7. `agent_picker.js` has no `factory` key and removes the stale storage entry.
8. `chat.js` has no `auto_train_progress` or dead `handoff` branch; the `forge.js` Save payload has no auto-training fields.
9. `skill_studio.js` imports from `./skill_studio/`; no file under `studios/factory/` exists; `skill_studio.js` has no `getFactoryCtrl`.

**Delete Factory-only Vitest files:** `factory_studio`, `factory_deliverable_modal`, `card_411_factory_layout`, `lab_monitor_fail_reason`, `lab_monitor_controls`, `lab_monitor_artifact_preview`, `train_agent_handshake`.

**Update to the new contract** (assertions about removed Factory UI become negative, or are dropped):
- `card_411_forge_factory_split`, `chat_train_workbench_keep_one_306`, `auto_train_backlog`, `agents_constitution_training_304`, `agent_picker_refresh_410`, `agent_desktop`;
- `card_418_skill_studio` (import path; L141 reads `factory.js` and goes), `card_419_skill_toggle_pills` and `card_420_skill_authoring` (import paths only; the `/api/agent_training_factory/scaffold/save` URL assertions stay until CARD-497);
- `chat_decomposed_modules`, `forge_monolith_decomposition_398`, `single_lever_dedup_384`, `socratic_agent_scaffold`, `chat_picker_sessions_drawer_296`, `dom_audit`, `forge_allowlist`, `chat_workbench_teach_wiring_472`, `teach_distill_contract_500`, `skill_distillation_ui`, `card_421_tools_studio`, `chat_composer_grow_465`.

Keep the net Vitest count honest: report deleted versus added.

**Playwright smoke (`tests/e2e/smoke.spec.js`), desktop and phone:**
- TC-1: expect `#dock-factory` to have **count 0** (was `toBeVisible`, L48).
- New TC: seed a gap through the API.
  - The Agent Studio "Capability gaps" section shows Open in Skill Studio, and clicking it shows `#view-skill-studio`.
  - Ask Developer, with the talk route mocked, opens chat with the Developer prompt.
- New TC: seed desktop prefs with a `factory` window; the page loads with 0 errors and no Factory window.
- New TC: the app loads, opens Agent Studio, Skill Studio and Tools Studio, and makes no request to `/api/agent_training_factory/jobs` or `/api/capabilities/scaffold/`. Skill Studio still lists tools.
- TC-34/35/36: switch to `.btn-escalate-developer`; keep the no-Factory-call assertion.

**Full suites at In Review:** unit, integration, Vitest, smoke, ESLint and ruff. The only allowed failures are the known CARD-454/456 ones.

---

## 6. Runbook (live test on Jarvis, after build)

On a scratch server first (`scratch\c505_run.ps1 -Data c496_rb -Wipe`, port 8767), then on serve at 0.0.0.0:8000.

1. **Dock:** there is no Factory button on desktop or phone, and the other 12 dock buttons are there.
2. **Agent Studio:**
   - Pick AutoReiv. Open **Capabilities**: there is no "Agent Training Optimization" panel.
   - Open **Capability gaps** (seed one first: `POST /api/agents/autoreiv/gaps` with `turn_text`, `identified_capability`, `suggested_tool_name`). It shows **Open in Skill Studio**, **Ask Developer** and **Dismiss**.
3. **Open in Skill Studio:** Skill Studio opens with AutoReiv selected, and the tool list loads.
4. **Ask Developer:** chat opens on Developer with the gap in the composer or first message. If Developer can't be reached, Tools Studio opens with a toast.
5. **Skill Studio save:** create skill `c496_probe`, generate a runbook, save with AutoReiv pinned. You get "Saved c496_probe and pinned to autoreiv", and the Agent Studio pills show it.
6. **Tools Studio:** the catalog loads.
7. **Teach:** in chat, Teach a reply to get a needs-tool proposal, then Ask Developer. The Developer chat opens.
8. **Old history:** reopen a chat where AutoReiv created an agent. The card shows Open in Skill Studio and Open in Agent Studio.
9. **Saved layout:** with the Factory window open in a saved layout from before the build, reload. There are no errors and no Factory window.
10. **DevTools network:** there is no `/api/agent_training_factory/jobs` and no `/api/capabilities/scaffold/`. The console has 0 errors.
11. Restart serve with `scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000`; health returns 200 on 127.0.0.1 and 192.168.1.99. Repeat steps 1-4 on the phone.

---

## 7. Definition of done

- REQ-496-001..010 pass.
- Tests are written first and were seen failing.
- Full suites pass, apart from the known CARD-454/456 failures.
- The runbook passes on scratch and on serve (desktop and phone).
- There are no backend changes.
- CARD-497's "Audit revisions" still matches, and the Skill Studio routes are untouched.
- The card is set to In Review with evidence, then Done at `merge to qa`.

## Audit revisions (CARD-495 audit, 2026-09-25)

These are folded into the sections above:
- the "Agent Training Optimization" panel removal;
- Skill Studio's `factory*` ids kept;
- the picker `factory` key dropped;
- the `AUTO_TRAIN_PROGRESS` handler and auto-training payload removed;
- `openSkillStudio(agentId)` from the gap backlog.
