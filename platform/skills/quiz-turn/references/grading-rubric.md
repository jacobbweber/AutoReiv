# Quiz Turn Grading & Extraction Rubric (`grading-rubric.md`)

Use this reference when extracting quiz questions from Wiki notes or grading a learner's retrieval attempt.

## 1. Item Selection & Extraction (`education_quiz_next` / `education_quiz_extract`)
1. Always call `education_quiz_next(topic=...)` first to draw from existing `education_mastery` items.
2. Only when `education_quiz_next` returns empty for the topic, call `education_quiz_extract(wiki_path=..., persist=True)`.
3. If the source note has no `## Quiz` section and `education_quiz_extract` returns `needs_questions=True`, author 3–7 focused short-answer `{prompt, answer}` pairs and call `education_quiz_extract(..., questions=[...], persist=True)`. This writes a companion `<note>-quiz.md` without mutating the source note.

## 2. Binary Grading Contract (`education_quiz_grade`)
- Grading is handled deterministically by `quiz_engine.grade_answer_binary` via `education_quiz_grade(item_id=..., answer=...)`.
- Never self-grade in prose without calling `education_quiz_grade`.
- Report `grade` (`pass` / `miss`), `interval_stage`, and `next_due` strictly from the tool return payload.
