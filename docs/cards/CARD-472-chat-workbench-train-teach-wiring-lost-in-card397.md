---
id: CARD-472
title: "Workbench, Train-agent handshake and Teach modal close wiring lost in the CARD-397 split"
status: Ready
created: 2026-09-24
updated: 2026-09-25
branch: qa
related:
  - CARD-397
  - CARD-469
  - CARD-138
  - CARD-165
  - CARD-306
  - CARD-352
  - CARD-495
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P1
---

# [CARD-472] Workbench, Train-agent handshake and Teach modal close wiring lost in the CARD-397 split

> **Status**: Ready (refined after Jacob's **continue**, 2026-09-25)
> **Created**: 2026-09-24
> **Observed during**: CARD-469 planning. I diffed every `addEventListener` in pre-split `chat.js` (`7b563003^`) against current `chat.js` and `chat/*`. `git blame` puts the broken call sites on `7b563003` (CARD-397, 2026-09-20 11:06 PM ET).
> **Reproduced**: 2026-09-25 ~3:15 PM ET on a scratch server (`scripts/smoke_server.py` on 127.0.0.1:8767 with a throwaway data dir, fake Ollama on 18434, no real AppData), driven by a Playwright script on desktop 1280x800 and phone 390x844. qa `f895c0cc`.
> **Related**: CARD-397, CARD-469, CARD-138, CARD-165, CARD-306, CARD-352, follow-up **CARD-495**
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `P1`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

The buttons in chat should do what they say:

- **Workbench**: the header button and each message's "Workbench" button open the side panel with that text. "View Full Report" on an artifact card opens that saved artifact. Close, back, Preview/Raw, Copy and Save to Wiki all work.
- **Training handshake**: when it opens (today only from Lab Monitor → Retry), X and Cancel close it and Start launches the job.
- **Teach modal**: X closes it, just like Cancel.

### Beat 2: What AutoReiv does now (qa `f895c0cc`, reproduced)

Every result below was the same on desktop and on phone:

| Action | Expected | Actual |
|--------|----------|--------|
| Click header `#workbenchToggleBtn` | Pane opens | Pane stays hidden |
| Click a message's Workbench button | Pane opens with the reply | Pane stays hidden; the title is still the template default "Workbench Canvas" |
| Click "View Full Report" on an `artifact://` card | Artifact opens | Nothing opens (no pane, no artifact modal) |
| Artifact badge on the Workbench button, with 1 artifact card in chat | Shows "1" | Hidden, empty |
| Teach → X | Modal closes | Stays open |
| Teach → Cancel | Modal closes | Closes (works) |
| Lab Monitor → Retry | Training modal opens | Opens (works), with `data-agent-id` pre-filled |
| Training modal X / Cancel | Modal closes | **Stays open**. The user is stuck behind a full-screen modal until they reload |
| Training modal Start | `POST /api/agent_training_factory/jobs` | **0 requests** |
| Training modal "Advanced requirements" toggle | Expands | Works (it looks itself up with `$()`) |

Root causes (file:line on qa `f895c0cc`):

1. **Workbench is never given its elements.** `src/web/static/modules/studios/chat.js` L640 calls `initWorkbench(state, { showToastFn: showToast })`. But `chat/workbench.js` L65-87 `initWorkbench(elements, {...})` destructures 13 element refs (`chatWorkbenchPane`, title, meta, preview, raw, tabs, toggle, close, mobile back, copy, save-to-wiki, badge, `messagesContainer`) from its first argument. `state` has none of them. So:
   - `openWorkbench` (L114-151) can't un-hide the pane.
   - The listeners (L161-197) never bind.
   - `renderMarkdownFn`, `getActiveSessionId`, `copyToClipboardFn` and `exportMessageToWikiFn` are not passed either.
   - All 13 IDs exist exactly once in `src/web/templates/index.html` (pane L594, toggle L253).
2. **Badge refresh gets the wrong type.** `chat.js` L647-648 calls `refreshWorkbenchArtifactCountDirect(state.activeSessionId)` with a string. `workbench.js` L40 expects `{ activeSessionId, messagesContainer, workbenchArtifactBadge, workbenchToggleBtn }`. So the badge never shows.
3. **"View Full Report" passes an id where an object is expected.** `chat/render.js` L86 calls `onOpenArtifact(artId)` with a string. `chat.js` L876 wires `onOpenArtifact: openWorkbench`, and `openWorkbench` expects `{ title, meta, content }`.
   - Nothing fetches `GET /api/artifacts/{id}`.
   - Once the pane is rewired, this would open an **empty** Workbench.
   - The existing `openArtifactModal` (render.js L101+, which does fetch) is skipped whenever `onOpenArtifact` is set.
4. **Toast arguments are reversed.** `workbench.js` L183 and L194 call `showToastFn('success', 'Artifact copied...')`. The signature is `showToast(message, type)`, so the toast would read "success".
5. **Training modal gets the wrong argument shape.** `chat.js` L666-670 calls `setupTrainModal(state, { trainAgentTargetSelect, showToastFn, onJobSubmitted })`. `chat/train_modal.js` L49-67 expects `(elements, { state, promptInput, messagesContainer, showToastFn, maybeAutoscrollMessagesFn })`. So Close, Cancel and Start (L92-227) never bind. `onJobSubmitted` isn't a supported option at all.
6. **The chat "Train agent" toggle has no handler on purpose.** `index.html` L453-454 says: "CARD-306: Train Agent checkbox removed from Chat Options - Training Factory owns training (keep-one). Modal retained for Factory." `#trainAgentToggle` is now a hidden, `aria-hidden` checkbox, and `#trainAgentBadge` (L572) is only ever hidden. This is a product removal, not lost wiring. What's left is dead markup.
7. **Dead lookups.** `trainAgentTargetSelect`, `trainAgentNameInput` and `trainAgentNameGroup` are not in the template (the repro confirmed they are missing). Yet `chat.js` L319 and L479-480, `train_modal.js` L13-31/L101-107 and `forge/lab_monitor.js` L135-147 still reference them. Retry already carries the agent in `modal.dataset.agentId` (L126-128), and Start already falls back to it (train_modal.js L105).
8. **Teach X was never re-bound.** `setupTeachAgentModal` (`train_modal.js` L234) binds Cancel (L273) and Submit (L285), but never `#closeTeachAgentModalBtn` (index.html L5300).

### End-to-end check: does each feature still earn its place?

| Feature | Backend | Durable state | Reachable in UI? | Verdict |
|---------|---------|---------------|------------------|---------|
| Workbench | Doesn't need one for message text. Artifacts: `GET /api/artifacts/{id}` (`routers/artifacts.py` L67) returns 200, or 404 for unknown ids (probed); `GET /api/sessions/{id}/artifacts` (L43) returns 200. Save to Wiki reuses `wiki/export.js` `exportMessageToWiki`, which already works from the message row | Artifacts saved by tools (`application/skills/worker_tools.py` L186-203, `state_store.save_artifact`); the Workbench itself keeps no state | Yes: a header button on every chat, a button on every assistant message, and artifact cards | **Rewire.** Live product, and all the pieces exist |
| Teach modal | `POST /api/skills/distill` (`routers/skills.py` L276) returned **200** in the probe with a SKILL.md proposal; `/api/skills/adopt` exists | The proposal is saved as a session message (`message_id` returned, `adoption_state: pending`); adopt writes the skill | Yes: a Teach button on every assistant message | **Rewire X** (one listener) |
| Chat "Train agent" toggle | n/a | n/a | No: hidden by CARD-306 | **Remove** the dead markup and lookups |
| Training handshake modal | `POST/GET /api/agent_training_factory/jobs` (`routers/agent_training_factory.py` L237/L375/L419): create returned 200 with `job_id`, list and get returned 200 | Jobs are stored in the DB through `FactoryPacketRepository` | **Barely.** Its only opener is Lab Monitor → Retry (`lab_monitor.js` L683-703). Lab Monitor opens only from an `open-lab-drawer-btn` in chat (render.js L780), which appears only after a job was started. Forge's Lab Monitor button (L563-574) goes to Factory Studio, and Factory Studio has no job list or "start training" at all. `POST /api/agents/{id}/gaps/{gap}/train` (`routers/gaps.py` L117) has no UI caller | **Rewire the three buttons here** (without this, Retry traps you behind a modal you can't close). Whether the autonomous training loop needs a real front door or should be retired is a bigger product question, filed as **CARD-495** |

