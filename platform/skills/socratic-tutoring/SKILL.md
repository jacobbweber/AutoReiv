---
name: Socratic Tutoring & Active Recall
description: Dedicated educational guidance, Feynman technique conceptual challenges, active recall inquiry, and error analysis grounded in Wiki notes and mastery ledger.
tools:
- wiki_note_read
- wiki_note_search
- wiki_note_list
- wiki_template_list
version: 1.1.0
tier: platform
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Dialogue references learner wiki notes or syllabus, asks probing conceptual questions, and avoids passive lecturing.
---

# Socratic Tutoring & Active Recall

Conduct interactive, high-retention educational dialogues across **Socratic Tutoring**, **Education Priming** (outline, schema, prerequisites, and learning goals with durable ledger anchors in `memory.db`), **Education Dual Coding** (clear prose paired with a fenced Mermaid diagram), and **Education Construction** (generative study artifacts). Guide learners to articulate deep conceptual mental models, diagnose misconceptions, and establish durable knowledge through active recall rather than passive lecturing.

## Progressive References (`skill_view`)
- `skill_view(skill_id="socratic-tutoring", reference="learning-modes.md")`: Cognitive mode protocols for **Priming**, **Dual Coding**, **Construction**, and **Application**, plus how they pair with Tutor's Learning OS skills.
- `skill_view(skill_id="socratic-tutoring", reference="priming-and-construction.md")`: Step-by-step Wiki write-back runbooks for **Education Priming**, **Education Dual Coding**, and **Education Construction** (`CARD-241`, `CARD-245`, `CARD-317`).

## Tools (order) — catalog-matched `wiki_note_*` only [CARD-241 / CARD-245 / CARD-317]

When grounding or staging Priming, Dual Coding, or Construction study artifacts into `00_Inbox/`, call **only** catalog-matched Wiki tools:

1. `wiki_note_search` / `wiki_note_list` — ground in existing notes and priors in the vault.
2. `wiki_note_read` / `wiki_template_list` — inspect selected grounding notes and `education-*` templates.
3. `wiki_note_create` — stage Priming schemas, Dual Coding (prose + Mermaid) notes, or Construction study artifacts into `00_Inbox/` (one-door policy, seeding ledger anchors in `memory.db` / `education_mastery`).

**Forbidden**: `wiki_overview`, `wiki_graph`, and any other bare/non-matched Wiki tool during Education Priming, Dual Coding, or Construction turns. If a tool is missing or blocked, **soft-fail / skip it** and continue with `wiki_note_search` / `wiki_note_read` / `wiki_note_create` so Execute still lands the Inbox note.

## Order

1. **Wiki & Context Grounding**:
   - Search and read the learner's active topic notes (`wiki_note_search`, `wiki_note_read`, `wiki_note_list`) and templates (`wiki_template_list`).
2. **Priming, Dual Coding & Construction Write-Back**:
   - For **Education Priming**: draft a schema (outline, prerequisites, learning goals, and quiz anchors) and write to `00_Inbox/` via `wiki_note_create` so ledger anchors land in `memory.db`.
   - For **Education Dual Coding**: pair verbal explanation with a fenced Mermaid diagram and stage in `00_Inbox/`.
   - For **Education Construction**: stage a combined study artifact (schema + dual-code Mermaid + quiz + elaboration prompts) in `00_Inbox/`.
3. **The Socratic Method & Feynman Technique**:
   - Ask targeted, probing questions that encourage the learner to articulate concepts in their own words and simplify jargon into analogies.
   - When the learner makes an error, ask an incremental question that exposes the contradiction rather than lecturing.
4. **Provenance & Study Takeaways**:
   - Ground citations in real note paths; never fabricate quotes or mastery levels. Conclude each study sprint with an objective summary and next focus areas.

## Done-when

- Concepts are explored via guided questioning, Feynman articulation, or staged study notes (`00_Inbox/`) with durable ledger anchors in `memory.db`.
- Learner notes are inspected using canonical wiki tools without calling forbidden bare `wiki_overview`.

## Hard rails (CARD-436)

In **education mode**, Tutor must drive turns through named Learning OS skills:

`start-resume-topic`, `quiz-turn`, `flashcard-turn`, `due-review`, `education-wiki-curation`, `progress-summary`.

This Socratic skill is the dialogue method used inside those turns. Open vibes without a named Learning OS skill are non-product. See `docs/education/tutor-learning-os-inventory.md` and `skill_view(skill_id="socratic-tutoring", reference="learning-modes.md")`.
