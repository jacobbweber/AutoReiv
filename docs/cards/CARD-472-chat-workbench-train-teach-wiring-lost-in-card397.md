---
id: CARD-472
title: "Workbench, artifact open and Teach modal wiring lost in the CARD-397 split"
status: Done
created: 2026-09-24
updated: 2026-09-25
branch: qa
related:
  - CARD-397
  - CARD-469
  - CARD-138
  - CARD-306
  - CARD-352
  - CARD-358
  - CARD-422
  - CARD-495
  - CARD-496
  - CARD-497
  - CARD-498
  - CARD-499
  - CARD-500
  - CARD-501
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P1
---

# [CARD-472] Workbench, artifact open and Teach modal wiring lost in the CARD-397 split

> **Status**: Done (Jacob said **merge to qa**, 2026-09-25 5:59 PM ET; merged --no-ff into qa).
> **Created**: 2026-09-24
> **Observed during**: CARD-469 planning (diff of pre-split `chat.js` listeners). `git blame` puts the broken call sites on `7b563003` (CARD-397, 2026-09-20 11:06 PM ET).
> **Reproduced**: 2026-09-25 about 3:15-3:35 PM ET on a scratch server (`scripts/smoke_server.py` on 127.0.0.1:8767, throwaway data, fake Ollama on 18434, no real AppData), Playwright on desktop 1280x800 and phone 390x844, qa `f895c0cc`. Scripts: `scratch/c472_ui.cjs`, `scratch/c472_artifact.cjs`, `scratch/c472_404.cjs`.
> **Related**: CARD-397, CARD-469, CARD-138, CARD-306, CARD-352, CARD-358, CARD-422 (Tools Studio developer chat), Factory retirement CARD-495..498
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `P1`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

### Beat 1: What Jacob means

The chat buttons that survive the Factory retirement should work:

- **Workbench.** The header button and each reply's Workbench button open the side panel with that text.
- **Artifacts.** "View Full Report" opens that saved report, and the Workbench button shows how many reports the chat has.
- **Copy.** Copy says "Artifact copied to clipboard".
- **Teach.** The Teach modal's X closes it. When a lesson needs a new tool, the proposal card's button hands it to the Developer instead of the retired Factory.

The training popup is **not** fixed here. It goes away with the Factory (CARD-496).

### Beat 2: What AutoReiv does now (qa `f895c0cc`, reproduced on desktop and phone)

1. **The Workbench never opens.** `chat.js` L640 calls `initWorkbench(state, { showToastFn })`, but `chat/workbench.js` L65-87 destructures 13 page elements from its first argument. So:
   - the pane can't un-hide;
   - the toggle, Close, back, Preview/Raw, Copy and Save to Wiki listeners (L161-197) never bind;
   - the markdown, clipboard, wiki and session helpers are never passed.
   Repro: the header button and the message Workbench button both leave the pane hidden.
2. **The artifact count never shows.** `chat.js` L647-648 passes a session id string to `refreshWorkbenchArtifactCount`, which expects an object (`workbench.js` L40). Repro: 1 artifact card in chat, badge hidden.
3. **"View Full Report" depends on how the card was drawn.**
   - For history cards, `render.js` L524 calls `renderMarkdownFn(bodyEl, content)` with no options. The card listener (L83-89) falls back to the older `openArtifactModal(artId)`, which fetches `/api/artifacts/{id}`. On a 404 it fails silently, because no toast function is passed.
   - For cards drawn at the end of a streamed reply, `chat.js` L875-878 passes `onOpenArtifact: openWorkbench`, which gets an id string instead of `{title, content}`.
   - Repro with a real (routed) artifact: one card opened the older popup, another did nothing. With a missing id: `GET /api/artifacts/art_c472_demo` returned 404 and nothing was shown.
4. **Copy toast arguments are reversed.** `workbench.js` L183 and L194 call `showToastFn('success', 'Artifact copied...')`, but the signature is `showToast(message, type)`.
5. **Teach X has no listener.** `setupTeachAgentModal` (`chat/train_modal.js` L234) binds Cancel (L273) and Submit (L285), but not `#closeTeachAgentModalBtn` (index.html L5300). Repro: X leaves the modal open; Cancel works.
6. **"Send to Factory Studio" on a needs-tool proposal is dead.**
   - `render.js` L306 renders the button, and L376-380 only binds it when `onEscalate` is passed.
   - The live path (`train_modal.js` L301) and the history path (`render.js` L699) never pass it.
   - The Factory it points at is being retired.
