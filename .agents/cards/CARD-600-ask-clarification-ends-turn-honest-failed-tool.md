---
id: CARD-600
title: "ask_clarification ends the turn, and a reply that hides a failed tool call gets a short note (CARD-523 items 5 and 7)"
status: Done
created: 2026-10-01
completed: 2026-10-02
branch: feat/card-599-600-reply-honesty
related:
  - CARD-523
labels:
  - type:bug
  - area:kernel
  - area:chat
  - P2
needs_decision: none
milestone: M24
---

# [CARD-600] ask_clarification ends the turn, and a reply that hides a failed tool call gets a short note (CARD-523 items 5 and 7)

> **Status**: Done (2026-10-02)
> **Labels**: `type:bug`, `area:kernel`, `area:chat`, `P2`

## Why

CARD-523 (Done) left two items for a follow-up because they change reply behaviour:
- **Item 5.** The model called `ask_clarification` and then kept working, asking again later.
- **Item 7.** A failed tool call (for example a hand-off that hit its budget) was not mentioned in the final reply.

## Scope

1. **`ask_clarification` ends the turn.** The kernel stops the loop after the call, shows the question, and the next user message answers it.
2. **When a turn's last failed tool call is not mentioned in the final reply, append one line:** "Note: <tool> failed: <short error>." No re-prompt.

## Acceptance criteria

- **Unit:** a scripted turn that calls `ask_clarification` makes no further model or tool calls and shows the question.
- **Unit:** a turn whose last tool failed and whose reply omits it gets the note. A reply that mentions it does not.
- Fast preflight and smoke are green.

## Change

Shared branch with CARD-599: `feat/card-599-600-reply-honesty`.

- `ask_clarification` ends the turn. Other tool calls in the same step get a "skipped, waiting for the user" result and do not run. The question is saved and streamed as the reply, and not repeated if the model already wrote it. The next user message is the answer.
- Failed tool note: if the last failed tool call (error, `{"success": false}`, or status error/failed) is not mentioned in the reply, the reply gets "Note: <tool> failed: <short error>." A later success of the same tool clears it. Approval parks and ask_clarification do not count. Machine codes such as `tool_not_offered:` are dropped from the note.
- Both `run_turn` and `stream_turn`. Tests: `tests/unit/kernel/test_card600_clarify_and_failed_tool_note.py`.

## Results

| Check | Result | Notes |
|---|---|---|
| Kernel suite | PASS | 213 passed |
| Full pytest | PASS | 2320 passed, 12 skipped |
| Full preflight (`--base origin/qa`) | PASS | ruff, eslint (0 errors, 3 warnings), pytest 2320, vitest 944, smoke 76 |
| Live clarification ("rename my note", no details) | PASS | 4/4 turns ended and waited (1 via `ask_clarification` as the only tool, 3 asked in plain text); 3/3 follow-ups were used as the answer |
| Live failed tool, reply mentions it | PASS | read of missing `00_Inbox/zz-missing-note.md`: reply said it does not exist, no extra note |
| Live failed tool, reply hides it ("session ID only") | PASS | reply = session ID + "Note: wiki_note_read failed: Note '00_Inbox/zz-missing-note.md' not found." |

Live env: throwaway :8770, Spark nemotron-3.5-lightning only. Screenshots in `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1002c\`: `600-clarification-reply.png`, `600-failed-tool-reply.png`, `600-failed-tool-note.png`.

## Release note

When an agent asks a clarifying question it now stops and waits for the answer. If a tool fails and the reply does not say so, the reply ends with a short "Note: ... failed" line.
