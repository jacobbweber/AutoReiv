---
id: CARD-720
title: "Comprehensive UI Audit and Button Functionality Fixes"
type: bug
status: In Progress
priority: P1
milestone: M31
needs_decision: none
proof:
  journeys: [card-720-comprehensive-ui-audit-and-button-functionality]
  checks: [tests/unit/test_card720_ui_audit_contracts.py]
branch: feat/card-720-comprehensive-ui-audit-and-button-functionality
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-18
---

# CARD-720 Comprehensive UI Audit and Button Functionality Fixes

## Problem
A full audit of every studio, modal, drawer, and interactive control across AutoReiv surfaced several broken or silent UI interactions, dead listeners, z-index stacking bugs, and stale agent/studio references:
1. **Chat Reply `.copy-msg-btn` silent & misses first click after sending (`docs/findings.md` M22)**:
   - Clicking `Copy` (`.copy-msg-btn`) on an assistant reply gives zero visual feedback (no `"Copied!"` label swap and no toast, unlike `#workbenchCopyBtn`, `#copyThreadBtn`, and `#chatDebugCopyBtn`).
   - Right after sending a message, `#promptInput` remains focused with `engaged === true` and stays 8 lines tall (`~160px`) even though it is empty. Clicking `.copy-msg-btn` or another reply button blurs `#promptInput`, shrinking the composer by ~140px mid-click and shifting the reply buttons away from the cursor.
   - In non-secure HTTP contexts (`clipboard.js`), `fallbackCopyTextToClipboard` calls `textArea.focus()` without `{ preventScroll: true }` and without restoring prior focus.
   - Reply action buttons (`.msg-teach-agent-btn`, `.workbench-msg-btn`, `.copy-msg-btn`, `.wiki-msg-btn`) lack `type="button"` and `title`/`aria-label`.
2. **Triple-bound `#toggleSidebarBtn`**:
   - `#toggleSidebarBtn` has three competing click listeners in `app.js:90-96` (toggles legacy `#sidebar`), `chat/scroll.js:117-128` (toggles `#chatSessionsDrawer` when `!radical-desktop-demo`), and `agent-desktop.js:561-582` (capture-phase listener). Because `app.js` binds directly on `#toggleSidebarBtn` before `agent-desktop.js`, both `#sidebar` and `#chatSessionsDrawer` toggle on click.
3. **Unwired Self-Verify / Reflexion SSE badge & reversed toast args in `openArtifactModal`**:
   - `.reflexion-status-badge` in `stream_bubble.js` and `renderReflexionBadge` in `job_chrome.js` are never wired in `bindStreamBubbleElements` / `chat.js`.
   - `openArtifactModal` in `chat/render.js` passes `('error', 'Failed...')` instead of `('Failed...', 'error')` to `showToastFn`.
   - `#teachAgentModal` clobbers the `<i data-lucide="sparkles">` icon and `"Auto-Diagnose & Draft"` label on `#submitTeachAgentBtn` after first run, and lacks backdrop click and `data-modal-close` dismissal.
4. **Desktop modal z-index & window preset tab alignment**:
   - `enhanceHitlDialogs` in `agent_desktop/chrome.js` only elevates `chatToolsModal` and `routineModal` (`z-index: 11000`), leaving 8 other modals (`forgeNewAgentModal`, `teachAgentModal`, `manageTonesModal`, `deleteAgentModal`, `agentBrainDrawer`, `wikiNewNoteModal`, `wikiMindMapModal`, `artifactModal`) at `z-index: 50` underneath active desktop windows (`z-index: 43..9002`) and the dock (`z-index: 10000`).
   - `PRIORITY_TABS` in `agent_desktop/presets.js` still lists retired `'skill-studio'` and `'tools-studio'` instead of `'capabilities'`, and `onTalkToForge` in `app.js` switches to retired agent `'forge'` instead of `'autoreiv'`.
