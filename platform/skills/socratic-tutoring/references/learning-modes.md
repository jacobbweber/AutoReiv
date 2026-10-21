# Cognitive Learning Modes & Learning OS Reference (`learning-modes.md`)

Tutor combines Socratic inquiry with four structured cognitive modes and six durable Learning OS turn skills.

## Four Cognitive Modes

1. **Priming (`education-priming`)** — *Schema & Prerequisites*:
   - Build a high-level structural outline, prerequisite map, and learning objectives before diving into dense details.
   - Ground in `wiki_note_search` / `wiki_note_read` and stage new priming outlines into `00_Inbox/` via `wiki_note_create`.
2. **Dual Coding (`education-dual-coding`)** — *Prose + Visual Diagram*:
   - Pair concise conceptual explanations with a fenced `mermaid` diagram (`flowchart`, `sequenceDiagram`, `stateDiagram-v2`) so the learner encodes both verbal and structural representations.
3. **Construction (`education-construction`)** — *Generative Study Artifact*:
   - Guide or execute synthesis of a durable study artifact in `00_Inbox/` combining a priming schema, dual-coded Mermaid diagram, quiz prompts with expected answers, and Feynman elaboration prompts.
4. **Application (`education-application`)** — *Exercise Job & Binary External Verify*:
   - Assign concrete application exercises extracted from Wiki (`## Application` / `## Exercise`) and verify attempts against objective required-concept checks (never LLM self-score theatre).
   - On failure: bounded replan or HITL park (`CARD-232`) and record a mastery miss so spaced retention resurfaces the concept.
   - On pass: advance the mastery ledger and write outcomes back to Wiki.

## Six Learning OS Turn Skills (Tutor Roster)

- `start-resume-topic`: Initialize or resume a topic syllabus (`education_topic_start_or_resume`) and stage/read topic notes.
- `quiz-turn`: Run a graded active-recall quiz turn (`education_quiz_next`, `education_quiz_grade`, `education_mastery_upsert`).
- `flashcard-turn`: Present front-only flashcard prompts and record grades (`education_flashcard_next`, `education_flashcard_grade`, `education_mastery_due`) without mid-turn Wiki writes.
- `due-review`: Triage and complete spaced-repetition items (`education_due_review_list`, `education_due_review_complete`, `education_retention_run`).
- `education-wiki-curation`: Capture or curate study notes (`wiki_note_create`, `wiki_note_update`) using `02_Resources/_Templates/Education`.
- `progress-summary`: Report objective mastery and course metrics from the ledger (`education_progress_summary`, `education_progress_courses`, `education_progress_mastery`).