7. **Not a bug:** the 404 seen in the first repro was that made-up artifact id, not a page-load request. `scratch/c472_404.cjs` shows no 4xx on page load or when opening chat, on desktop or phone.

**Out of scope (moved to CARD-496):** the training popup's X, Cancel and Start are unbound (`chat.js` L666-670 passes `state` first to `setupTrainModal`). It opens only from Lab Monitor → Retry on an existing job, and Jacob's live DB has 0 Factory jobs. The hidden `#trainAgentToggle`, `#trainAgentBadge` and the missing target-select lookups (`chat.js` L319, L479-481) are also removed there.

### Beat 3: What will change

1. **`chat/workbench.js`:**
   - `collectWorkbenchElements()` looks up the 13 template IDs plus `#messagesContainer`.
   - `initWorkbench` gains `openArtifactById(id)`. It fetches `GET /api/artifacts/{id}` once and opens the Workbench with the artifact's title, "Session artifact · id" and its content. On a non-OK response, a missing artifact or a network error, it shows the error toast **"Artifact not found"** and leaves the pane closed.
   - The toast argument order is fixed.
2. **`chat.js`:**
   - `initWorkbench(collectWorkbenchElements(), { renderMarkdownFn, copyToClipboardFn, showToastFn, exportMessageToWikiFn, getActiveSessionId })`.
   - A single `renderChatMarkdown(el, md)` wrapper injects `onOpenArtifact: openArtifactById` and the badge refresh. Every chat render path uses it (`loadMessages`, the end-of-stream fallback, the appended bubble), so every "View Full Report" goes through `openArtifactById`.
   - The badge refresh calls the bound `workbench.refreshWorkbenchArtifactCount()`.
   - `chat.js` must not grow; the target is fewer lines than 1,012.
3. **New `chat/teach_modal.js`** holds `setupTeachAgentModal`, moved out of `train_modal.js`.
   - X closes the modal like Cancel.
   - One delegated click handler on `#messagesContainer` covers the needs-tool button on both live and history proposal cards. It reads the card's `data-factory-escalation` and summary, then posts to the existing Tools Studio developer-chat endpoint `POST /api/tools_studio/authoring/talk` with `{ intent: 'create', draft: { tool_name, behavior } }`. The behavior text carries the seed intent, the observed slip, the remedy and the objectives.
   - It then opens that Developer chat with the prompt filled in, via chat's `openDeveloperSession`, the same path Tools Studio uses (CARD-422).
   - If that fails, it shows an error toast and opens Tools Studio for the agent.
   - The button label becomes **"Ask Developer to build this tool"**. The `btn-escalate-factory` class and `factory_escalation` field keep their names until CARD-496 (class) and CARD-497 (field) rename them.
4. **`render.js`:** only the button label and title change, with no net growth (the file is already over its cap; see CARD-499).

### Beat 4: What dies

- Workbench setup called with `state`.
- A badge that never counts.
- Two different artifact viewers depending on render path, and silent artifact failures.
- The reversed Copy toast.
- The Teach X that does nothing.
- The escalation button pointing at a retired Factory.

## 2. Acceptance criteria (EARS)

- **[REQ-472-001]** WHEN Jacob clicks `#workbenchToggleBtn` while the pane is hidden, THE SYSTEM SHALL show `#chatWorkbenchPane` with the last opened artifact, or the "Workbench is empty" note. WHEN he clicks it again, or clicks Close or Mobile back, THE SYSTEM SHALL hide the pane.
- **[REQ-472-002]** WHEN Jacob clicks a reply's Workbench button, THE SYSTEM SHALL show the pane with that reply rendered in Preview and verbatim in Raw.
- **[REQ-472-003]** WHEN Jacob clicks "View Full Report" on any artifact card (live or history), THE SYSTEM SHALL fetch `GET /api/artifacts/{id}` once and show that artifact's title and content in the Workbench. IF the response is not OK, has no artifact, or the request fails, THEN THE SYSTEM SHALL show the error toast "Artifact not found" and SHALL NOT open the pane.
- **[REQ-472-004]** WHILE the open chat has N distinct artifacts (N > 0, the larger of the session API count and the DOM cards), THE SYSTEM SHALL show N on `#workbenchArtifactBadge`. WHEN N is 0, THE SYSTEM SHALL hide the badge.
- **[REQ-472-005]** WHEN Jacob clicks Preview or Raw, THE SYSTEM SHALL switch the visible tab. WHEN he clicks Copy, THE SYSTEM SHALL copy the raw text and show the success toast "Artifact copied to clipboard". WHEN he clicks Save to Wiki, THE SYSTEM SHALL call the existing wiki export with the raw text.
- **[REQ-472-006]** WHEN Jacob clicks `#closeTeachAgentModalBtn`, THE SYSTEM SHALL close the Teach modal and clear its guidance, the same as Cancel, and SHALL NOT call `/api/skills/distill`.
- **[REQ-472-007]** WHEN Jacob clicks "Ask Developer to build this tool" on a needs-tool proposal card (live or history), THE SYSTEM SHALL post `POST /api/tools_studio/authoring/talk` with `intent: 'create'` and a draft carrying the suggested tool name, the proposal's seed intent and starter objectives, and the target agent (the slip and remedy are not on the card, see build note), then open that Developer chat with the returned prompt. IF the request fails, THEN THE SYSTEM SHALL show an error toast and open Tools Studio for the target agent.
- **[REQ-472-008]** THE SYSTEM SHALL build the Workbench from `collectWorkbenchElements()` and SHALL NOT pass `state` as its first argument (guard test). Every chat markdown render SHALL use the single artifact opener.

