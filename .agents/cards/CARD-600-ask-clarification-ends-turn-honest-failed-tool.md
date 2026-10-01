---
id: CARD-600
title: "ask_clarification ends the turn, and a reply that hides a failed tool call gets a short note (CARD-523 items 5 and 7)"
status: Ready
created: 2026-10-01
branch: qa
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

> **Status**: Ready (filed 2026-10-01)
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