5. **Wiki, Projects, Routines, Agents, Capabilities, Education, Metrics & Settings bugs**:
   - **Wiki**: Clicking `#wikiOverviewDeleteFolderBtn` ("Delete Folder") in the Folder Overview pane passes `onNoteSelect` as `onReloadVault`, calling `loadWikiNote(undefined)` -> `GET /api/wiki/note?path=undefined` (404). `#fmCopyRawBtn` ("Copy YAML") gives no toast feedback.
   - **Projects**: `#projectsCopyPathBtn` ("Copy relative path") only fires its `"Copied: ..."` toast inside the `catch` block instead of the `try` block! Mobile `closeReadingPane` returns early before clearing stale file content.
   - **Routines & Agent Studio**: `.toggle-routine-btn` and `.trigger-routine-btn` in `routines.js` and `.forge-routine-run-btn` in `forge/config.js` do not check `res.ok` before showing success UI; `.forge-routine-edit-btn` clicks dead `#tab-routines` instead of `callbacks.switchTab('routines')`.
   - **Agent Studio**: `updateAvatarPreview` in `forge/config.js` injects `<i data-lucide>` inside the already-rendered `<svg id="forgeAvatarIcon">`, creating nested invalid SVG; `#forgeMemoryEnabled` checkbox has no `change` listener to toggle `#forgeMemoryConfigContainer`.
   - **Capabilities Studio**: MCP server `delete`, `toggle`, and `test-saved` actions lack toast feedback and `try/catch` guards; `#capabilitiesCreateNameInput` lacks `Enter`/`Escape` key handling.
   - **Education Studio**: `.edu-op-due-item` buttons in `#educationOperatorDueList` have no click handler, `#educationOperatorDuePanel` has no Hide button (`#educationOperatorDueHideBtn`), `education.js` does not refresh active context on tab switch, and `toast(..., 'warn')` uses an unstyled type (`'warn'` vs `'warning'`).
   - **Observability (Metrics) Studio**: Live log polling in `observability.js:390` checks `$query('.tab-view:not(.hidden)')`, which in desktop mode always matches `#view-chat` first, preventing live log polling in Metrics; `loadObservability()` omits `populateSessionSelectEl` and `loadFrictionRecommendations()`; `journey_canvas.js` and `observability_audit.js` omit `safeCreateIcons()` after button `innerHTML` updates.
   - **Settings Studio**: `setupAllowedOrigins` attaches duplicate click listeners on `#allowedOriginsSaveBtn` every time Settings loads; `loadUpdateHistory` in `settings/updates.js` interpolates unescaped strings into `innerHTML`; `settings_local_model_probe.js` omits `safeCreateIcons()`; `settings_core.html` empty state references `"Refresh From Providers"` instead of `"Refresh Models"`.

## Cause
- `chat/render.js`: `.copy-msg-btn` handler only ran `await copyToClipboard(content)` with no button text swap or `showToastFn` call.
- `chat/composer.js`: `setupComposerSizing` kept `engaged = true` when `setComposerText(promptInput, '')` cleared `#promptInput` on send, leaving the empty focused textarea at 8 lines until `blur`.
- `app.js`, `chat/scroll.js`, `agent-desktop.js`: `#toggleSidebarBtn` was bound in three separate modules across mobile/desktop migrations.
- `agent_desktop/chrome.js` & `presets.js`: `enhanceHitlDialogs` and `PRIORITY_TABS` were not updated when new modals were added and `skill-studio`/`tools-studio` consolidated into `capabilities`.
- `wiki/folder.js` & `wiki/tree.js`: `renderFolderOverview` received `onNoteSelect` but not `onReloadVault`, passing `onNoteSelect` into `deleteWikiFolder({ onReloadVault })`.
- `projects.js`: `toast(\`Copied: \${state.selectedFile}\`)` was accidentally placed only inside `catch` instead of `try`.
- `forge/config.js`: `lucide.createIcons()` replaces `<i id="forgeAvatarIcon">` with `<svg id="forgeAvatarIcon">`, so setting its `innerHTML` nested an `<i>`/`<svg>` inside `<svg>`.
- `education_operator.js`: `.edu-op-due-item` rows were rendered as `<button>` elements without a delegated click handler on `#educationOperatorDueList`.
- `observability.js`: `$query('.tab-view:not(.hidden)')` returns the first non-hidden `.tab-view` in DOM order (`#view-chat`), not `#view-observability`.

