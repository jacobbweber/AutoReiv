---
id: CARD-437
title: "Study Entry = Tutor Education Mode (Thin Shell; Keep Studio Alive)"
status: In Review
created: 2026-09-23
adr: none
labels:
  - type:feature
  - area:education
  - area:tutor
  - P0
parent: CARD-435
---

# [CARD-437] Study Entry = Tutor Education Mode (Thin Shell; Keep Studio Alive)

> **Status**: In Review
> **Created**: 2026-09-23
> **Baseline**: `qa` @ `9f2e7b14` (after CARD-435 docs tip)
> **ADR Reference**: none
> **Labels**: `type:feature`, `area:education`, `area:tutor`, `P0`
> **Parent**: [CARD-435](./CARD-435-education-tutor-first-direction.md)
> **Build order**: **2 of 7**. Keep Education Studio nav/landing until [CARD-442](./CARD-442-retire-education-studio-landing.md).

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine Study shell vs Chat deep-link, course-context shape — **still no product code** |
| **`build`** | Implement Study entry → Tutor education mode + course context. Do **not** remove Education Studio nav. |
| **`merge to qa`** | After In Review + live operator proof |

Do **not** write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | [CARD-436](./CARD-436-inventory-tutor-learning-os-rails.md) Done or In Review with inventory skill ids usable |
| **Blocked by** | Missing Tutor education-mode skill inventory from CARD-436 |
| **Unlocks** | [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md), [CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md), and later progress/retirement cards that assume Study → Tutor entry |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Study starts as **Tutor in education mode** with course context, not as “open the Education Studio panel farm.”
2. This slice is a **thin shell / entry**: add or adjust Study entry that opens Tutor education mode. **Do not** remove Education Studio bottom-nav or landing yet — Studio stays as reference while later cards move quiz, reviews, wiki curation, and progress.

### Beat 2: What AutoReiv does now

1. Bottom-nav / tabs: `src/web/templates/index.html` button `#tab-education` (`data-studio="education"`) opens `#view-education` / `#educationStudio` (Education Studio landing).
2. Study launcher today is Ask form chrome inside Education Studio (`#educationAskForm`, `#educationTopicInput`, course chrome `#educationCourseChrome`).
3. Tutor discuss exists inside Education Studio (`discussWithTutor` path in `src/web/static/modules/studios/education.js` calling `/api/education/tutor/context`); Chat can select Tutor but is not the sole Study destination with education-mode rails.
4. Course APIs: `POST /api/education/course/start`, `GET /api/education/course`, jump/complete-step under `src/web/routers/education.py` backed by `src/application/education/course.py`.

### Beat 3: What will change

