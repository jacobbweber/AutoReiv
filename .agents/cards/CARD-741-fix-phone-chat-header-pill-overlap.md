---
id: CARD-741
title: "Fix phone Chat header pill overlap and retire redundant Pair Tutor button in Education Studio"
type: bug
status: In Progress
priority: P2
milestone: M33
needs_decision: none
proof:
  journeys: [card-741-fix-phone-chat-header-pill-overlap]
  checks: [tests/unit/frontend/card_447_education_studio_operator.test.js, tests/unit/frontend/card_463_education_legacy_panels_removed.test.js, tests/unit/frontend/card_437_study_entry.test.js]
branch: feat/card-741-fix-phone-chat-header-pill-overlap-and
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-21
---

# CARD-741 Fix phone Chat header pill overlap and retire redundant Pair Tutor button in Education Studio

## Problem
1. At `390px` phone width, when an active project pill (`#chatActiveProjectPill`) is visible in the Chat top bar (`src/web/templates/partials/chat.html`), `#agentSelect` (`min-w-[150px]`) overflows out of `#chatEngineSelector` (`min-w-0`) and paints directly underneath `#chatActiveProjectPill` (`shrink-0`).
2. In Education Studio (`#educationOperatorConsole` in `src/web/templates/partials/prompts_education_skill_studio.html`), `Set active` (`#educationSetActiveContextBtn`) and `Pair Tutor` (`#educationPairTutorBtn`) sit side by side for the same context-binding job. Just like `Set Active` vs `Pair with Developer` in Projects Studio (`CARD-740`), `Set active` already starts/resumes the course (`POST /api/education/course/start`), persists `selected_education_context` (`PUT /api/education/selected`), and pins the study context into `Tutor`'s memory (`POST /api/education/tutor/context`), while `#chatStudyEntryBtn` (`Study`) in Chat header handles switching to `Tutor`.

## Cause
1. In `src/web/templates/partials/chat.html`, `#chatEngineSelector` used `min-w-0` (allowing flex-shrink below its child `#agentSelect`'s `min-w-[150px]`) inside a non-wrapping (`flex items-center justify-between`) top bar. At `390px` width, `#chatEngineSelector` compressed to ~40px while `#agentSelect` stayed `150px` wide, colliding with `#chatActiveProjectPill`.
2. `#educationPairTutorBtn` was added in `CARD-447`/`CARD-463` before `Set active` (`#educationSetActiveContextBtn`) already assembled `Tutor` context (`POST /api/education/tutor/context`) directly on save; moreover, `renderEducationActiveContextChrome` updated only `#educationActiveTopic`/`#educationActiveCourseId` and did not sync `#educationPlayerContextTopic`/`#educationPlayerContextCourse` in the Players bar below it.

## Change
- `src/web/templates/partials/chat.html`: add `flex-wrap gap-2` to the Chat top bar and `flex-wrap gap-1.5 sm:gap-2` to the selector/pill container, and change `#chatEngineSelector` from `min-w-0` to `shrink-0` so `#agentSelect` (`min-w-[150px]`) and `#chatActiveProjectPill` never overlap at `390px` phone width.
- `src/web/templates/partials/prompts_education_skill_studio.html`: remove `#educationPairTutorBtn` (`Pair Tutor`) from `#educationOperatorConsole`.
- `src/web/static/modules/studios/education_operator.js`: remove the `educationPairTutorBtn` listener and unused `enterTutorEducationMode` import, and update `renderEducationActiveContextChrome(selected)` to also sync `#educationPlayerContextTopic` and `#educationPlayerContextCourse` when `Set active` is clicked.
- `docs/findings.md`: remove the resolved M33 phone Chat top-bar overlap finding.
- `tests/unit/frontend/card_447_education_studio_operator.test.js`, `tests/unit/frontend/card_463_education_legacy_panels_removed.test.js`, `tests/unit/frontend/card_437_study_entry.test.js`: update unit tests to assert `#educationPairTutorBtn` is retired, `#educationSetActiveContextBtn` updates both Operator and Players topic/course badges, and `#chatEngineSelector` uses `shrink-0` inside a `flex-wrap` Chat top bar.
- `tests/e2e/journeys/card-741-fix-phone-chat-header-pill-overlap.mjs`: live journey on desktop (`1280x800`) and phone (`390x844`) verifying zero bounding-box overlap between `#agentSelect` and `#chatActiveProjectPill`, verifying `#educationPairTutorBtn` is retired from Education Studio while `Set active` updates both `#educationActiveTopic` and `#educationPlayerContextTopic`, and verifying `Tutor` in Chat knows the active topic set via `Set active`.

## What dies
- `#educationPairTutorBtn` button in `src/web/templates/partials/prompts_education_skill_studio.html`.
- `pairBtn` (`$('educationPairTutorBtn')`) listener and unused `enterTutorEducationMode` import in `src/web/static/modules/studios/education_operator.js`.

## Proof
- Journey `card-741-fix-phone-chat-header-pill-overlap`:
  1. Sets an active project, opens Chat Studio on desktop and phone (`390x844`), and asserts the bounding boxes of `#agentSelect` and `#chatActiveProjectPill` have zero intersection (`overlapArea === 0`) and zero horizontal overflow.
  2. Opens Education Studio (`#view-education`), verifies `#educationPairTutorBtn` is absent (`count === 0`), enters a topic in `#educationTopicInput`, clicks `#educationSetActiveContextBtn` (`Set active`), and verifies both `#educationActiveTopic`/`#educationActiveCourseId` and `#educationPlayerContextTopic`/`#educationPlayerContextCourse` update immediately.
  3. Switches to Chat Studio, selects `Tutor` (`#chatStudyEntryBtn`), and verifies the Study strip (`#chatEducationModeTopic`) reflects the active topic set via `Set active` in Education Studio.
- Checks: `tests/unit/frontend/card_447_education_studio_operator.test.js`, `tests/unit/frontend/card_463_education_legacy_panels_removed.test.js`, `tests/unit/frontend/card_437_study_entry.test.js`.

## Plan and decisions
- Approved by Jacob (`Option A`): Fix the `390px` phone Chat header overlap between `#agentSelect` and `#chatActiveProjectPill`, and retire `#educationPairTutorBtn` (`Pair Tutor`) in Education Studio so `Set active` (`#educationSetActiveContextBtn`) is the single lever in the Education operator bar.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
- **Fixed**: Prevented `#agentSelect` and `#chatActiveProjectPill` from overlapping in the Chat top bar on `390px` phone screens and retired the redundant `Pair Tutor` button (`#educationPairTutorBtn`) in Education Studio in favor of `Set active` (`#educationSetActiveContextBtn`) (`CARD-741`).
