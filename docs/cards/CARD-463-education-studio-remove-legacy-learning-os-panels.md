---
id: CARD-463
title: "Education Studio cleanup: remove the legacy Learning OS panels, keep operator bar + players"
status: Ready
created: 2026-09-24
branch: qa
adr: ADR-0059 (Education Studio = operator + players)
related:
  - CARD-446
  - CARD-447
  - CARD-448
  - CARD-464
  - CARD-435
  - CARD-369
  - CARD-400
labels:
  - type:refactor
  - area:education
  - area:frontend
  - P1
---

# [CARD-463] Education Studio cleanup: remove the legacy Learning OS panels, keep operator bar + players

> **Status**: Ready (product questions in section 4 should be answered at **continue**, before **build**)
> **Created**: 2026-09-24
> **Observed during**: Jacob review of Education Studio on Jarvis (screenshot shared in chat, described below).
> **ADR Reference**: [ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md) - Studio stays and is the operator + players surface. This card removes the old panel farm that ADR-0059 option 2 rejected; it does **not** retire the Studio.
> **Labels**: `type:refactor`, `area:education`, `area:frontend`, `P1`
> **Related**: [CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md), [CARD-447](./CARD-447-education-studio-operator-strip-and-tutor-context.md), [CARD-448](./CARD-448-education-studio-flashcard-quiz-test-players.md) (all Done - what stays), [CARD-464](./CARD-464-education-studio-full-screen-players-and-flip-flashcards.md) (successor), [CARD-435](./CARD-435-education-tutor-first-direction.md), [CARD-369](./CARD-369-audit-and-prune-dead-ui-controls-and-vestiges-across-studios.md)

---

## What the screenshot showed (described in text)

Education Studio today, top to bottom:

- **Top:** the operator bar (active topic / course, Set active, Pair Tutor, Due, Progress, Wiki curate) and the Flashcard / Quiz / Test players strip - these stay.
- **Left column (Study Launcher):** a Course pipeline block (level shown as "Kindergarten", mastery badge, rank, growth portfolio, progress bar, next milestone), a Knowledge Anchor bar, the current step (e.g. "Priming") and step list, **Jump to step** buttons, a **Presentation / Delivery Profile** toolbar, **Pedagogy Style & Constraints**, **Wiki Grounding** search, and a **Launch Study Session** button.
- **Right column:** collapsible sections **Dual Coding (Prose & Diagram Player)**, **Quiz & Due Reviews**, **Explain-It-Back (Elaboration)**, **Study Artifact & Construction Lab**, **Application Lab**, **Mastery Analysis**, **Delivery Profile**, **Visual Amplifiers**.
- **Bottom:** an **Education Jobs & Study Sessions** list.

Jacob: the original "engineering look" Learning OS UI never added value (it moved to Chat Studio and back). Keep the operator bar and the players.

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Answer the product questions (section 4) - **still no product code** |
| **`build`** | Remove the legacy panels and their frontend code/tests per the inventory |
| **`merge to qa`** | After In Review + the Human Verification Runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | CARD-447 / CARD-448 (Done) |
| **Unlocks** | [CARD-464](./CARD-464-education-studio-full-screen-players-and-flip-flashcards.md) - players take the freed space |
| **Supersedes (proposed)** | CARD-400 education.js decomposition (unmerged commit `ed1f6a6f`; its local branch is no longer present). Splitting 2,753 lines is moot if most of them are deleted. |
| **Blocked by** | Section 4 answers |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Education Studio should be just the operator bar and the players. Remove the old "Learning OS dashboard" panels and launcher that never helped.
2. Do not break anything Tutor or the players still use, and ask me about anything that might still matter instead of silently deleting it.

### Beat 2: What AutoReiv does now

**Markup:** `src/web/templates/index.html` `#view-education` (~L3180-3820). **Code:** `src/web/static/modules/studios/education.js` (2,753 lines; `initEducationStudio` also lazy-loads `education_operator.js` and `education_players.js`). `app.js` ~L405-432 initialises it and wires the Lumina shortcut.

**Inventory - KEEP**

