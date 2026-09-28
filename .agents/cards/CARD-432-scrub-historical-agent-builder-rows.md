---
id: CARD-432
title: "Scrub historical agent-builder session and job rows"
status: Done
created: 2026-09-23
adr: docs/adr/0058-retire-agent-builder-into-developer.md
labels:
  - type:cleanup
  - area:agents
  - area:sessions
---

# [CARD-432] Scrub historical agent-builder session and job rows

> **Status**: Done
> **Created**: 2026-09-23
> **Found during**: [CARD-429](./CARD-429-classification-simplification.md)
> **ADR Reference**: [ADR-0058](../adr/0058-retire-agent-builder-into-developer.md)
> **Parent**: [CARD-429](./CARD-429-classification-simplification.md)

Optional later slice. Planning only. Say **continue** to change this card. Say **build** before any product code. Say **merge to qa** only after In Review and a live look.

---

## Gate language

| Jacob reply | Meaning |
| --- | --- |
| **`continue`** | Refine this card. No product code. |
| **`build`** | Implement on `feat/card-432-*` from `qa`. |
| **`merge to qa`** | After In Review and a live test. |

---

## 1. Why / Intent (Beat 1)

Boot already deletes the `agent-builder` profile. Old chats and jobs can still say `agent-builder`. Opening one of those chats has no live agent behind that id. Jacob should see Developer on those rows, and the transcript text should stay.

---

## 2. What AutoReiv does now (Beat 2)

`retire_agent_builder_rows` in `src/infrastructure/memory/repositories/settings.py` deletes `custom_agents` and `agent_overrides` for `agent-builder` and sets `routines.agent_id` to `developer`. It does not update `sessions`, `messages`, `jobs`, or `phases` (`src/infrastructure/memory/schema.py`). Those tables store `agent_id` or `assigned_agent_id`. CARD-429 left them on purpose.

---

## 3. What will change (Beat 3)

On boot, rows that still name `agent-builder` point at `developer`:

- `sessions.agent_id`
- `messages.agent_id`
- `jobs.agent_id`
- `phases.assigned_agent_id`

Message `content` stays. Recommended: one migration function next to `retire_agent_builder_rows`, idempotent, no deletes. A session opened after boot loads under Developer.

---

## 4. What dies today (Beat 4)

- Stored `agent_id` / `assigned_agent_id` values equal to `agent-builder` on sessions, messages, jobs, and phases.

Kept: the transcript text, the profile purge from CARD-429, and the paused skill routines already aimed at Developer.

---

## 5. Acceptance criteria (EARS)

- **[REQ-432-001]** WHEN boot runs THE SYSTEM SHALL set `sessions.agent_id`, `messages.agent_id`, `jobs.agent_id`, and `phases.assigned_agent_id` from `agent-builder` to `developer`.
- **[REQ-432-002]** THE SYSTEM SHALL NOT delete those session, message, job, or phase rows AND SHALL NOT change message content.
- **[REQ-432-003]** WHEN the same boot runs twice THE SYSTEM SHALL leave rows that already say `developer` unchanged.
- **[REQ-432-004]** THE SYSTEM SHALL NOT recreate an `agent-builder` profile.

---

## 6. Human verification runbook

After **build**:

1. If you still have an old Agent Builder chat, restart serve and open it. The agent shown is Developer. The old messages are still there.
2. Routines `skill-eval-sleep` and `skill-curator` still show Developer and stay off.
3. Chat still has no Agent Builder.

---

## 7. Out of scope

- Editing the words inside old messages.
- Unregistering `save_agent_specification` ([CARD-431](./CARD-431-unregister-save-agent-specification.md)).
- Rewriting a developer prompt you already edited ([CARD-433](./CARD-433-user-modified-developer-prompt-authoring-sentence.md)).
