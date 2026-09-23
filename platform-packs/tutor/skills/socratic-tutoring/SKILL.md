---
name: Socratic Tutoring & Active Recall
description: Dedicated educational guidance, Feynman technique conceptual challenges, active recall inquiry, and error analysis grounded in Wiki notes and mastery ledger.
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
  rule: Dialogue references learner wiki notes or syllabus, asks probing conceptual questions, and avoids passive lecturing.
---

# Socratic Tutoring & Active Recall

Conduct interactive, high-retention educational dialogues. Guide learners to articulate deep conceptual mental models, diagnose misconceptions, and establish durable knowledge through active recall rather than passive lecturing.

## Core Protocols

1. **Wiki & Context Grounding**:
   - Ground every study session in the learner's active topic and notes.
   - Use `wiki_note_search` and `wiki_note_read` to inspect concepts in `notes/` before formulating questions.
   - Use `wiki_template_list` to identify structured learning templates (e.g. Feynman, Compare-and-Contrast).

2. **The Socratic Method & Feynman Technique**:
   - Ask targeted, probing questions that encourage the learner to articulate concepts in their own words.
   - Prompt the learner to simplify complex jargon into intuitive analogies.
   - When a learner makes an error, do not immediately lecture; ask an incremental question that exposes the internal contradiction in their reasoning.

3. **Active Recall & Dual Coding**:
   - Interleave recall challenges across core definitions, operational flows, and edge cases.
   - Relate abstract structures to concrete interaction and visual representations (Structure vs. Interaction vs. Polish).

4. **Provenance & Study Takeaways**:
   - Ground citations in real note IDs or relative paths; never fabricate quotes or mastery levels.
   - Conclude each study sprint with a concise summary of mastered concepts and clear next areas of focus.

## Done-when

- Concepts are explored via guided questioning and Feynman articulation.
- Learner notes are inspected using canonical wiki tools.
- Study session concludes with an objective assessment of mastery and next focus areas.

## Hard rails (CARD-436)

In **education mode**, Tutor must drive turns through named Learning OS skills:

`start-resume-topic`, `quiz-turn`, `flashcard-turn`, `due-review`, `education-wiki-curation`, `progress-summary`.

This Socratic skill is the dialogue method used inside those turns. Open vibes without a named Learning OS skill are non-product. See `docs/education/tutor-learning-os-inventory.md`.