| Element (id) | Where | Backing |
|---|---|---|
| Studio header (title, "Adaptive SRS" badge) | ~L3182-3196 | static |
| Operator bar `#educationOperatorConsole`: `#educationActiveTopic`, `#educationActiveCourseId`, `#educationSetActiveContextBtn`, `#educationPairTutorBtn`, Due / Progress / Curate buttons and panels | ~L3205-3265 (CARD-447) | `education_operator.js`; `/api/education/selected`, `/course/start`, `/mastery/due`, `/progress`, `/wiki/curate`, `/tutor/context` |
| Players `#educationPlayersConsole` (Flashcard / Quiz / Test panels) | ~L3273-3346 (CARD-448) | `education_players.js`; `/quiz/next`, `/quiz/grade`, `/mastery/due` |
| **Topic input `#educationTopicInput`** - currently inside the Ask pane but **read by the operator**: `setEducationStudioActiveContext` (`education_operator.js:71`) takes the topic from it, and `education_operator.js:60` fills it | ~L3354 | **Must move into the operator bar**, not be deleted |

**Inventory - REMOVE (legacy)**

| Element (id) | Where | Only caller of these endpoints |
|---|---|---|
| Header **Refresh** `#educationSessionsRefreshBtn` - only re-renders the local job list (`education.js:1639`) | ~L3197 | none (local) |
| Ask pane / Study Launcher `#educationAskForm` (except the topic input) | ~L3352-3478 | |
| - Course chrome `#educationCourseChrome` (status, mastery badge, academic rank, growth portfolio, progress bar, next milestone) | ~L3368 (CARD-327) | `/course/portfolio/create` |
| - Knowledge Anchor bar `#educationKnowledgeAnchorBar` | ~L3390 (CARD-334) | |
| - Current step / step list, **Jump to step** `#educationModeGroup` (Priming, DualCoding, Construction, Application, Analysis, Environment, Amplifiers, Custom) | Ask pane | `/course/jump`, `/course/complete-step` |
| - Delivery Profile toolbar `#educationDeliveryProfileToolbar` | ~L3421 (CARD-333) | `/environment`, `/environment/select`, `/environment/apply-ask` |
| - Pedagogy Style `#educationTeachStyleInput`, Wiki Grounding `#educationWikiSearchInput` + hits | Ask pane | `/ask/pressure` |
| - Launch Study Session `#educationAskSubmitBtn`, `#educationDiscussTutorBtn` (duplicate of Pair Tutor), status, job chip, open chat / observe | Ask pane | `/api/sessions` + job stream |
| Main column `#educationMainColumn` / `#educationPedagogyColumns`, `details.edu-section` panels: | ~L3480-3817 | |
| - Dual Coding `#educationDualCodingSection` | ~L3485 (CARD-321) | `/course/dual-coding/preview` |
| - Quiz & Due Reviews `#educationQuizPanel` (duplicates players + operator Due) | ~L3533 | `/quiz/extract`, `/retention/run` (UI copy only; Tutor tools keep the backend) |
| - Explain-It-Back `#educationElaborationSection` | ~L3580 (CARD-323) | `/elaboration/extract`, `/elaboration/next`, `/elaboration/grade`, `/course/elaboration/preview`, `/course/elaboration/complete` |
| - Study Artifact & Construction Lab `#educationConstructionSection` | ~L3622 (CARD-324) | `/construction/generate`, `/course/lab/preview`, `/course/lab/grade` |
| - Application Lab `#educationApplicationSection` (incl. `#educationMintExerciseJobBtn`) | ~L3665 (CARD-324) | `/application/extract`, `/application/next`, `/application/mint`, `/application/grade` |
| - Mastery Analysis `#educationAnalysisPanel` | ~L3706 | `/analysis`, `/course/analysis/handoff` |
| - Delivery Profile `#educationEnvironmentPanel` | ~L3744 | `/environment`, `/course/environment/complete` |
| - Visual Amplifiers `#educationAmplifiersPanel` (incl. `#educationAmpWatchLuminaBtn`) | ~L3772 | `/amplifiers`, `/amplifiers/{id}`, `/amplifiers/attach` |
| Education Jobs & Study Sessions `#educationSessionList` - a **browser-only** list in localStorage `autoreiv.education.sessions.v1`, filled only by Launch Study Session | ~L3804-3814 | none (local) |