## Change
1. **Chat & Modals (`chat/render.js`, `chat/composer.js`, `chat/scroll.js`, `chat/stream_bubble.js`, `chat/teach_modal.js`, `chat.js`, `utils/clipboard.js`, `app.js`, `modals.html`)**:
   - Update `.copy-msg-btn` in `chat/render.js` to check the return value of `copyToClipboard`, swap button text to `"Copied!"` for 1.5s, and call `showToastFn('Copied to clipboard', 'success')`; add `type="button"` and `title`/`aria-label` to `.msg-teach-agent-btn`, `.workbench-msg-btn`, `.copy-msg-btn`, and `.wiki-msg-btn`; fix reversed `showToastFn` arguments in `openArtifactModal`.
   - Reset `engaged = false` in `setupComposerSizing` (`chat/composer.js`) when `input` fires with an empty `promptInput.value` so sending a message immediately collapses the empty composer to 1 line.
   - Preserve focus and use `focus({ preventScroll: true })` in `clipboard.js`.
   - Consolidate `#toggleSidebarBtn` click handling in `chat/scroll.js` (removing duplicates in `app.js` and `agent-desktop.js`).
   - Wire `reflexionBadge` in `stream_bubble.js` and `chat.js`; preserve icon/label and add backdrop/`data-modal-close` dismissal on `#teachAgentModal`; update `onTalkToForge` in `app.js` and default routine agent in `routines.js` to `'autoreiv'`.
2. **Desktop Shell (`agent_desktop/chrome.js`, `agent_desktop/presets.js`)**:
   - Elevate all 10 modal overlays in `enhanceHitlDialogs()` with `.desktop-dialog-host`.
   - Replace `'skill-studio'` and `'tools-studio'` in `PRIORITY_TABS` with `'capabilities'`.
3. **Wiki, Projects, Routines, Agents, Capabilities, Education, Metrics & Settings**:
   - Pass `onReloadVault` through `selectWikiFolder` -> `renderFolderOverview` -> `deleteWikiFolder`; add toast feedback to `#fmCopyRawBtn` in `wiki/note.js`.
   - Move `#projectsCopyPathBtn` success toast into `try` block in `projects.js`; clear mobile reading pane content in `projects_journey_runs.js`.
   - Check `res.ok` and show toasts on routine toggle/trigger in `routines.js` and `forge/config.js`; use `callbacks.switchTab('routines')` on `.forge-routine-edit-btn`.
   - Fix `updateAvatarPreview` in `forge/config.js` to re-render `<i id="forgeAvatarIcon">` inside `#forgeAvatarPreview`; wire `#forgeMemoryEnabled` checkbox in `forge.js`.
   - Add `try/catch` + toasts for MCP `delete`, `toggle`, and `test-saved` and `Enter`/`Escape` key handlers on `#capabilitiesCreateNameInput` in `capabilities_studio.js`.
   - Wire `.edu-op-due-item` click delegation and `#educationOperatorDueHideBtn` in `education_operator.js` + `prompts_education_skill_studio.html`; refresh active context in `education.js`; support `'warn'` alias in `toast.js`; use `setComposerText` in `study_entry.js` and `study_entry_panels.js`.
   - Fix live log polling visibility check (`$('view-observability')`), session select population, friction loading, and `safeCreateIcons()` calls in `observability.js`, `observability_audit.js`, and `journey_canvas.js`.
   - Guard `#allowedOriginsSaveBtn` with `dataset.wired = '1'` in `settings_allowed_origins.js`; escape HTML in `settings/updates.js`; call `safeCreateIcons()` in `settings_local_model_probe.js`; align `"Refresh Models"` text in `settings_core.html`.

## What dies
- Duplicate `#toggleSidebarBtn` click listeners in `src/web/static/app.js` and `src/web/static/modules/ui/agent-desktop.js` (single canonical listener in `src/web/static/modules/studios/chat/scroll.js`).
- Retired `'skill-studio'` and `'tools-studio'` entries in `PRIORITY_TABS` in `src/web/static/modules/ui/agent_desktop/presets.js`.
- Stale M22 finding in `docs/findings.md` (`first click on a reply button right after sending (focused composer) can miss`).