1. Add or adjust a **Study** entry (exact control location locked at **continue**/**build**: e.g. Chat deep-link, dock/Study button, or secondary control that is not “retire the Education tab”) that opens **Tutor in education mode** with topic/course context.
2. Education mode must carry course context (topic, `course_id` / agent id as Learning OS already uses) into Tutor using CARD-436 named skills (start/resume at minimum).
3. Prefer reusing existing Chat / Agent Desktop / standing-job patterns over a new mega-shell. Document the chosen operator path in-card during build.
4. **Keep** `#tab-education`, `#view-education`, and Education Studio panels fully available.

**Out of scope:** Removing Education Studio ([CARD-442](./CARD-442-retire-education-studio-landing.md)); chat quiz durability ([CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md)); due reviews UX ([CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md)); wiki curation ([CARD-440](./CARD-440-wiki-curation-from-links-curriculum.md)); non-Studio progress UI ([CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md)); Lumina; monolith split of `education.js`.

### Beat 4: What dies today

1. The product story that Study *only* means “land on Education Studio Ask pane.”
2. Nothing about the Education Studio dashboard itself — it stays until CARD-442.

---

## 2. Acceptance criteria

- **[REQ-437-001]** WHEN the operator uses the new/adjusted Study entry, THE SYSTEM SHALL open Tutor in education mode with course/topic context (start or resume via Learning OS course APIs), without requiring the operator to navigate Education Studio panels first.
- **[REQ-437-002]** WHEN Study entry succeeds, THE OPERATOR SHALL see Tutor (Chat or agreed thin shell) with education-mode rails from CARD-436, not a freeform untitled chat with no course binding.
- **[REQ-437-003]** THE SYSTEM SHALL NOT remove or hide `#tab-education` / `#view-education` / Education Studio landing on this card.
- **[REQ-437-004]** Anti-theatre: course start/resume MUST hit durable Learning OS (`/api/education/course/start` and/or `GET /api/education/course`) so refresh still shows the same course state.

---

## 3. Proof / live-test notes

1. From a cold browser on Jarvis: use Study entry → Tutor education mode on a known topic; confirm course chrome or Tutor context shows the same course id as `GET /api/education/course`.
2. Hard-refresh; resume still binds the same course (durable).
3. Open Education Studio tab — still works as before (reference path).
4. Failure modes: missing topic → clear operator error; Tutor pack missing → fail soft with exact message; do not silently open plain Chat without education mode.
5. Automated: frontend and/or API contract tests for Study entry → education mode flags + course bind (paths chosen at **build**).

---

## 4. Constraints

- Branch off `qa`: `feat/card-437-*` only after **build**.
- **No product code** until Jacob says **build**.
- Do not merge to `main`. No GitHub PRs. No version bump for docs-only.
- Do not implement CARD-434. Do not retire Studio early.

---



---

## Implementation notes (In Review)

**Branch**: `feat/card-437-study-entry-tutor-education-mode`

### Chosen operator path (locked at build)

**Simplest honest path**: reuse Chat + select Tutor + education-mode flag + durable course bind.

1. Click **Study** in the left studio nav (`#btn-study-entry`, next to Education — not a replacing tab), **or** click **Study** in the Chat header (`#chatStudyEntryBtn`).
2. Enter a topic in the prompt (defaults to last Study topic from `localStorage`). Cancel / blank → error toast; does **not** open plain untitled Chat.
3. System:
   - `POST /api/education/course/start` with `agent_id=tutor`, `topic_id=<topic>` (Learning OS skill `start-resume-topic`)
   - `POST /api/education/tutor/context` with `agent_id=tutor`, `topic=<topic>`
   - `switchTab('chat')` + `switchSelectedAgent('tutor')`
   - Shows `#chatEducationModeStrip` with skill / topic / course id (education-mode rails)
   - Prefills `#chatInput` with `[Tutor Education Mode] skill=start-resume-topic …`
4. Education Studio remains: `#tab-education` → `#view-education` / `#educationStudio` unchanged. Studio **Discuss with Tutor** now calls the same `enterTutorEducationMode` helper.

### Delivered

- Module: `src/web/static/modules/studios/study_entry.js` (`enterTutorEducationMode`, course/tutor API helpers, chrome)
- Markup: `#btn-study-entry`, `#chatStudyEntryBtn`, `#chatEducationModeStrip` (+ topic/course/skill/exit)
- Wire: `src/web/static/app.js` `initStudyEntry`; `education.js` `discussWithTutor` reuses Study entry
- Tests: `tests/unit/frontend/card_437_study_entry.test.js` (REQ-437-001..004 contracts)
- Must-not held: Education nav/landing not removed; no mega Studio; CARD-438..442 out of scope

### Live-test checklist (Jacob / Jarvis)

1. Cold browser on Jarvis Control Plane.
2. Click sidebar **Study** → enter topic e.g. `Bayes Theorem` → lands on Chat with **Tutor** selected; emerald **Education mode** strip shows skill `start-resume-topic`, topic, and a `course_…` id.
3. Confirm `GET /api/education/course?agent_id=tutor&topic_id=Bayes%20Theorem` returns the same `course_id` as the strip (durable Learning OS).
4. Hard-refresh → strip may restore from local chrome; click Study again with same topic → resume same course id (anti-theatre).
5. Open **Education** tab — Studio Ask / panels still work (reference path).
6. Blank/cancel Study prompt → error toast; Chat does not silently become freeform untitled education session.
7. Automated: `npx vitest run tests/unit/frontend/card_437_study_entry.test.js`



### Live fix (2026-09-23 ET) — datetime JSON on Tutor chat

Jacob live-tested Study → topic `okta` → education strip OK (`course_f4f105904ee1`). First Tutor Chat turn failed with:

`⚠️ Error: Object of type datetime is not JSON serializable`

**Root cause**: `src/application/kernel/agent_kernel.py` `stream_turn` did `json.dumps(tool_res.output)` (observability traceback @ former L1648). A tool result dict carried a raw `datetime` (education course/tutor/SRS-shaped fields are the high-probability source). FastAPI `jsonable_encoder` hid the same values on `/api/education/*`, but the kernel Chat path uses stdlib `json.dumps`.

**Fix**:
- `src/infrastructure/serialization/json_safe.py` — `dumps_jsonable` / `dumps_tool_output` (datetime → ISO)
- Kernel tool-result + parked + tool-schema sizing uses the helper
- Telemetry `metadata_json` and Chat `_sse` also use it (defense in depth)
- Regression: `tests/unit/kernel/test_json_safe_datetime.py`

**Retry**: Study → topic → send a Tutor message (education-mode prompt or follow-up). Expect no datetime JSON error in the Tutor bubble.

### After live proof

Say **merge to qa**.

## 5. Reply phrases

- Refine entry UX: say **continue**.
- Start implementation: say **build**.
- After live proof: say **merge to qa**.