**Real backing check**

1. **Tutor tools do not use the removed endpoints.** `education_tools.py` covers quiz extract/next/grade, flashcards, mastery / due, retention run, progress, courses and wiki curate. Those backend services stay.
2. **Education Jobs list:** browser-local history of launches from this pane only. Jobs themselves still exist server-side; only this list and the launcher go.
3. **Retention routine** (CARD-319 standing job): reachable through Tutor's `education_retention_run`; the legacy Quiz panel was one more UI entry.
4. **Lumina:** has its own tab (`#tab-lumina`, `lumina.js`). The Amplifiers panel only offered a "Watch in Lumina" shortcut (wired in `app.js`). Lumina's **Send to course** (`/api/lumina/send-to-course`) attaches amplifiers that were only visible in the Visual Amplifiers panel (see question 3).
5. **Backend endpoints left with no UI caller** after removal (only `education.js`, `education_studio.test.js` and their own backend tests reference them): `ask/pressure`, `elaboration/*`, `construction/generate`, `application/*`, `analysis`, `environment`, `environment/select`, `environment/apply-ask`, `amplifiers`, `amplifiers/{id}`, `amplifiers/attach`, `course/complete-step`, `course/jump`, `course/dual-coding/preview`, `course/elaboration/*`, `course/lab/*`, `course/environment/complete`, `course/analysis/handoff`, `course/portfolio/create`. Already caller-less today: `construction/ask-clause`, `analysis/errors`, `analysis/patterns`, `environment/profiles`, `amplifiers/extract`, `amplifiers/refuse-check`, `knowledge-types`, `knowledge-artifact`, `course/mastery/grade`, `course/construction/complete`, `course/application/complete`; test-only: `course/environment/preview`, `course/depth`. **Kept:** `learner` (used by `progress_summary.py`), `course`, `course/start`, `quiz/*`, `mastery/*`, `progress`, `selected`, `tutor/context`, `wiki/curate`, `retention/run`.

### Beat 3: What will change

1. Move `#educationTopicInput` (label "Target topic") into `#educationOperatorConsole` next to Set active; operator behaviour unchanged.
2. Delete every REMOVE element above from `index.html`.
3. Shrink `education.js` to the Studio init that loads the operator and players (plus any helper they still import); delete launcher, course chrome, panel, local-session and job-forwarding code (`buildEducationAsk`, `educationAskKeepsOriginSession`, `buildLearnerPressureClause`, `renderEducationCourseChrome`, `load/save/upsertEducationSessions`, `isEducationJobGoal`, `extractJobIdFromSsePayload`, `forwardJobPhaseChromeEvent`, `gradeEducationAnswerLocal`, `gradeElaborationAnswerLocal` and the panel handlers) once confirmed unused.
4. Remove the Lumina shortcut wiring in `app.js` (~L420-430); the Lumina tab stays.
5. Delete CSS that only styles removed elements: `studios.css` `#educationPedagogyColumns`, `details.edu-section`, `#educationAskForm` / mobile rules; `desktop.css` CARD-237 rules for `#educationAskForm`, `#educationAskSubmitBtn`, `#educationTopicInput` (retarget the topic rule to its new place), `#educationTeachStyleInput`.
6. Tests: delete / rewrite `tests/unit/frontend/education_studio.test.js` (31 tests), `education_continuity_315.test.js` (3), `job_phase_chrome_education.test.js` (8); update id references in `dom_audit.test.js`, `card_447_education_studio_operator.test.js`, `card_441_progress.test.js`, and the Python checks in `tests/unit/education/test_card438_*`, `test_card441_*`, `test_card444_*`.
7. **Backend:** default = **UI only** in this card (single purpose). The caller-less endpoints listed in Beat 2 item 5 are recorded for a follow-up prune card if Jacob wants it (question 5).
8. Leave a one-off localStorage cleanup: remove `autoreiv.education.sessions.v1` on Studio init.

### Beat 4: What dies today