## 3. Decisions (Jacob accepted all, 2026-09-25)

| # | Decision | Choice |
|---|----------|--------|
| D1 | Workbench: rewire or remove | **Rewire** |
| D2 | What "View Full Report" opens | **The Workbench, through one fetch-then-open function on every path**. The older artifact popup is no longer reached from chat clicks |
| D3 | Where element lookups live | **In each module** (`collectWorkbenchElements()`) |
| D4 | Teach | **Keep it** (it's a Skills feature); move it to `chat/teach_modal.js` |
| D5 | Needs-tool escalation | **Developer chat through `/api/tools_studio/authoring/talk` with the proposal attached; Tools Studio as fallback** |
| D6 | Training popup | **Out of scope**; removed in CARD-496 |
| D7 | Guard | **A source guard on `chat.js` call shapes plus the element-resolve test** |
| D8 | pytest | **None** (no backend change) |

## 4. Failing-tests-first plan

**Vitest:** new `tests/unit/frontend/chat_workbench_teach_wiring_472.test.js` (jsdom plus the real `index.html` body)

1. `collectWorkbenchElements()` returns a real element for every key (REQ-008).
2. Toggle shows then hides the pane; Close and Mobile back hide it; Raw/Preview switch tabs (REQ-001, REQ-005).
3. `openWorkbench({title, content})` renders through `renderMarkdownFn`, and Raw holds the verbatim text (REQ-002).
4. `openArtifactById`:
   - on 200 it shows the title and content;
   - on 404, a missing artifact or a rejected fetch, it shows toast `('Artifact not found', 'error')` and the pane stays hidden (REQ-003).
5. The badge shows "2" for two distinct cards plus a duplicate, and is hidden for none (REQ-004).
6. Copy calls `copyToClipboardFn(raw)` and `showToastFn('Artifact copied to clipboard', 'success')`. Save to Wiki calls `exportMessageToWikiFn(raw)` (REQ-005).
7. `setupTeachAgentModal` from `chat/teach_modal.js`: open, then X hides and clears guidance, with no fetch (REQ-006).
8. Escalation:
   - clicking `.btn-escalate-factory` inside a proposal card posts to `/api/tools_studio/authoring/talk` with the tool name and intent, then calls `openDeveloperSessionFn(sessionId, prompt)`;
   - on failure it shows an error toast and calls `openToolsStudio(agentId)` (REQ-007).
9. Guard (REQ-008):
   - `chat.js` has no `initWorkbench(state`;
   - it has no `onOpenArtifact: openWorkbench`;
   - every `renderMarkdownFn:` in `chat.js` is `renderChatMarkdown`.

`skill_distillation_ui.test.js` gets `teach_modal.js` added to its source list; its assertions are unchanged.

**Playwright smoke** (`tests/e2e/smoke.spec.js`, desktop and phone loop; sessions created through `request`, messages and artifacts routed to fixtures)

- **TC-33** (desktop, phone):
  - The history reply has `artifact://art_tc33` (routed to a fixture) and `artifact://art_tc33_missing` (routed 404).
  - The badge shows 2.
  - The header toggle opens the pane.
  - The reply's Workbench button shows the reply.
  - "View Full Report" on art_tc33 shows "TC33 Fixture Report".
  - Close hides the pane (phone: Mobile back).
  - The missing report shows the toast "Artifact not found" and the pane stays hidden.
- **TC-34** (desktop, phone):
  - Teach from the reply, then X, closes the modal with no distill request.
  - The history needs-tool proposal card shows "Ask Developer to build this tool". Clicking it posts one routed `/api/tools_studio/authoring/talk` and opens the Developer chat, with the prompt in the composer.

**pytest:** none. The unit and integration suites still run as regression.

## 5. Build order

1. In Progress (docs).
2. Red tests (Vitest and TC-33/34).
3. `workbench.js`.
4. `teach_modal.js` (move plus X plus escalation), trimming `train_modal.js`.
5. `chat.js` wiring (no growth).
6. `render.js` label only.
7. CHANGELOG, Scavenger Pass, preflight, scratch repro rerun, In Review.

## 6. Runbook (Jarvis, after build)

See the build note for the numbered desktop and phone steps.

## 7. Follow-ups

CARD-495..498 (Factory retirement), CARD-499 (line caps), CARD-500 (Teach distill fields), CARD-501 (smoke for the first click after sending).

## 8. Build note (2026-09-25, In Review)

**Commits** on `feat/card-472-workbench-artifact-teach-wiring` (from qa `36c3cfec`):

| Commit | What |
|--------|------|
| `6f44eef8` | Card In Progress |
| `e1b42fe1` | Red tests: Vitest `chat_workbench_teach_wiring_472.test.js` (10 of 13 red) and smoke TC-33/TC-34 desktop + phone (4 of 4 red) |
| `04e54f50` | Fix: `collectWorkbenchElements()`, `openArtifactById()` (fetch then open, "Artifact not found"), bound badge refresh, toast argument order, `renderChatMarkdown` on every chat render, Teach modal moved to `chat/teach_modal.js` with X wired, "Ask Developer to build this tool" opens a Developer chat (Tools Studio fallback), phone Workbench pane `absolute` (it was `fixed` and slid under the window title bar, so the back arrow could not be tapped) |
| `3ab7d5bf` | CHANGELOG and Scavenger Pass (dead `onEscalate` option and handler in `render.js`; unused `refreshWorkbenchArtifactCountDirect` and `renderSkillProposalCard` imports gone) |
| `c34a85dd` | Red guard: a press in the message list must survive the composer shrink |
| `87e1ab2a` | Fix: `messagesContainer` added to `pressRegions`, so the first click on View Full Report or Workbench right after sending works on desktop |
| `66adb259` | CARD-470 `pressRegions` contract accepts more regions |

**Line counts:** `chat.js` 1,012 -> 1,004 (still over 1,000, so the CARD-499 cap test stays red); `chat/render.js` 836 -> 829 (still over 800). New `chat/teach_modal.js` 143; `train_modal.js` 321 -> 231.

**Tests**

| Suite | Result |
|-------|--------|
| Vitest CARD-472 (14) | 14 pass (10 red before the fix, plus 1 guard red before `87e1ab2a`) |
| Vitest full | 899 pass, 5 fail: the known CARD-456 set only (`chat_monolith_decomposition_397` x2 = chat.js / render.js line caps, `per_agent_model_config`, `system_updates` x2) |
| Smoke (Playwright) | 49 / 49 pass, including TC-33 and TC-34 desktop + phone |
| pytest unit | 2045 pass, 11 skipped, 1 fail: known CARD-454 `test_capability_linter` |
| pytest integration | 107 pass |
| ESLint | baseline 4 errors + 5 warnings, none in chat files |
| ruff | baseline 9 (CARD-454) |

**Scratch repro (fake gateway, scratch data only)**

| Check | Before | After |
|-------|--------|-------|
| Header Workbench button (desktop / phone) | did nothing | opens and closes |
| Reply Workbench button | did nothing | opens with the reply |
| View Full Report (fixture artifact) | no fetch, nothing opened | 1 fetch, Workbench shows "C472 Fixture Report" (desktop + phone) |
| View Full Report (missing artifact) | nothing | "Artifact not found" toast (the 404 in the log is expected) |
| First View Full Report click right after sending (desktop, composer focused) | lost (0 fetches) | works (1 fetch) |
| Badge | wrong / empty | "1" for 1 artifact |
| Teach X / Cancel | X did nothing | both close; 0 distill calls |
| Training popup | broken | still broken, out of scope, removed in CARD-496 |

**REQ-472-007 wording:** the proposal card only carries `data-factory-escalation` (tool name, seed intent, starter objectives, target agent). The slip and remedy are not on the card DOM, so the Developer draft carries what the card has. CARD-500 fixes where the card reads the slip and remedy.

**Live test on Jarvis (http://127.0.0.1:8000 desktop, http://192.168.1.99:8000 phone)** is in the build report.
