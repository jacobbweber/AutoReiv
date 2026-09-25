---
name: Flashcard Turn (SRS Card)
description: Run one spaced flashcard / SRS turn using mastery due items and flashcard Wiki template; durable grade path shared with quiz.
version: 1.2.0
tier: platform
requires_tools:
  - education_flashcard_next
  - education_flashcard_grade
  - education_mastery_due
  - education_mastery_upsert
  - wiki_note_read
  - wiki_template_list
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Education-mode Tutor invokes this named Learning OS skill; grades via education_flashcard_grade into education_mastery; never invent success on tool failure; never mid-turn wiki_note_create / curation loops (CARD-444).
---

# Flashcard Turn (SRS Card)

Run **one** flashcard / SRS card turn. Keep the ReAct tool loop tiny so the turn finishes under Tutor's default `max_turns` (do not burn the budget on Wiki side quests).

## Minimal tool loop (CARD-444) — stay under the turn budget

Happy path (due ledger has at least one item) — **at most two education tool calls**:

1. `education_flashcard_next` (or `education_mastery_due`) → select one due card.
2. Prompt the learner with the **front only** (`prompt`). Do **not** reveal `expected_answer` until after they attempt.
3. When they answer → `education_flashcard_grade` with `item_id` + learner `answer`.
4. Report `grade` / `interval_stage` / `next_due` from the tool, then **stop**. Do not open Wiki tools after a successful grade.

Empty due ledger — **seed once, then grade** (still no curation loop):

1. `education_flashcard_next` / `education_mastery_due` returns empty.
2. At most **one** targeted `wiki_note_read` of a known `education-flashcard` note (optional `wiki_template_list` only if you need the template slug).
3. `education_mastery_upsert` once with prompt + expected_answer from that note.
4. Prompt front-only → `education_flashcard_grade` → report honestly → **stop**.

Target fixed tool count for a seeded due card: **next → grade** (2 tools). Empty-due seed path: **next → (optional one wiki_note_read) → upsert → grade** (≤4 tools). Both stay far under the default turn budget; never raise `max_turns` to make this skill fit.

## Forbidden mid-turn (CARD-444)

Inside this skill turn, **do not**:

- Call `wiki_note_create`, `wiki_note_update`, or any education-wiki-curation path (`education_wiki_curate_from_link`, `education_wiki_curate_from_curriculum`, `education_wiki_template_catalog`).
- Open a multi-note `wiki_note_search` / `wiki_note_list` loop to "find something to study."
- Switch to the `education-wiki-curation` skill mid-flashcard-turn.
- Keep calling Wiki tools after the card is selected and graded.

Wiki curation belongs on **`education-wiki-curation`**, not here. If the library is empty and you cannot seed from one known flashcard note, report that honestly and stop — do not invent grades or burn turns curating.

## Exact agent tools (CARD-438 durable path; CARD-444 efficiency)

| Tool | Role | HTTP twin |
|---|---|---|
| `education_flashcard_next` | Next due SRS / flashcard item(s) | `GET /api/education/mastery/due` |
| `education_mastery_due` | Full due list | `GET /api/education/mastery/due` |
| `education_mastery_upsert` | Seed / upsert a card (empty-due only) | `POST /api/education/mastery/upsert` |
| `education_flashcard_grade` | Binary grade + SRS advance (shared path) | `POST /api/education/quiz/grade` |

There is **no** `/api/education/flashcard/*` router. Flashcards share the mastery / SRS ledger with quiz (`srs.next_due_after_grade`).

Seed-only Wiki tools (empty due): `wiki_note_read`, `wiki_template_list`. Not for curation.

## Front-only then grade discipline

- Show **front** (`prompt`) first; hide expected answer until after the learner's attempt.
- Grade only via `education_flashcard_grade` — never invent a chat-only pass/miss.
- On `success=false`, do **not** claim a durable SRS update.

## Wiki

- Template: `education-flashcard` (`data/wiki/02_Resources/_Templates/education-flashcard.md`)

## Done-when

- A due card is presented (front-only), graded via `education_flashcard_grade`, and `next_due` / interval updated in `education_mastery`.
- Tool-call names on the happy path are the education flashcard/mastery set — **no** `wiki_note_create`.
- The turn finishes without `Execution terminated: Max turn budget of N reached.`

## Hard rails (CARD-436 / CARD-435 / CARD-444)

Education-mode Tutor **must** use a named Learning OS skill (this skill or a sibling Learning OS skill id). Open vibes and freeform chat without a named Learning OS skill are **non-product**. `socratic-tutoring` is the dialogue method used *inside* Learning OS turns; it is not a bypass of these rails.

Never invent a successful durable grade when `education_flashcard_grade` fails. Never spend the turn budget on Wiki side quests instead of grading.

## AppData note

Prefer the platform pack body under `platform-packs/tutor/skills/flashcard-turn/`. If live AppData `packs/tutor/` lags, that is [CARD-443](../../../../docs/cards/CARD-443-platform-tutor-pack-appdata-sync.md) — do not manually redesign Learning OS here.

## Successor

- Due-review packaging / queue UX: **CARD-439** (Done tools); default turn budget for every agent: **CARD-445** (separate — do not raise budget as a crutch for this skill).