1. DOM: `#educationSessionsRefreshBtn`, `#educationAskForm` (minus the moved topic input), `#educationCourseChrome`, `#educationKnowledgeAnchorBar`, `#educationModeGroup`, `#educationDeliveryProfileToolbar`, `#educationTeachStyleInput`, `#educationWikiSearchInput`, `#educationAskSubmitBtn`, `#educationDiscussTutorBtn`, `#educationMainColumn` / `#educationPedagogyColumns` and the 8 `details.edu-section` panels, `#educationMintExerciseJobBtn`, `#educationAmpWatchLuminaBtn`, `#educationSessionList`.
2. JS: the launcher / course chrome / panel / local-session / job-forwarding functions in `education.js` listed in Beat 3 item 3; the Lumina shortcut in `app.js`.
3. CSS: the `studios.css` and `desktop.css` rules in Beat 3 item 5.
4. Storage: localStorage key `autoreiv.education.sessions.v1`.
5. Tests: `education_studio.test.js`, `education_continuity_315.test.js`, `job_phase_chrome_education.test.js` (or the parts covering removed code).

---

## 2. Acceptance criteria (EARS)

- **[REQ-463-001]** THE Education Studio SHALL show only the header, the operator bar (with the topic input) and the Flashcard / Quiz / Test players.
- **[REQ-463-002]** WHEN Jacob types a topic in the operator bar and clicks Set active, THE SYSTEM SHALL set the active topic / course exactly as before (CARD-447 behaviour).
- **[REQ-463-003]** THE SYSTEM SHALL keep Due, Progress, Wiki curate, Pair Tutor and all three players working.
- **[REQ-463-004]** THE page SHALL NOT contain any element listed in Beat 4 item 1, and no JS SHALL reference those ids.
- **[REQ-463-005]** THE SYSTEM SHALL NOT change any Tutor tool or backend endpoint in this card.
- **[REQ-463-006]** WHEN Education Studio loads, THE SYSTEM SHALL remove localStorage key `autoreiv.education.sessions.v1` if present.
- **[REQ-463-007]** THE frontend and backend test suites SHALL be no worse than before (known CARD-454 / CARD-456 failures excepted).

---

## 3. Human Verification Runbook (under 2 minutes)

1. Pull qa, restart with the serve-hygiene skill, hard-refresh the browser.
2. Open **Education Studio**. Expected: header, operator bar (topic box, Set active, Pair Tutor, Due, Progress, Wiki curate) and the players - nothing else. No launcher, no collapsible sections, no Education Jobs list.
3. Type a topic -> **Set active**: topic and course chips update.
4. Click **Due**, **Progress**, **Wiki curate**: each panel opens.
5. Click **Flashcard** -> **Start deck**; **Quiz** -> **Start / Next**; **Test** -> **Start test**: each loads.
6. Click **Pair Tutor**: Chat opens with Tutor on the active topic.

**Failure signals:** any removed panel still visible; Set active says "Enter a Target Topic"; a console error mentioning an `education*` id.

---

## 4. Product questions for Jacob (answer at continue)

1. **Education Jobs / study-session launcher:** OK to drop launching a multi-phase "study session job" from the Studio, with Pair Tutor (chat with Tutor) as the replacement? (Recommended: yes.)
2. **Retention routine:** OK that it is started only through Tutor (`education_retention_run`), not a Studio button? (Recommended: yes.)
3. **Lumina "Send to course":** after removal, amplifiers sent from Lumina have no place to show in Education Studio. Keep as-is (invisible), or remove the Lumina button in a follow-up?
4. **Mastery rank / growth portfolio / course pipeline (Kindergarten level, steps):** the course model stays in the backend (Tutor uses `education_course`), but its UI goes. Any part you want surfaced in the operator Progress panel instead?
5. **Backend prune:** after this lands, should a follow-up card delete the caller-less endpoints listed in Beat 2 item 5 and their backend tests? (Recommended: yes, as a separate card.)
6. **CARD-400** (split education.js): mark it Superseded by this card? (Recommended: yes.)

---

## 5. Constraints

- Docs-only until **build**.
- ADR-0059 holds: the Studio stays; only the legacy panels go.
- No backend or Tutor tool changes in this card.
- No `main` merge, no GitHub PR, no version bump for docs-only.

---

## 6. Reply phrases

- Answer the questions: say **continue** with answers.
- Start the cleanup: say **build**.
- After the runbook passes: say **merge to qa**.