### Beat 3: What will change

1. **Workbench:**
   - Add `collectWorkbenchElements()` in `chat/workbench.js`, which looks up the 13 IDs.
   - `chat.js` then calls `initWorkbench(collectWorkbenchElements(), { renderMarkdownFn, getActiveSessionId, copyToClipboardFn: copyToClipboard, exportMessageToWikiFn: callbacks.exportMessageToWiki, showToastFn })`.
   - Fix the badge call (`workbench.refreshArtifactCount()`, bound inside the module) and the toast argument order.
2. **Artifact cards:** add `openArtifactById(id)` in `workbench.js`. It fetches `/api/artifacts/{id}` and opens the Workbench with the title, "Session artifact · id" and the content. If the artifact is missing, it shows a toast "Artifact not found" and doesn't open an empty pane. `chat.js` passes it as `onOpenArtifact`. `render.js` is unchanged.
3. **Training modal:** add `collectTrainModalElements()` in `train_modal.js`. `chat.js` calls `setupTrainModal(collectTrainModalElements(), { state, promptInput, messagesContainer, showToastFn, maybeAutoscrollMessagesFn })`.
4. **Remove dead training bits:** the `trainAgentToggle` hidden input, the `trainAgentBadge` span, the `trainAgentTargetSelect` lookup and `populateTrainAgentTargetOptions` call in `chat.js`, and the unsupported `onJobSubmitted`. `train_modal.js` and `lab_monitor.js` keep tolerating a missing select, so existing unit tests that pass one explicitly still work.
5. **Teach:** bind `#closeTeachAgentModalBtn` to `closeTeachAgentModal`.
6. **Guard:** a jsdom test that builds the real template and runs each `collect*Elements()` helper, asserting every key resolves to an element. A source contract fails if `chat.js` passes `state` as the first argument to `initWorkbench` or `setupTrainModal`.

