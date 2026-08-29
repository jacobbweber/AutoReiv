# Design

Add a profile. Reuse `set_card_status` and `handoff_to_agent`.

## Action to route to function

1. App start -> `BUILTIN_PROFILES` includes Review -> Chat/Forge list it.
2. Conductor `handoff_to_agent` target `review` after Coding marks In Review.
3. Review reads spec + project files. Pass: `set_card_status` In Review -> Done. Fail: In Review -> Returned with `return_reason`.
4. Writes (`write_card`, `write_spec`, `write_project_file`) and `execute_code` are allowlist-denied.

## System prompt

Judge the result against the spec only. Pass -> Done. Fail -> Returned with a concrete gap. Do not edit product files or rewrite cards.

## Out of this slice

Coding bounce-back prompt (CARD-084). Projects studio.
