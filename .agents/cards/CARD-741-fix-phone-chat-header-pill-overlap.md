---
id: CARD-741
title: "Fix phone Chat header pill overlap and retire redundant Pair Tutor button in Education Studio"
type: bug
status: Done
priority: P2
milestone: M33
needs_decision: none
proof:
  journeys: [card-741-fix-phone-chat-header-pill-overlap]
  checks: [tests/unit/education/test_card447_education_studio_selected_context.py, tests/unit/frontend/card_447_education_studio_operator.test.js, tests/unit/frontend/card_463_education_legacy_panels_removed.test.js, tests/unit/frontend/card_437_study_entry.test.js]
branch: feat/card-741-fix-phone-chat-header-pill-overlap-and
log: {minutes: 15, qa_runs: 2, findings: 1}
created: 2026-10-21
completed: 2026-10-21
---

# CARD-741 Fix phone Chat header pill overlap and retire redundant Pair Tutor button in Education Studio

## Problem
1. At `390px` phone width, when an active project pill (`#chatActiveProjectPill`) is visible in the Chat top bar (`src/web/templates/partials/chat.html`), `#agentSelect` (`min-w-[150px]`) overflows out of `#chatEngineSelector` (`min-w-0`) and paints directly underneath `#chatActiveProjectPill` (`shrink-0`).
2. In Education Studio (`#educationOperatorConsole` in `src/web/templates/partials/prompts_education_skill_studio.html`), `Set active` (`#educationSetActiveContextBtn`) and `Pair Tutor` (`#educationPairTutorBtn`) sit side by side for the same context-binding job. Furthermore, while `AutoReiv` had `## Active Selected Project` injected into its system prompt from `ProjectsService.get_selected()`, `Tutor` never had `## Active Selected Study Context` injected from `get_selected_education_context()`.

