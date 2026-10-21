# Flashcard Turn SRS Loop & Efficiency Guide (`srs-loop.md`)

Use this reference to keep `flashcard-turn` fast, front-only, and strictly bounded under `CARD-444`.

## 1. Happy Path (2 Tool Calls Total)
1. Call `education_flashcard_next` (or `education_mastery_due`) to fetch the next due card.
2. Present **only the front** (`prompt`) to the learner; never reveal `expected_answer` before their attempt.
3. Once the learner replies, call `education_flashcard_grade(item_id=..., answer=...)` and report `grade`, `interval_stage`, and `next_due`. Stop immediately.

## 2. Empty Due Queue (At Most 4 Tool Calls)
1. `education_flashcard_next` returns empty.
2. Read at most **one** known `education-flashcard` note via `wiki_note_read`.
3. Seed one card via `education_mastery_upsert(topic=..., wiki_path=..., prompt=..., expected_answer=...)`.
4. Present the front prompt, then grade via `education_flashcard_grade` once the learner answers.

## 3. Hard Exclusions (`CARD-444`)
- Never call `wiki_note_create`, `wiki_note_update`, `wiki_note_search`, `wiki_note_list`, or `education_wiki_curate_*` inside `flashcard-turn`.
