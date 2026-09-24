---
name: Start / Resume Topic (Learning OS Course)
description: Start or resume an ordered Learning OS course for a topic; bind Tutor education mode to course chrome and tutor context.
version: 1.0.0
tier: platform
requires_tools:
  - wiki_note_read
  - wiki_note_search
  - wiki_note_list
  - wiki_template_list
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Education-mode Tutor invokes this named Learning OS skill; durable Learning OS APIs or Wiki templates are cited; no invented backend.
---

# Start / Resume Topic (Learning OS Course)

Open or continue a durable Learning OS course for the learner's topic.

## Durable contracts (exist today)

- `POST /api/education/course/start` — `src/application/education/course.py` `start_or_resume_course`
- `GET /api/education/course` — course chrome snapshot (`course_chrome_snapshot`)
- `POST /api/education/course/jump` — jump to a known step
- `POST /api/education/tutor/context` — `src/application/education/tutor.py` `assemble_tutor_topic_context`
- Ledger: agent `memory.db` table `education_course` (`src/infrastructure/memory/repositories/education_course_ops.py`)

## Wiki

- Prefer priming / concept templates: `education-priming`, `education-concept` under `data/wiki/02_Resources/_Templates/`
- Ground with `wiki_note_search` / `wiki_note_read` before advising next step

## Agent tool lane

No dedicated `education_course_*` agent tool yet. CARD-437 wires Study entry (Chat + Tutor education mode) to the HTTP contracts above (`study_entry.js` → course/start + tutor/context). Education Studio Ask / course chrome remain available until CARD-442. Do not fake a course tool.

## Done-when

- Topic has an active course row (or explicit resume) and Tutor knows current step + wiki grounding.
- Inventory row: Studio Ask + `#educationCourseChrome` → this skill.

## Successor

- Study entry UX / Tutor education-mode thin shell: **CARD-437**


## Hard rails (CARD-436 / CARD-435)

Education-mode Tutor **must** use a named Learning OS skill (this skill or a sibling Learning OS skill id). Open vibes and freeform chat without a named Learning OS skill are **non-product**. `socratic-tutoring` is the dialogue method used *inside* Learning OS turns; it is not a bypass of these rails.

If a required HTTP/tool binding is not yet callable from the agent tool lane, do not invent a fake tool. Cite the durable `/api/education/*` contract below and the owning successor card. Studio UI remains alive until CARD-442.