`chat.js` is at 1,012 lines (cap 1,045). The lookups move into the modules, so the net change is about +/-5 lines.

### Beat 4: What dies

- Setup helpers called with the wrong argument shape.
- A Workbench that can't open, and an artifact badge that never counts.
- A training modal that traps you.
- The hidden CARD-306 leftovers (`#trainAgentToggle`, `#trainAgentBadge`, the lookups for the missing select and name input).

## 2. Acceptance criteria (EARS)

- **[REQ-472-001]** WHEN Jacob clicks `#workbenchToggleBtn` while the pane is hidden, THE SYSTEM SHALL show `#chatWorkbenchPane` with the last opened artifact, or the "Workbench is empty" note. WHEN he clicks it again, or clicks Close or Mobile back, THE SYSTEM SHALL hide the pane.
- **[REQ-472-002]** WHEN Jacob clicks a message's Workbench button, THE SYSTEM SHALL show the pane with that message's text rendered in Preview and verbatim in Raw, titled "<agent> Output".
- **[REQ-472-003]** WHEN Jacob clicks "View Full Report" on an artifact card, THE SYSTEM SHALL fetch `GET /api/artifacts/{id}` and show that artifact's title and content in the pane. IF the fetch fails or returns 404, THEN THE SYSTEM SHALL show the error toast "Artifact not found" and SHALL NOT open an empty pane.
- **[REQ-472-004]** WHILE the open chat contains N distinct artifact cards (N > 0), THE SYSTEM SHALL show N on `#workbenchArtifactBadge`. WHEN N is 0, THE SYSTEM SHALL hide the badge.
- **[REQ-472-005]** WHEN Jacob clicks Preview or Raw, THE SYSTEM SHALL switch the visible tab. WHEN he clicks Copy, THE SYSTEM SHALL copy the raw text and show the success toast "Artifact copied to clipboard". WHEN he clicks Save to Wiki, THE SYSTEM SHALL call the existing wiki export with the raw text.
- **[REQ-472-006]** WHILE `#trainAgentHandshakeModal` is open, WHEN Jacob clicks X or Cancel, THE SYSTEM SHALL hide the modal and clear `data-agent-id` and the form fields.
- **[REQ-472-007]** WHILE `#trainAgentHandshakeModal` is open from Retry, WHEN Jacob clicks Start, THE SYSTEM SHALL send exactly one `POST /api/agent_training_factory/jobs` with the `target_agent_id` from Retry, close the modal, and on success show "Training Job <id> initiated!" and open Lab Monitor on that job. IF the POST fails, THEN THE SYSTEM SHALL show "Failed to start training loop: <reason>" and re-enable Start.
- **[REQ-472-008]** THE SYSTEM SHALL NOT render `#trainAgentToggle` or `#trainAgentBadge` in Chat (CARD-306 keep-one: training lives in the Factory).
- **[REQ-472-009]** WHEN Jacob clicks `#closeTeachAgentModalBtn`, THE SYSTEM SHALL close the Teach modal and clear its guidance, the same as Cancel, and SHALL NOT call `/api/skills/distill`.
- **[REQ-472-010]** THE SYSTEM SHALL resolve every element that `initWorkbench` and `setupTrainModal` destructure to a real template element at startup (enforced by the guard test).

