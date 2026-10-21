# Due Review & Retention Schedule Guide (`retention-schedule.md`)

Use this reference when triaging due SRS items or triggering the background retention routine in `due-review`.

## 1. Due Queue Triage (`education_due_review_list`)
- Call `education_due_review_list` (or `education_mastery_due`) at the start of the turn.
- When `empty` is `True` (or `empty_state == "No due reviews."`), report the empty queue honestly and stop; never fabricate due questions.

## 2. Completing a Review (`education_due_review_complete`)
- Present one due `prompt` without revealing `expected_answer`.
- After the learner answers, call `education_due_review_complete(item_id=..., answer=...)`.
- Report `grade` (`pass` / `miss`), `interval_stage`, `next_due`, and `left_due_queue` directly from the tool response.

## 3. Standing Retention Routine (`education_retention_run`)
- Only call `education_retention_run` when the operator explicitly asks to run the retention routine or mint standing review jobs.
- Report minted job IDs or `no_orchestrator` / failure status honestly from the tool return.