## Cause
1. In `src/web/templates/partials/chat.html`, `#chatEngineSelector` used `min-w-0` (allowing flex-shrink below its child `#agentSelect`'s `min-w-[150px]`) inside a non-wrapping (`flex items-center justify-between`) top bar. At `390px` width, `#chatEngineSelector` compressed to ~40px while `#agentSelect` stayed `150px` wide, colliding with `#chatActiveProjectPill`.
2. `#educationPairTutorBtn` duplicated the study entry lever (`#chatStudyEntryBtn`), `renderEducationActiveContextChrome` updated only `#educationActiveTopic`/`#educationActiveCourseId` without syncing `#educationPlayerContextTopic`/`#educationPlayerContextCourse`, and `build_effective_system_message` in `src/application/kernel/system_prompt_builder.py` only injected `selected_project` and omitted `get_selected_education_context(kernel.state_store)`.

## Change
- `src/web/templates/partials/chat.html`: add `flex-wrap gap-2` to the Chat top bar and `flex-wrap gap-1.5 sm:gap-2` to the selector/pill container, and change `#chatEngineSelector` from `min-w-0` to `shrink-0` so `#agentSelect` (`min-w-[150px]`) and `#chatActiveProjectPill` never overlap at `390px` phone width.
- `src/web/templates/partials/prompts_education_skill_studio.html`: remove `#educationPairTutorBtn` (`Pair Tutor`) from `#educationOperatorConsole`.
- `src/web/static/modules/studios/education_operator.js`: remove the `educationPairTutorBtn` listener and update `renderEducationActiveContextChrome(selected)` to also sync `#educationPlayerContextTopic` and `#educationPlayerContextCourse` when `Set active` is clicked.
- `src/application/kernel/system_prompt_builder.py`: inject `## Active Selected Study Context` (`Topic` and `Course ID` from `get_selected_education_context(kernel.state_store)`) when the agent has education tools (`has_education_tools`), matching `has_project_tools`.
- `docs/findings.md`: remove the resolved M33 phone Chat top-bar overlap finding.
- `tests/unit/education/test_card447_education_studio_selected_context.py`, `tests/unit/frontend/card_447_education_studio_operator.test.js`, `tests/unit/frontend/card_463_education_legacy_panels_removed.test.js`, `tests/unit/frontend/card_437_study_entry.test.js`: unit tests for `## Active Selected Study Context` system prompt injection, `#educationPairTutorBtn` retirement, Players context chrome sync, and Chat top-bar `shrink-0` / `flex-wrap`.
- `tests/e2e/journeys/card-741-fix-phone-chat-header-pill-overlap.mjs`: live journey on desktop (`1280x800`) and phone (`390x844`) verifying zero bounding-box overlap between `#agentSelect` and `#chatActiveProjectPill`, verifying `#educationPairTutorBtn` is retired from Education Studio while `Set active` updates both `#educationActiveTopic` and `#educationPlayerContextTopic`, and verifying `Tutor` in Chat knows the active topic and course ID directly from `Set active`.

## What dies
- `#educationPairTutorBtn` button in `src/web/templates/partials/prompts_education_skill_studio.html`.
- `pairBtn` (`$('educationPairTutorBtn')`) listener in `src/web/static/modules/studios/education_operator.js`.

## Proof
- Journey `card-741-fix-phone-chat-header-pill-overlap`:
  1. Sets an active project, opens Chat Studio on desktop and phone (`390x844`), and asserts the bounding boxes of `#agentSelect` and `#chatActiveProjectPill` have zero intersection (`overlapArea === 0`) and zero horizontal overflow.
  2. Opens Education Studio (`#view-education`), verifies `#educationPairTutorBtn` is absent (`count === 0`), enters a topic in `#educationTopicInput`, clicks `#educationSetActiveContextBtn` (`Set active`), and verifies both `#educationActiveTopic`/`#educationActiveCourseId` and `#educationPlayerContextTopic`/`#educationPlayerContextCourse` update immediately.
  3. Switches to Chat Studio, selects `Tutor` (`#chatStudyEntryBtn`), and verifies `Tutor` replies with the active study topic and course ID without needing to call tools.
- Checks: `tests/unit/education/test_card447_education_studio_selected_context.py`, `tests/unit/frontend/card_447_education_studio_operator.test.js`, `tests/unit/frontend/card_463_education_legacy_panels_removed.test.js`, `tests/unit/frontend/card_437_study_entry.test.js`.

## Plan and decisions
- Approved by Jacob (`Option A`): Fix the `390px` phone Chat header overlap between `#agentSelect` and `#chatActiveProjectPill`, and retire `#educationPairTutorBtn` (`Pair Tutor`) in Education Studio so `Set active` (`#educationSetActiveContextBtn`) is the single lever in the Education operator bar.

## Findings
- Fixed (in-area): `build_effective_system_message` in `src/application/kernel/system_prompt_builder.py` injected `## Active Selected Project` from `ProjectsService.get_selected()` for `AutoReiv`, but never injected `## Active Selected Study Context` from `get_selected_education_context(kernel.state_store)` for `Tutor`. Added `has_education_tools` injection so `Tutor` knows the active topic and course ID on every turn once `Set active` is saved.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-741-fix-phone-chat-header-pill-overlap` | desktop | PASS | Zero overlap between `#agentSelect` and `#chatActiveProjectPill`; `Set active` updated both Operator and Players badges without `#educationPairTutorBtn`; `Tutor` answered with active topic `Raft Consensus desktop` |
| `card-741-fix-phone-chat-header-pill-overlap` | phone | PASS | Zero overlap between `#agentSelect` and `#chatActiveProjectPill` (`top: 48..78` vs `top: 84..105`); `Set active` updated both Operator and Players badges without `#educationPairTutorBtn`; `Tutor` answered with `Raft Consensus phone` (`course_ee9efd57958c`) |

### Screenshots
- `/tmp/autoreiv-qa/card-741/card-741-fix-phone-chat-header-pill-overlap-phone-01-1-verify-agentselect-and-chatactiveprojectpill-d.png`
- `/tmp/autoreiv-qa/card-741/card-741-fix-phone-chat-header-pill-overlap-desktop-02-2-verify-educationpairtutorbtn-is-retired-in-edu.png`
- `/tmp/autoreiv-qa/card-741/card-741-fix-phone-chat-header-pill-overlap-phone-03-3-verify-chat-study-button-binds-the-set-active-.png`

## Release note
- **Fixed**: Prevented `#agentSelect` and `#chatActiveProjectPill` from overlapping in the Chat top bar on `390px` phone screens, retired the redundant `Pair Tutor` button (`#educationPairTutorBtn`) in Education Studio in favor of `Set active` (`#educationSetActiveContextBtn`), and injected `## Active Selected Study Context` into `Tutor`'s system prompt on every turn (`CARD-741`).