## 3. Decisions (recommendations in bold)

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | Workbench: rewire or remove? | (a) rewire; (b) remove the pane and buttons | **(a) Rewire.** It's visible on every chat and every assistant message, and the artifact backend works. Removing it would also mean removing the message-row button, the header button and the artifact cards |
| D2 | What "View Full Report" opens | (a) the Workbench, after fetching `/api/artifacts/{id}`; (b) the older artifact modal (`openArtifactModal`, with pin/promote/delete); (c) leave it passing an id (it would open an empty Workbench) | **(a).** CARD-306 made the Workbench the single artifact viewer, and its empty-state text promises exactly this. The pin/promote/delete modal stays reachable from the session artifact shelf. Keep one viewer per click |
| D3 | Where the element lookups live | (a) `collect*Elements()` in each module; (b) inline `$()` calls in `chat.js` | **(a).** It keeps `chat.js` under its cap and gives the guard test one function to check |
| D4 | Chat "Train agent" toggle: rewire or remove? | (a) restore the pre-split `change` handler; (b) remove the hidden input and badge | **(b) Remove.** CARD-306 deliberately moved training to the Factory, so rewiring would bring back a second entry point Jacob already cut. Update `chat_train_workbench_keep_one_306.test.js` to assert the elements are absent instead of hidden |
| D5 | Training modal buttons: rewire or remove? | (a) rewire Close/Cancel/Start now; (b) delete the modal and the Retry button | **(a) Rewire.** It's a few lines, it removes a real trap (a full-screen modal with no way out), and the jobs API works and saves jobs. Whether the autonomous loop should get a proper front door or be retired is filed as **CARD-495** |
| D6 | Missing `trainAgentTargetSelect` / name input | (a) add them to the modal; (b) drop the `chat.js` lookups and rely on `modal.dataset.agentId`, keeping the module code tolerant | **(b).** Retry already knows the agent. Adding a picker is CARD-495 territory (starting new jobs) |
| D7 | Teach X | (a) bind it to close; (b) remove the X | **(a).** Every other modal has an X |
| D8 | Guard against this bug class | (a) jsdom `collect*Elements()` resolve test plus a source contract on the `chat.js` call shapes; (b) behavioural tests only | **(a) plus the behavioural tests.** CARD-397 broke three helpers the same way, so a cheap structural guard is worth it |
| D9 | pytest | (a) none (no backend change); (b) add an integration test for `/api/skills/distill` and jobs create | **(a) for this card.** Both endpoints answered 200 in the repro and already have server-side coverage |

## 4. Failing-tests-first plan

Commit these red first (confirm each fails on qa), then fix.

**Vitest (new `tests/unit/frontend/chat_workbench_train_teach_wiring_472.test.js`, jsdom plus the real `index.html` body)**

1. `collectWorkbenchElements()` returns all 13 keys as elements (REQ-010). Red: the helper doesn't exist.
2. `initWorkbench(collectWorkbenchElements(), opts)`:
   - toggle click shows the pane, and a second click hides it;
   - Close and Mobile back hide it;
   - Raw/Preview switch the visible tab (REQ-001, REQ-005).
3. `openWorkbench({title, content})` sets the title and renders the preview through `renderMarkdownFn`; Raw holds the verbatim text (REQ-002).
4. `openArtifactById('art_1')` with a fake fetch:
   - on 200 it shows the artifact title and content;
   - on 404 it shows an error toast and the pane stays hidden (REQ-003).
5. With 2 distinct `.open-artifact-btn` in `messagesContainer` (plus one duplicate), refresh shows badge "2"; with 0 it hides the badge (REQ-004).
6. Copy calls `copyToClipboardFn(raw)` and `showToastFn('Artifact copied to clipboard', 'success')`, in that argument order. Save to Wiki calls `exportMessageToWikiFn(raw)` (REQ-005).
7. `setupTrainModal(collectTrainModalElements(), { state, ... })`, after `populateTrainModalForRetry({ job: { target_agent_id: 'demo' } })` and un-hiding the modal:
   - X hides it and clears `data-agent-id`; the same for Cancel (REQ-006);
   - Start sends exactly one POST with `target_agent_id: 'demo'`, closes the modal and shows the toast "Training Job fjob_x initiated!";
   - a failing POST shows the error toast and re-enables Start (REQ-007).
8. The template has no `#trainAgentToggle` / `#trainAgentBadge` (REQ-008). Update the CARD-306 test accordingly.
9. `setupTeachAgentModal` plus `openTeachAgentModal({ messageId })`, then X, hides the modal and clears guidance, with no fetch (REQ-009).
10. Source contract: `chat.js` has no `initWorkbench(state` or `setupTrainModal(state` (REQ-010).