## Proof
- Journey `card-720-comprehensive-ui-audit-and-button-functionality`:
  1. In Chat Studio, send a prompt and immediately click `.copy-msg-btn` on the assistant reply; assert the composer is already 1 line tall after send, the first click succeeds, `.copy-msg-btn` shows `"Copied!"`, and a toast appears.
  2. Click `#toggleSidebarBtn` to open and close `#chatSessionsDrawer` cleanly; open `#chatOptionsBtn` and `#chatToolsBtn` (`#chatToolsModal` elevated with `.desktop-dialog-host`).
  3. Open Agents Studio, test `#forgeIconPicker` avatar preview (`#forgeAvatarPreview` has a single `<svg>`, not nested `<svg><svg>`), toggle `#forgeMemoryEnabled` and verify `#forgeMemoryConfigContainer` visibility, and open/close `#forgeNewAgentModal`.
  4. Open Capabilities Studio, verify `#capabilitiesCreateSkillBtn` + Escape closes `#capabilitiesCreateBar`, and verify MCP panel toggle.
  5. Open Wiki Studio, select a folder to open `#wikiFolderOverviewPane` and verify `#wikiOverviewNewNoteBtn`, then select a note and click `#fmCopyRawBtn` ("Copy YAML") and verify toast feedback.
  6. Open Education Studio, open the Due review panel (`#educationOperatorReviewBtn`), verify `#educationOperatorDueHideBtn` hides `#educationOperatorDuePanel`.
  7. Open Settings Studio, verify `"Refresh Models"` naming and save Allowed Origins without duplicate handlers.
- Checks: `tests/unit/test_card720_ui_audit_contracts.py` (runs Vitest suite `tests/unit/frontend/card_720_ui_audit_fixes.test.js` + structural guard checks, including negative assertions against nested `<svg>` in avatar preview, duplicate `#toggleSidebarBtn` bindings, retired tabs in `PRIORITY_TABS`, and reversed `showToastFn` args).

## Plan and decisions
- Keep `TOOLSMITH_AGENT_ID = 'toolsmith'` in `tools_studio_authoring.js` and `"Opening Tools Studio"` in `teach_modal.js` / `forge/tools.js` and `"Pair with Developer"` in `wiki_projects.html` because existing unit tests (`card_422`, `card_496`, `card_520`, `developer_projects_integration`) explicitly assert those strings while `resolveAuthoringChatAgentId` maps `toolsmith`/`developer` to `autoreiv` at runtime.
- Reset `engaged = false` in `setupComposerSizing` whenever `input` fires with an empty `promptInput.value` so programmatic clearing on send (`setComposerText(promptInput, '')`) immediately shrinks the empty composer back to 1 line instead of waiting for `blur`.

## Findings
- (fixed) Chat `.copy-msg-btn` gave no toast or button text feedback and could miss the first click after sending because the empty focused composer stayed 8 lines tall until `blur` (`docs/findings.md` M22 resolved).
- (fixed) `#toggleSidebarBtn` was triple-bound across `app.js`, `chat/scroll.js`, and `agent-desktop.js`.
- (fixed) `openArtifactModal` in `chat/render.js` passed reversed `(type, message)` arguments to `showToastFn`.
- (fixed) `enhanceHitlDialogs` in `agent_desktop/chrome.js` left 8 modals at `z-index: 50` below desktop windows and the dock; `PRIORITY_TABS` in `presets.js` referenced retired `'skill-studio'` and `'tools-studio'`.
- (fixed) Wiki `#wikiOverviewDeleteFolderBtn` passed `onNoteSelect` as `onReloadVault`, triggering `GET /api/wiki/note?path=undefined` (404).
- (fixed) Projects `#projectsCopyPathBtn` only called `toast('Copied: ...')` inside its `catch` block.
- (fixed) Agent Studio `updateAvatarPreview` nested an `<svg>` inside `<svg id="forgeAvatarIcon">`, and `#forgeMemoryEnabled` had no `change` handler.
- (fixed) Education Studio `#educationOperatorDuePanel` had no Hide button and `.edu-op-due-item` rows had no click listener; `toast.js` did not map `'warn'` to `'warning'`.
- (fixed) Observability live log polling checked `$query('.tab-view:not(.hidden)')` (always matching `#view-chat` in desktop mode) instead of `$('view-observability')`.
- (fixed) Settings `#allowedOriginsSaveBtn` bound duplicate click listeners on each visit to Settings.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `/tmp/autoreiv-qa/card-720/...`

## Release note
Fixed UI button wiring, feedback toasts, modal z-index elevation, composer post-send sizing, Wiki folder deletion reload, Projects copy-path toast, Agent avatar preview and memory toggle, Education due-review panel controls, Observability live log polling, and Settings duplicate listeners across all studios (CARD-720).
