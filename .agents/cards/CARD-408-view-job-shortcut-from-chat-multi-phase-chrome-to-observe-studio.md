---
id: CARD-408
title: "View Job Shortcut from Chat Multi-Phase Chrome to Observe Studio"
status: Done
created: 2026-09-21
adr: none
labels:
  - type:feature
  - area:ui
  - area:chat
  - area:observability
---

# [CARD-408] View Job Shortcut from Chat Multi-Phase Chrome to Observe Studio

> **Status**: Done
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:feature`, `area:ui`, `area:chat`, `area:observability`  

---

## 1. Why / Intent (Beat 1: What Jacob Means)

When a multi-phase job is running in Chat Studio and its `job_id` is displayed alongside the copy button, the operator needs a direct, zero-friction path to inspect live job execution in Observe Studio. Rather than manually copying the job ID, opening the Desktop launcher or dock, clicking Observe Studio, and pasting the ID into the search input, there should be a **"View Job"** button right next to the copy action. Clicking it should open (or focus) Observe Studio, automatically populate the job search input with that `job_id`, trigger lookup, and immediately display the job details and phase timeline.

---

## 2. What AutoReiv Does Now (Beat 2)

- In `src/web/static/modules/studios/chat/chrome.js`, the multi-phase job chrome renders:
  ```html
  <span class="chat-job-chrome-id">${escapeHtml(jobId)}</span>
  <button type="button" class="chat-job-chrome-copy-btn" ...>Copy</button>
  ```
- Clicking "Copy" copies the text to the clipboard and shows a brief "Copied!" label.
- There is no navigation affordance to Observe Studio. The user must manually find and launch Observe Studio, find the job inspector input, paste the ID, and click search.

---

## 3. What Will Change (Beat 3)

1. **Chat Job Chrome Shortcut Action** (`src/web/static/modules/studios/chat/chrome.js`):
   - Add a button `class="chat-job-chrome-view-btn"` with label `View Job` adjacent to the Copy button.
   - On click, dispatch an event or call `openStudio("observe", { jobId })` or use `EventBus.publish("navigate:studio", { studio: "observe", params: { jobId } })`.
2. **Observe Studio Auto-Inspection** (`src/web/static/modules/studios/observe.js`):
   - Add handler to receive navigation params / custom event with `jobId`.
   - Automatically set the job search input value to `jobId`, invoke the job fetch method, and render the timeline without requiring manual user typing or clicks.
3. **Desktop Window Activation** (`src/web/static/modules/ui/agent-desktop.js`):
   - Ensure `openStudio("observe")` elevates and focuses the Observe Studio window on the desktop.

---

## 4. What Dies Today (The Prune List - Beat 4)

- **PRUNE**: The manual multi-step workflow (Copy ID -> Launch Dock -> Open Observe -> Find Input -> Paste ID -> Click Inspect) for inspecting active multi-phase jobs from Chat.
- **PRUNE**: Orphaned window navigation workarounds that don't pass route/job state to Observe Studio.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-408-001] View Job Button Affordance**:
  - *Ubiquitous*: THE SYSTEM SHALL render a `"View Job"` button in the Chat multi-phase job chrome header whenever a valid `job_id` is present.
- **[REQ-408-002] Deep-Link to Observe Studio**:
  - *Event-Driven*: WHEN the user clicks the `"View Job"` button in Chat Studio, THE SYSTEM SHALL open or focus the Observe Studio window.
- **[REQ-408-003] Automatic Job Inspection**:
  - *Event-Driven*: WHEN Observe Studio opens via the `"View Job"` shortcut with a `jobId`, THE SYSTEM SHALL automatically pre-fill the job search input and trigger inspection so that results and phases are viewable immediately upon arrival without additional clicks.
- **[REQ-408-004] Robustness Under Inactive Job**:
  - *Unwanted Behavior*: IF the `job_id` cannot be loaded or is invalid, Observe Studio SHALL display a clear error message in its viewer rather than crashing or freezing the desktop window.

---

## 6. Constraints & Verification Plan

### Automated Tests
- Vitest tests in `tests/unit/frontend/chat_job_view_shortcut_408.test.js`:
  - Assert that `renderJobHeader` or multi-phase chrome includes the `.chat-job-chrome-view-btn`.
  - Assert that clicking `.chat-job-chrome-view-btn` invokes navigation to `observe` with `{ jobId }`.
  - Assert that Observe Studio handles incoming `jobId` parameter and executes query.
- Static linting: `npm run lint:frontend` (0 errors, 0 warnings).

### Manual Verification
- Start a multi-phase job in Chat Studio.
- Click **"View Job"**.
- Confirm Observe Studio window opens in focus with the job ID populated and execution status visible.

---

## 7. Landed behavior

The job id and Copy control live on the Chat job strip `#jobPhaseStatusStrip` in `src/web/templates/index.html` (filled from `renderJobPhaseStrip` in `src/web/static/modules/studios/chat.js`). That strip is the multi-phase chrome this card names.

- **View Job** is `button.chat-job-chrome-view-btn` (`data-testid="chat-job-chrome-view-btn"`), immediately after Copy. It stays hidden until a `job_id` is bound, same as Copy.
- Click calls `openObserveJob` (`src/web/static/modules/studios/observability.js`): `switchTab('observability')` opens or focuses the Observe window (`openStudio('observe')` on the desktop resolves to that same tab), writes the id into `#standingJourneyJobIdInput`, opens the Standing Journey section, and loads `GET /api/observability/standing-journey?job_id=`.
- A missing or unknown id does not throw. HTTP failures (including 404) replace the timeline with `Failed to load standing journey: …`. A blank id does not switch studios.
- Education **Open in Observe** uses `openObserveJob` as well, so there is one lookup path.

---

## 8. Human Verification Runbook

About two minutes in the running AutoReiv UI.

1. Open Chat Studio and send a prompt that mints a multi-phase job (a goal with more than one phase). Wait until the strip under the Chat header shows a job id and **Copy**.
2. Confirm **View Job** is beside **Copy**. It should not be there on a plain Direct chat with no job id.
3. Click **View Job**.
4. Expected: the Observe window comes forward (opens if it was closed, un-minimizes if it was minimized). Standing Journey Timeline is open. The search box contains that same job id. The timeline shows phases, or a clear `Failed to load standing journey` line if the job cannot be read. The desktop does not freeze and the browser console has no new page error.
5. Negative check: in that same Observe search box, replace the id with `job_does_not_exist` and click **Load Journey**. Expected: the timeline shows the failure text and Observe stays usable.

Reply `merge to qa` when that matches what you see.