**Playwright smoke (`tests/e2e/smoke.spec.js`, inside the existing desktop + phone viewport loop, stubbed stream like TC-9)**

- **TC-33** (desktop, phone): the stubbed reply contains `[Report](artifact://art_tc33)`, and `/api/artifacts/art_tc33` is routed to a fixture.
  - The badge shows 1.
  - The header toggle opens the pane.
  - The message Workbench button shows the reply.
  - "View Full Report" shows the fixture title.
  - Close hides the pane. On phone, the pane is full screen and Mobile back hides it.
- **TC-34** (desktop, phone): Teach from a reply opens the modal; X closes it; no `/api/skills/distill` request is sent.
- **TC-35** (desktop, phone):
  - Route `/api/agent_training_factory/jobs/fjob_tc35` to a fixture and call `window.openLabMonitorDrawer('fjob_tc35')`. Retry opens the training modal. X closes it.
  - Retry again, then Cancel closes it.
  - Retry again, then Start sends one routed POST, the modal closes, and the success toast shows.
- **TC-36** (desktop): Chat Options has no Train agent control and no `#trainAgentToggle` in the DOM.

**pytest:** none (D9). The full unit and integration suites still run as regression.

## 5. Build order (after **build**)

1. Card to In Progress (docs commit).
2. Failing Vitest plus smoke TC-33..36 (commit; confirm red).
3. `workbench.js`: `collectWorkbenchElements`, `openArtifactById`, a bound badge refresh, and the toast argument order.
4. `train_modal.js`: `collectTrainModalElements` and the Teach X listener.
5. `chat.js`: the correct call shapes; drop the dead train lookups and `onJobSubmitted`. Keep it at or under 1,045 lines.
6. `index.html`: remove `#trainAgentToggle` and `#trainAgentBadge`. Update the CARD-306 test.
7. CHANGELOG `[Unreleased] ### Fixed`, then In Review with a build note.

## 6. Runbook (Jarvis, after build; scratch server or `:8000`)

1. **Workbench, header:** open a chat and click **Workbench** in the header. The side panel opens with "Workbench is empty". Click it again and it closes.
2. **Workbench, message:** send "hi". On the reply, click **Workbench**. The panel shows the reply. Click **Raw**: plain text. Click **Preview**: formatted. Click **Copy**: the toast says "Artifact copied to clipboard", and pasting gives the reply. Click **Save to Wiki**: the usual wiki export happens. Close with X.
3. **Artifact card:** in a chat where a tool saved an artifact (a "View Full Report" card), the Workbench button shows a count. Click **View Full Report**: the panel shows that report's title and text.
4. **Phone** (192.168.1.99:8000): repeat 1-2. The panel covers the screen, and the back arrow returns to chat.
5. **Teach:** on a reply, click **Teach**, then the **X**. The modal closes and nothing is submitted. Open it again, and **Cancel** also closes it.
6. **Training Retry:** open Lab Monitor on an existing job (from a "View in Lab Monitor" link) and click **Retry**. Then:
   - **X** closes the modal.
   - **Retry** again, then **Cancel** closes it.
   - **Retry** again, then **Launch Autonomous Loop**: the toast shows "Training Job ... initiated!" and Lab Monitor switches to the new job.
7. **Chat Options** shows no Train agent switch.

## 7. Repro script and evidence

- `scratch/c472_ui.cjs` (Playwright, Node) against `scratch/c472_run.ps1 serve`:
  - `scratch/c472_fake_gateway.py` replies "Report ready. See [C472 demo report](artifact://art_c472_demo) now.".
  - The script seeds a job through `POST /api/agent_training_factory/jobs`, opens Lab Monitor with `window.openLabMonitorDrawer(jobId)`, and probes `/api/skills/distill`, `/api/sessions/{id}/artifacts` and `/api/artifacts/{missing}` directly.
- Output: `scratch/c472_ui_out.txt`; screenshots `scratch/c472_desktop.png` and `scratch/c472_phone.png`.
- The only console noise was one unrelated 404 resource load on page start (not investigated here).

## 8. Out of scope / follow-ups

- **CARD-495**: the autonomous training loop has no front door. There's no way to start a new job or list jobs, and Lab Monitor opens only from a chat link that appears after a job starts. Factory Studio (declared the owner by CARD-306) has neither. Rehome it or retire it.
- `render.js` is 836 lines, already over the 800 target. This card doesn't touch it.
